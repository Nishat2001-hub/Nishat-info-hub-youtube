import asyncio, json, os, subprocess, pathlib, random, wave
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"output"; OUT.mkdir(exist_ok=True)
FONT="/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"

def run(args):
    subprocess.run(args,check=True)

async def main():
    topics=json.loads((ROOT/"data/topics.json").read_text(encoding="utf-8"))
    index=int(os.getenv("TOPIC_INDEX",str(datetime.utcnow().toordinal())))%len(topics)
    topic=topics[index]
    script=topic["script"]
    audio=OUT/"voice.mp3"
    voice=os.getenv("BENGALI_VOICE","bn-BD-NabanitaNeural")
    await edge_tts.Communicate(script,voice).save(str(audio))
    font=ImageFont.truetype(FONT,68)
    small=ImageFont.truetype(FONT,43)
    im=Image.new("RGB",(1080,1920),(7,19,40))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((65,180,1015,1720),radius=55,fill=(13,43,70))
    d.text((100,275),"NISHAT TECH",font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",62),fill=(60,220,245))
    # Pillow basic layout; render Bengali lines without external copyrighted assets
    words=topic["title"].split()
    lines=[]; line=""
    for word in words:
        candidate=(line+" "+word).strip()
        if d.textbbox((0,0),candidate,font=font)[2]>830 and line:
            lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    for n,line in enumerate(lines):d.text((110,600+n*105),line,font=font,fill="white")
    d.text((110,1510),"বাংলায় প্রযুক্তি সহজভাবে",font=small,fill=(180,230,235))
    img=OUT/"cover.png";im.save(img)
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)]).decode().strip())
    video=OUT/"short.mp4"
    run(["ffmpeg","-y","-loop","1","-framerate","25","-i",str(img),"-i",str(audio),"-c:v","libx264","-tune","stillimage","-c:a","aac","-b:a","160k","-pix_fmt","yuv420p","-shortest","-movflags","+faststart",str(video)])
    if video.stat().st_size<10000:raise RuntimeError("Output too small")
    (OUT/"metadata.json").write_text(json.dumps({"title":topic["title"]+" #Shorts","description":script+"\n#NishatTech #BanglaTech #Shorts","topic_index":index},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Created",video,"seconds",round(duration,1),"topic",index)

if __name__=="__main__":asyncio.run(main())
