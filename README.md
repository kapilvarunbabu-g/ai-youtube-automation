# AI Tech Shorts — Zero-Rupee Cloud Automation

This repository automates a daily faceless AI/technology YouTube Shorts pipeline.

Daily:
RSS + YouTube research
→ rank topics
→ update content_log.xlsx
→ Gemini creates original script + story-specific video prompt
→ Gemini TTS creates narration
→ FFmpeg/Pillow creates a 9:16 Short with motion graphics, subtitles and original procedural music
→ YouTube Data API uploads it
→ GitHub Actions repeats daily

Important:
- No workflow can guarantee viral views, likes or revenue.
- YouTube's current monetization policy excludes repetitive/mass-produced inauthentic content.
- The stable zero-cost renderer does not depend on unlimited text-to-video generation. Photorealistic video generation remains compute/quota dependent.

## Free stack

- GitHub Actions: standard GitHub-hosted runners are free and unlimited for public repositories.
- Gemini 3.8 Flash: editor/script model on the current free tier.
- Gemini 3.8 Flash-Lite TTS: natural narration on the current free tier.
- YouTube Data API: research + upload.
- FFmpeg + Pillow: rendering.
- openpyxl: actual .xlsx research/content ledger.
- Google News RSS: discovery.

## 1. Create a PUBLIC GitHub repository

Public is recommended for free/unlimited standard runner usage.

Never commit:
- API keys
- OAuth client files
- token.json

Upload this project to the repository.

## 2. Create the Gemini API key

Create a Gemini API key in Google AI Studio.

GitHub → Settings → Secrets and variables → Actions

Create secret:

GEMINI_API_KEY

Create repository variables:

GEMINI_MODEL=gemini-3.8-flash
GEMINI_TTS_MODEL=gemini-3.8-flash-lite-tts
TTS_VOICE=Kore

## 3. Create YouTube API credentials

Google Cloud Console:

1. Create/select a project.
2. Enable YouTube Data API v3.
3. Create an API key.
4. Add the key to GitHub Secrets as YOUTUBE_API_KEY.
5. Configure OAuth consent screen.
6. Create OAuth Client ID → Desktop app.
7. Download the OAuth JSON as client_secret.json.

Upload authorization scope:

https://www.googleapis.com/auth/youtube.upload

## 4. Connect YOUR YouTube channel

This is a one-time authorization.

On a computer:

```bash
pip install -r requirements.txt
python auth_once.py
```

A Google authorization page opens.

Sign into the Google account that owns the intended YouTube channel and approve the upload permission.

The script creates token.json.

Copy the COMPLETE contents of token.json into:

GitHub → Settings → Secrets and variables → Actions → New repository secret

Name:

YOUTUBE_TOKEN_JSON

The workflow then uses the refresh token to upload to that channel.

If several channels are attached to the same Google account, authorize the intended channel.

## 5. Important YouTube upload restriction

YouTube currently states that uploads through videos.insert from unverified API projects created after July 28, 2020 are restricted to private viewing until the API project passes the required audit.

Start with repository variable:

YOUTUBE_PRIVACY_STATUS=private

After the public-upload restriction is cleared, change it to:

YOUTUBE_PRIVACY_STATUS=public

## 6. Excel research database

Every successful run creates/updates:

content_log.xlsx

Sheets:
- Research
- Daily Picks
- Video Queue
- Published

Video Queue includes:
- title
- hook
- full script
- story-specific video prompt
- description
- hashtags
- status

GitHub Actions commits the workbook back to the repository, so it can be opened in Microsoft Excel.

## 7. Daily schedule

.github/workflows/daily.yml schedules the pipeline at:

19:00 IST = 13:30 UTC

GitHub scheduled workflows can be delayed, so treat this as a daily publishing window.

You can also run it manually from:
Actions → Daily AI Tech Short → Run workflow.

## 8. Video output

The default Short is:
- 1080x1920
- 30 FPS
- approximately 45–55 seconds
- natural TTS narration
- quiet original background music
- subtitles
- motion graphics
- source/takeaway card
- synthetic-media disclosure in the YouTube API

The generated video_prompt is also saved for an optional cinematic video-model stage.

## 9. Quality/monetization guardrails

The workflow does not:
- copy creator scripts
- reuse creator videos
- scrape TikTok/Reels
- invent quotes/statistics
- buy views or likes
- produce hundreds of identical videos

It should publish a distinct story, explanation and scene plan every day.

## 10. First test

Keep YOUTUBE_PRIVACY_STATUS=public.

Run the workflow manually.

Verify:
1. content_log.xlsx updates.
2. output/video.mp4 appears in the workflow artifact.
3. output/story.json appears.
4. YouTube Studio shows a private upload.

Only then enable public publishing.
