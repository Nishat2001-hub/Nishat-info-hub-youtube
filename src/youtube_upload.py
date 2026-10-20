"""Private-only resumable uploads; OAuth lives in environment variables only."""
import json
import os
from pathlib import Path
from .common import OUT, retry

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
SECRET_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET",
                "YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CHANNEL_ID")


def configured():
    return all(os.getenv(name) for name in SECRET_NAMES)


def client():
    if not configured():
        raise RuntimeError("YouTube OAuth secrets and channel binding are required")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    creds = Credentials(token=None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YOUTUBE_CLIENT_ID"],
                        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"], scopes=SCOPES)
    retry(lambda: creds.refresh(Request()))
    service = build("youtube", "v3", http=AuthorizedHttp(creds, http=httplib2.Http(timeout=90)),
                    cache_discovery=False)
    channels = service.channels().list(part="id", mine=True).execute(num_retries=3)
    if os.environ["YOUTUBE_CHANNEL_ID"] not in {item["id"] for item in channels.get("items", [])}:
        raise RuntimeError("Authorized YouTube channel does not match configured channel")
    return service


def upload_private(service, metadata, video_path=None, media_factory=None):
    if metadata.get("smoke_test") or metadata.get("test_render"):
        raise RuntimeError("Test videos must never be uploaded")
    if metadata.get("privacyStatus", "private") != "private":
        raise RuntimeError("Only private uploads are permitted")
    if media_factory is None:
        from googleapiclient.http import MediaFileUpload
        media_factory = MediaFileUpload
    video_path = Path(video_path or OUT / "short.mp4")
    if not video_path.is_file() or video_path.stat().st_size < 10000:
        raise RuntimeError("Upload video missing or too small")
    body = {"snippet": {"title": metadata["title"][:100],
                        "description": metadata["description"][:5000],
                        "tags": metadata.get("tags", []),
                        "categoryId": "28", "defaultLanguage": "bn",
                        "defaultAudioLanguage": "bn"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True}}
    request = service.videos().insert(
        part="snippet,status", body=body,
        media_body=media_factory(str(video_path), mimetype="video/mp4",
                                 chunksize=4*1024*1024, resumable=True),
        notifySubscribers=False)
    response = None
    # next_chunk retries the SAME resumable session, never creates another insert.
    while response is None:
        _, response = request.next_chunk(num_retries=5)
    if not response.get("id") or response.get("status", {}).get("privacyStatus") != "private":
        raise RuntimeError("Upload response did not confirm a private video")
    return response["id"]


def thumbnail(service, video_id, path=None):
    from googleapiclient.http import MediaFileUpload
    path = Path(path or OUT / "thumbnail.jpg")
    if path.stat().st_size >= 2*1024*1024:
        return "Generated locally; file exceeds YouTube thumbnail size limit."
    try:
        service.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(path), mimetype="image/jpeg")
        ).execute(num_retries=3)
        return "API accepted thumbnail; Shorts surfaces may use a video frame instead."
    except Exception:
        # Thumbnail support/channel verification must not trigger another video upload.
        return "Generated locally; YouTube rejected thumbnail (channel eligibility or Shorts restriction)."


def verify(service, video_id):
    response = service.videos().list(part="status", id=video_id).execute(num_retries=3)
    items = response.get("items", [])
    if not items or items[0]["status"]["privacyStatus"] != "private":
        raise RuntimeError("YouTube did not confirm private status")
    return items[0]["status"].get("uploadStatus", "unknown")

