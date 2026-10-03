from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    path = Path("client_secret.json")
    if not path.exists():
        raise SystemExit(
            "Download your Google OAuth Desktop-App JSON and rename it to client_secret.json."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(path), SCOPES)
    credentials = flow.run_local_server(port=0)
    Path("token.json").write_text(credentials.to_json(), encoding="utf-8")
    print("Created token.json. Copy its complete contents into GitHub secret YOUTUBE_TOKEN_JSON.")

if __name__ == "__main__":
    main()
