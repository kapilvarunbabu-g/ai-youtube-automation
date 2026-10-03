import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .common import env

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_service():
    data = json.loads(env("YOUTUBE_TOKEN_JSON", required=True))
    credentials = Credentials.from_authorized_user_info(data, SCOPES)
    if not credentials.valid and credentials.expired and credentials.refresh_token:
        from google.auth.transport.requests import Request
        credentials.refresh(Request())
    if not credentials.valid:
        raise RuntimeError("YouTube OAuth token is invalid and could not be refreshed.")
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)

def upload_video(story, video_path):
    youtube = get_service()
    privacy = env("YOUTUBE_PRIVACY_STATUS", "private")
    sources = "\n".join(
        f"- {source.get('title', '')}: {source.get('url', '')}"
        for source in story.get("sources", [])
    )
    description = (
        story.get("description", "").strip()
        + "\n\nSources:\n"
        + sources
        + "\n\nProduction note: this video uses AI-assisted research, synthetic narration and generated motion graphics."
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": story["title"][:100],
                "description": description[:4950],
                "tags": story.get("tags", [])[:20],
                "categoryId": "28",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": bool(story.get("contains_synthetic_media", True)),
                "license": "youtube",
            },
        },
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=-1, resumable=True),
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    return video_id, f"https://www.youtube.com/watch?v={video_id}"
