"""Shared bounded retries and atomic, credential-free reports."""
import json
import os
import random
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def retry(operation, attempts=3, retryable=lambda error: True):
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as error:
            if attempt == attempts - 1 or not retryable(error):
                raise
            time.sleep(min(30, 2 ** attempt) + random.random())


def report(status, stage, **fields):
    # Never serialize raw exceptions: HTTP errors may include credentials/session URLs.
    data = {"status": status, "stage": stage, **fields}
    write_json(OUT / "report.json", data)
    print(json.dumps(data, ensure_ascii=False))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### NISHAT TECH\nStatus: **{status}**\n\nStage: {stage}\n\n")
            for key, value in fields.items():
                handle.write(f"- {key}: {value}\n")
    return data
