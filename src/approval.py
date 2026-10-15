"""Approval binds the exact MP4 and metadata bytes; generation has no upload path."""
import argparse
import hashlib
import hmac
import json
import re
from .common import OUT, report
from .state import History
from . import youtube_upload


def bundle_digest():
    digest = hashlib.sha256()
    for name in ("short.mp4", "metadata.json"):
        data = (OUT / name).read_bytes()
        digest.update(name.encode() + b"\0" + len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--approved-sha256", required=True)
    args = parser.parse_args(argv)
    stage = "approval"
    try:
        if not re.fullmatch(r"[0-9a-f]{64}", args.approved_sha256):
            raise ValueError("A reviewed artifact digest is required")
        if not hmac.compare_digest(bundle_digest(), args.approved_sha256):
            raise ValueError("Approved bytes do not match")
        metadata = json.loads((OUT / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("smoke_test") or metadata.get("privacyStatus") != "private":
            raise ValueError("Only real private videos are eligible")
        key = metadata["content_key"]
        stage = "history"
        history = History().load()
        if history.ambiguous():
            raise RuntimeError("Reconcile uncertain upload first")
        entry = history.data["entries"].get(key, {})
        if entry.get("status") != "rendered":
            raise RuntimeError("Artifact must have a rendered production history entry")
        stage = "oauth_preflight"
        service = youtube_upload.client()
        stage = "upload_checkpoint"
        history.mark(key, "uploading", approved_sha256=args.approved_sha256)
        stage = "private_upload"
        video_id = youtube_upload.upload_private(service, metadata)
        stage = "save_upload"
        history.mark(key, "uploaded", video_id=video_id, privacy="private")
        stage = "verify_upload"
        status = youtube_upload.verify(service, video_id)
        # Thumbnail is retained for review; no unapproved extra file is uploaded.
        report("uploaded_private", stage, video_id=video_id, privacy="private",
               youtube_upload_status=status, upload_verified=True)
        return 0
    except Exception as error:
        report("failed", stage, error_type=type(error).__name__, upload_verified=False)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
