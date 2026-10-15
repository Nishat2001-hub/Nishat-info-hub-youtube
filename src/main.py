"""One complete daily factory run. Safe to restart; public publishing is absent."""
import argparse
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from .common import OUT, report
from .content import Exhausted, select
from .state import History
from .render import render
from . import youtube_upload


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Synthetic audio; upload forbidden")
    parser.add_argument("--test-render", action="store_true", help="Stateless CI render; upload forbidden")
    args = parser.parse_args(argv)
    stage = "history"
    key, history = None, None
    try:
        day = datetime.now(ZoneInfo("Asia/Dhaka")).date().isoformat()
        test = args.test_render or args.smoke
        history = None if test else History().load()
        entries = {} if test else history.data["entries"]
        if history and history.ambiguous():
            report("blocked", stage, reason="Uncertain upload requires YouTube reconciliation.",
                   content_keys=history.ambiguous())
            return 1
        if any(entry.get("day") == day and entry.get("status") in {"rendered", "uploaded"}
               for entry in entries.values()):
            report("skipped", stage, reason="This Bangladesh calendar day already completed.")
            return 0
        stage = "content"
        topic, warning = select(entries, day)
        key = topic["key"]
        stage = "render"
        metadata = render(topic, smoke=args.smoke)
        if args.render_only or test or not youtube_upload.configured():
            if history:
                history.mark(key, "rendered", day=day, title=topic["title"],
                             script=topic["script"], provider=topic["provider"])
            status = "test_rendered" if test else (
                "rendered" if args.render_only else "awaiting_oauth")
            report(status, stage, duration_seconds=round(metadata["duration_seconds"], 2),
                   voice_providers=metadata["voice_providers"],
                   script_provider=metadata["script_provider"],
                   warning=warning or "", upload_verified=False)
            return 0
        stage = "oauth_preflight"
        service = youtube_upload.client()
        stage = "upload_checkpoint"
        history.mark(key, "uploading", day=day, title=topic["title"],
                     script=topic["script"], provider=topic["provider"])
        stage = "private_upload"
        video_id = youtube_upload.upload_private(service, metadata)
        # Save the confirmed video ID BEFORE thumbnail/post-upload work.
        stage = "save_upload"
        history.mark(key, "uploaded", video_id=video_id, privacy="private")
        stage = "verify_upload"
        upload_status = youtube_upload.verify(service, video_id)
        thumbnail_status = youtube_upload.thumbnail(service, video_id)
        history.mark(key, "uploaded", verified_at=datetime.now(ZoneInfo("UTC")).isoformat(),
                     youtube_upload_status=upload_status, thumbnail=thumbnail_status)
        report("uploaded_private", stage, video_id=video_id, privacy="private",
               youtube_upload_status=upload_status, upload_verified=True,
               thumbnail=thumbnail_status, warning=warning or "",
               voice_providers=metadata["voice_providers"])
        return 0
    except Exhausted:
        report("blocked", stage, reason="Curated catalog exhausted; duplicates are blocked.",
               action="Configure optional Gemini AI Studio free-tier key or extend catalog.")
        return 1
    except Exception as error:
        # Do not dump a stack trace or HTTP response that could reveal OAuth/session data.
        # A persisted 'uploading' entry remains unresolved on any uncertain outcome.
        report("failed", stage, error_type=type(error).__name__,
               http_status=getattr(error, "code", None),
               reason="Operation failed. See stage; no credentials are included in this report.",
               upload_verified=False)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
