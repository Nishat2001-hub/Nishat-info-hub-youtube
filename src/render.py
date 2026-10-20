"""Bengali shaping, sentence-timed subtitles and animated 1080x1920 rendering."""
import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features
from .common import OUT, write_json

FONT = os.getenv("BENGALI_FONT", "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf")
LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def run(args):
    # Keep ffmpeg noise out of logs, including any future resource URLs.
    result = subprocess.run(args, capture_output=True, timeout=600)
    if result.returncode:
        raise RuntimeError(f"Rendering command failed: {Path(args[0]).name}")
    return result.stdout


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(path)]))


def duration(path):
    return float(probe(path)["format"]["duration"])


def wrap(text, font, width):
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, line = [], ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        if draw.textlength(candidate, font=font) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


async def edge_voice(text, destination, voice):
    import edge_tts
    # Timeouts prevent one provider from consuming the entire workflow timeout.
    await asyncio.wait_for(edge_tts.Communicate(
        text, voice, rate="-5%", pitch="+0Hz", volume="+0%"
    ).save(str(destination)), timeout=60)


def voice_segment(text, destination):
    voices = [os.getenv("BENGALI_VOICE", "bn-BD-NabanitaNeural"), "bn-BD-PradeepNeural"]
    for voice in dict.fromkeys(voices):
        for attempt in range(2):
            try:
                asyncio.run(edge_voice(text, destination, voice))
                if duration(destination) > .2:
                    return voice
            except Exception:
                destination.unlink(missing_ok=True)
    try:
        from gtts import gTTS
        gTTS(text=text, lang="bn", timeout=40).save(str(destination))
        if duration(destination) > .2:
            return "gtts-bn"
    except Exception:
        destination.unlink(missing_ok=True)
    if shutil.which("espeak-ng"):
        wav = destination.with_suffix(".wav")
        run(["espeak-ng", "-v", "bn", "-s", "145", "-w", str(wav), text])
        run(["ffmpeg", "-y", "-i", str(wav), str(destination)])
        if duration(destination) > .2:
            return "espeak-ng-bn (offline fallback)"
    raise RuntimeError("All Bengali voice providers failed")


def audio(sentences, smoke=False):
    timeline, cursor, providers = [], 0.0, []
    concat = []
    for index, sentence in enumerate(sentences):
        part = OUT / f"speech-{index}.mp3"
        if smoke:
            run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                 "sine=frequency=440:sample_rate=48000:duration=1.5", str(part)])
            provider = "synthetic-smoke-test"
        else:
            provider = voice_segment(sentence, part)
        seconds = duration(part)
        # Normalize each segment to PCM; pause is part of the precise subtitle timeline.
        pcm = OUT / f"segment-{index}.wav"
        run(["ffmpeg", "-y", "-i", str(part), "-af", "apad=pad_dur=0.18",
             "-ar", "48000", "-ac", "1", str(pcm)])
        segment_duration = duration(pcm)
        timeline.append({"start": cursor, "end": cursor + seconds, "text": sentence})
        cursor += segment_duration
        providers.append(provider)
        concat.append(f"file '{pcm.name}'")
    manifest = OUT / "audio.txt"
    manifest.write_text("\n".join(concat), encoding="utf-8")
    output = OUT / "voice.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", str(output)])
    return output, timeline, sorted(set(providers))


def ass_time(seconds):
    centiseconds = round(seconds * 100)
    return f"{centiseconds // 360000}:{centiseconds // 6000 % 60:02}:{centiseconds // 100 % 60:02}.{centiseconds % 100:02}"


def srt_time(seconds):
    millis = round(seconds * 1000)
    return f"{millis // 3600000:02}:{millis // 60000 % 60:02}:{millis // 1000 % 60:02},{millis % 1000:03}"


def subtitles(timeline):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Noto Sans Bengali,58,&H00FFFFFF,&H0000E5FF,&H00120A06,&H90000000,0,0,0,0,100,100,0,0,1,4,1,2,90,90,440,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events, srt = [], []
    font = ImageFont.truetype(FONT, 58)
    for index, item in enumerate(timeline, 1):
        # Only trusted text, escaped before entering libass's formatting grammar.
        text = item["text"].replace("\\", "").replace("{", "").replace("}", "")
        lines = wrap(text, font, 870)
        ass_text = r"\N".join(lines)
        events.append(f"Dialogue: 0,{ass_time(item['start'])},{ass_time(item['end'])},Caption,,0,0,0,,"
                      + r"{\fad(120,120)}" + ass_text)
        srt.append(f"{index}\n{srt_time(item['start'])} --> {srt_time(item['end'])}\n" + "\n".join(lines))
    (OUT / "subtitles.ass").write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    (OUT / "subtitles.srt").write_text("\n\n".join(srt) + "\n", encoding="utf-8")


