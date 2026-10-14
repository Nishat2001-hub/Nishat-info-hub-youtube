"""Run interactively on a trusted computer; NEVER run inside GitHub Actions."""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
def main():
    print("Use a Google OAuth Desktop client JSON downloaded to this computer.")
    path=Path(input("Path to client_secret JSON: ").strip())
    flow=InstalledAppFlow.from_client_secrets_file(str(path),SCOPES)
    creds=flow.run_local_server(port=0,open_browser=True)
    print("OAuth authorization complete.")
    print("Add these values directly to GitHub Actions Secrets; never paste into chat:")
    data=json.loads(path.read_text())
    client=data.get("installed") or data.get("web")
    print("YOUTUBE_CLIENT_ID:",client["client_id"])
    print("YOUTUBE_CLIENT_SECRET:",client["client_secret"])
    print("YOUTUBE_REFRESH_TOKEN:",creds.refresh_token or "NOT RETURNED: check OAuth consent configuration")
if __name__=="__main__":main()
