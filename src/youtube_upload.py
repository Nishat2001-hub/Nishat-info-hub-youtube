"""Private-only YouTube upload. Requires user-authorized OAuth secrets."""
import json, os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES=["https://www.googleapis.com/auth/youtube.upload"]

def upload_private(video_path="output/short.mp4", metadata_path="output/metadata.json"):
    keys=("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN")
    missing=[k for k in keys if not os.getenv(k)]
    if missing:
        raise RuntimeError("Missing OAuth secrets: "+", ".join(missing))
    creds=Credentials(
        token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=SCOPES)
    creds.refresh(Request())
    youtube=build("youtube","v3",credentials=creds,cache_discovery=False)
    meta=json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    body={"snippet":{"title":meta["title"][:100],
                     "description":meta["description"][:5000],
                     "categoryId":"28"},
          "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}}
    request=youtube.videos().insert(part="snippet,status",body=body,
        media_body=MediaFileUpload(video_path,mimetype="video/mp4",resumable=True))
    response=None
    while response is None:
        _,response=request.next_chunk()
    print("Private upload complete; video ID:",response["id"])
    return response["id"]

if __name__=="__main__":
    upload_private()