def artwork(topic):
    if not features.check("raqm"):
        raise RuntimeError("Pillow requires libraqm for correct Bengali text shaping")
    background = Image.new("RGB", (1080, 1920))
    d = ImageDraw.Draw(background)
    for y in range(1920):
        t = y / 1920
        d.line((0, y, 1080, y), fill=(int(5 + 15*t), int(20 + 16*t), int(42 + 33*t)))
    for x in range(-80, 1160, 120):
        d.line((x, 0, x+220, 1920), fill=(25, 54, 76), width=2)
    for y in range(80, 1920, 120):
        d.line((0, y, 1080, y), fill=(25, 54, 76), width=2)
    d.ellipse((580, 400, 1390, 1210), outline=(26, 117, 148), width=5)
    d.ellipse((-420, 1080, 400, 1900), outline=(36, 89, 154), width=4)
    background.save(OUT / "background.png")
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle((70, 170, 1010, 355), 28, fill=(5, 14, 32, 230))
    d.text((110, 218), "NISHAT TECH", font=ImageFont.truetype(LATIN, 64), fill="#53e1ef")
    d.rounded_rectangle((70, 410, 1010, 920), 36, fill=(7, 22, 44, 220))
    font = ImageFont.truetype(FONT, 78)
    lines = wrap(topic["title"], font, 820)
    if len(lines) > 4:
        font = ImageFont.truetype(FONT, 64)
        lines = wrap(topic["title"], font, 820)
    for index, line in enumerate(lines):
        d.text((120, 490 + index*105), line, font=font, fill="white")
    d.rounded_rectangle((70, 1000, 1010, 1515), 36, fill=(5, 14, 32, 200))
    d.text((115, 1580), "বাংলায় প্রযুক্তি সহজভাবে", font=ImageFont.truetype(FONT, 45), fill="#b5d9ea")
    overlay.save(OUT / "overlay.png")
    thumb = background.convert("RGBA")
    thumb.alpha_composite(overlay)
    d = ImageDraw.Draw(thumb)
    d.text((140, 1140), "জানুন সহজ ভাষায়", font=ImageFont.truetype(FONT, 72), fill="#53e1ef")
    thumb.convert("RGB").save(OUT / "thumbnail.jpg", quality=92, optimize=True)


def render(topic, smoke=False, test_render=False):
    OUT.mkdir(exist_ok=True)
    sentences = topic["sentences"][:2] if smoke else topic["sentences"]
    voice, timeline, providers = audio(sentences, smoke=smoke)
    seconds = duration(voice)
    if not 2 <= seconds <= 59:
        raise RuntimeError("Narration must be between 2 and 59 seconds")
    subtitles(timeline)
    artwork(topic)
    # Gentle camera motion, moving light, subtitle fades, and intro/outro transitions.
    # All artwork is original; no external footage or copyrighted music required.
    filters = (
        "[0:v]zoompan=z='1.04+0.02*sin(on/70)':"
        "x='iw/2-iw/zoom/2+8*sin(on/50)':y='ih/2-ih/zoom/2':"
        "d=1:s=1080x1920:fps=30[bg];"
        "[bg][1:v]overlay=0:0,"
        "drawbox=x=70:y=1690:w=940:h=8:color=0x25445d:t=fill,"
        "drawbox=x=70:y=1690:w=iw-140:h=8:color=0x53e1ef:t=fill,"
        f"subtitles=filename='{(OUT / 'subtitles.ass').as_posix()}',"
        f"fade=t=in:st=0:d=0.3,fade=t=out:st={max(0, seconds-.4):.3f}:d=0.4[v]"
    )
    video = OUT / "short.mp4"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(OUT / "background.png"),
         "-loop", "1", "-i", str(OUT / "overlay.png"), "-i", str(voice),
         "-filter_complex", filters, "-map", "[v]", "-map", "2:a:0",
         "-t", f"{seconds:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "21",
         "-threads", "2", "-filter_complex_threads", "1", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(video)])
    details = probe(video)
    streams = details["streams"]
    visual = next(stream for stream in streams if stream["codec_type"] == "video")
    sound = next(stream for stream in streams if stream["codec_type"] == "audio")
    if (visual["width"], visual["height"], visual["codec_name"], sound["codec_name"]) != (1080, 1920, "h264", "aac"):
        raise RuntimeError("Invalid video format")
    if abs(float(details["format"]["duration"]) - seconds) > .5 or video.stat().st_size < 10000:
        raise RuntimeError("Invalid rendered duration or size")
    # Decode the entire finished file: container metadata alone is insufficient.
    run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"])
    meta = {"title": topic["title"][:90] + " #Shorts",
            "description": topic["script"] + "\n\nNISHAT TECH — বাংলায় প্রযুক্তি সহজভাবে"
            + ("\nতথ্যসূত্র: " + topic["source_url"] if topic.get("source_url") else "")
            + "\n#NishatTech #BanglaTech #Shorts",
            "tags": ["Nishat Tech", "Bangla Tech", "Bengali", "Shorts"],
            "privacyStatus": "private", "content_key": topic["key"],
            "script_provider": topic["provider"], "voice_providers": providers,
            "duration_seconds": seconds, "smoke_test": smoke, "test_render": test_render}
    write_json(OUT / "metadata.json", meta)
    write_json(OUT / "timing.json", timeline)
    return meta

