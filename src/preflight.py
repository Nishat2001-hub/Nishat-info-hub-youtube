"""Read-only channel preflight. Never creates an upload or changes history."""
import os
from . import youtube_upload
from .common import report


def main():
    missing = [name for name in youtube_upload.SECRET_NAMES if not os.getenv(name)]
    if missing:
        report("needs_setup", "oauth_preflight", missing_secret_names=missing,
               upload_verified=False, channel_verified=False)
        return 0
    try:
        youtube_upload.client()
        report("channel_verified", "oauth_preflight", channel_verified=True,
               upload_verified=False)
        return 0
    except Exception as error:
        report("failed", "oauth_preflight", error_type=type(error).__name__,
               channel_verified=False, upload_verified=False)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
