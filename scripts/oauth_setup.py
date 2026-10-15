"""Trusted-computer loopback OAuth -> GitHub Secrets, no token files or output."""
import argparse
import os
import subprocess

REPO = "Nishat2001-hub/Nishat-info-hub-youtube"


def set_secret(name, value):
    if not value:
        raise RuntimeError("Required credential was not returned")
    result = subprocess.run(["gh", "secret", "set", name, "--repo", REPO],
                            input=value, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError("GitHub rejected secret storage; check gh login and repository access")
    print(f"Stored {name} in GitHub Secrets.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-json", required=True, help="Downloaded Desktop OAuth client file")
    args = parser.parse_args()
    if os.getenv("GITHUB_ACTIONS") == "true":
        raise RuntimeError("OAuth consent must run on your trusted computer")
    result = subprocess.run(["gh", "auth", "status"], capture_output=True)
    if result.returncode:
        raise RuntimeError("Sign in using gh auth login before running OAuth setup")
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    scopes = ["https://www.googleapis.com/auth/youtube.upload",
              "https://www.googleapis.com/auth/youtube.readonly"]
    flow = InstalledAppFlow.from_client_secrets_file(args.client_json, scopes, autogenerate_code_verifier=True)
    if flow.client_type != "installed":
        raise RuntimeError("Use a Desktop OAuth client with a loopback redirect")
    creds = flow.run_local_server(
        host="localhost", bind_addr="127.0.0.1", port=0, open_browser=True,
        authorization_prompt_message="", success_message="Authorization complete. You may close this window.",
        access_type="offline", prompt="consent", timeout_seconds=300)
    if not creds.refresh_token:
        raise RuntimeError("Google did not return an offline refresh token")
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    channels = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = channels.get("items", [])
    if len(items) != 1:
        raise RuntimeError("Authorize exactly one YouTube channel before storing secrets")
    print("Authorized channel:", items[0]["snippet"]["title"])
    # No secrets are passed in CLI arguments, printed, or written to disk.
    for name, value in (
        ("YOUTUBE_CLIENT_ID", creds.client_id),
        ("YOUTUBE_CLIENT_SECRET", creds.client_secret),
        ("YOUTUBE_REFRESH_TOKEN", creds.refresh_token),
        ("YOUTUBE_CHANNEL_ID", items[0]["id"]),
    ):
        set_secret(name, value)
    print("Setup complete. Generation never uploads; each private upload requires artifact approval.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Avoid printing provider responses or a traceback with authorization details.
        print(f"Setup stopped ({type(error).__name__}). Check Google consent and GitHub login.")
        raise SystemExit(1)
