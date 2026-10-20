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
from .approval import bundle_digest


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
        metadata = render(topic, smoke=args.smoke, test_render=args.test_render)
        # Generation never uploads, even when credentials are present.
        digest = bundle_digest()
        if history:
            history.mark(key, "rendered", day=day, title=topic["title"],
                         script=topic["script"], provider=topic["provider"])
        status = "test_rendered" if test else (
            "awaiting_approval")
        report(status, stage, duration_seconds=round(metadata["duration_seconds"], 2),
               voice_providers=metadata["voice_providers"],
               script_provider=metadata["script_provider"],
               warning=warning or "", upload_verified=False, approval_sha256=digest)
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

