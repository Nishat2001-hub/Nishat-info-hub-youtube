"""Optional Gemini AI Studio free-tier scripts; curated Bengali fallback."""
import hashlib
import json
import os
import re
import urllib.request
import unicodedata
from difflib import SequenceMatcher
from .common import ROOT, retry


class Exhausted(RuntimeError):
    pass


def normalized(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def fingerprint(value):
    return hashlib.sha256(normalized(value).encode()).hexdigest()


def validate(topic):
    title, script = topic.get("title", ""), topic.get("script", "")
    if not isinstance(title, str) or not isinstance(script, str):
        raise ValueError("Text required")
    if not 8 <= len(title) <= 85 or not 70 <= len(script) <= 650:
        raise ValueError("Invalid script length")
    if len(re.findall(r"[\u0980-\u09ff]", script)) < 45:
        raise ValueError("Script must be Bengali")
    if any(x in script for x in ("<", ">", "{", "}")):
        raise ValueError("Unexpected markup")
    sentences = [part.strip() for part in re.split(r"(?<=[।!?])\s*", script) if part.strip()]
    if not 2 <= len(sentences) <= 9:
        raise ValueError("Use two to nine short sentences")
    return {**topic, "sentences": sentences, "key": fingerprint(script)}


def duplicate(topic, history):
    for key, entry in history.items():
        if key == topic["key"] or normalized(entry.get("title", "")) == normalized(topic["title"]):
            return True
        previous = entry.get("script", "")
        if previous and SequenceMatcher(None, normalized(previous), normalized(topic["script"])).ratio() > .82:
            return True
    return False


def ai_topic(history):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    # AI Studio key, no Vertex AI / billing / Cloud API provisioning.
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not re.fullmatch(r"gemini-[a-z0-9.-]+", model):
        raise ValueError("Invalid Gemini model name")
    recent = [entry.get("title") for entry in history.values()][-200:]
    prompt = (
        "Write one original Bengali technology education YouTube Short for NISHAT TECH. "
        "Use evergreen, factual, practical advice; no current news, prices, medical advice, "
        "claims of guaranteed security or fabricated sources. Bengali natural speech, "
        "3-6 sentences, 70-110 Bengali words maximum, 650 characters maximum. "
        "Start with a concise hook, then useful steps and a short conclusion. "
        "Return JSON only: title (8-75 characters), script (Bengali punctuation ।), "
        "source_url (a relevant official documentation URL or empty). "
        "Avoid all these previously used topics: " + json.dumps(recent, ensure_ascii=False))
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"responseMimeType": "application/json", "temperature": .7,
                                    "maxOutputTokens": 2048, "thinkingConfig": {"thinkingBudget": 0}}}
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
    def call():
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
        parts = result["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts if not part.get("thought"))
        topic = validate(json.loads(text))
        topic["provider"] = "gemini-ai-studio"
        return topic
    return retry(call, attempts=2)


def select(history, day):
    warning = None
    if os.getenv("GEMINI_API_KEY"):
        try:
            topic = ai_topic(history)
            if not duplicate(topic, history):
                return topic, warning
            warning = "AI returned a duplicate; curated fallback used."
        except Exception:
            warning = "AI unavailable or invalid response; curated fallback used."
    topics = json.loads((ROOT / "data/topics.json").read_text(encoding="utf-8"))
    # Rotate starting point without repeating previously rendered/uploaded scripts.
    start = int(fingerprint(day)[:8], 16) % len(topics)
    for index in range(len(topics)):
        topic = validate(topics[(start + index) % len(topics)])
        topic["provider"] = "curated"
        if not duplicate(topic, history):
            return topic, warning
    raise Exhausted("All curated topics used. AI key can extend the catalog; repeats are blocked.")
