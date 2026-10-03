import json
from google import genai
from google.genai import types

from .common import env, OUTPUT, write_json

EDITORIAL = r'''
You are the chief editor of a faceless AI + technology YouTube Shorts channel.

The channel wins by explaining important developments clearly and originally,
not by copying news articles or other creators.

Rules:
1. Use only the supplied research evidence.
2. Do not invent statistics, quotes, launch dates or capabilities.
3. Prefer multiple independent sources where available.
4. Prefer primary company/developer sources when they are in the inputs.
5. Do not copy article or YouTuber wording.
6. Do not reuse creator footage.
7. Pick a story that is fresh and useful to the target audience.
8. Every episode needs a distinct angle and scene concept.
9. Do not use deceptive clickbait.
10. Write like a smart human technology creator: conversational and concise.
11. Avoid political persuasion, financial advice, medical advice and unsupported claims.
'''

def choose_and_write_story(pack):
    research = {
        "news": pack["candidates"][:90],
        "youtube_trends": pack["youtube_trends"][:25],
    }

    prompt = EDITORIAL + "\n\nTODAY'S RESEARCH:\n" + json.dumps(
        research,
        ensure_ascii=False,
    )

    prompt += r'''
Return ONLY valid JSON:

{
  "publish": true,
  "confidence": 0.0,
  "topic": "...",
  "title": "...",
  "hook": "...",
  "script": "...",
  "voice_style": "natural, energetic, conversational",
  "video_prompt": "...",
  "scenes": [
    {
      "on_screen_text": "...",
      "visual_concept": "...",
      "caption": "...",
      "seconds": 5
    }
  ],
  "description": "...",
  "hashtags": ["#AI", "#Technology"],
  "tags": ["ai", "technology"],
  "sources": [
    {"title": "...", "url": "..."}
  ],
  "contains_synthetic_media": true
}

Requirements:
- 40–55 seconds.
- 105–135 spoken words.
- 8 distinct scenes.
- Strong hook in the first sentence.
- Explain what changed and why it matters.
- End with a useful takeaway.
- The video_prompt must describe a realistic, polished 9:16 vertical short with:
  natural camera motion, human-like pacing, clean typography,
  narration, quiet background music, burned-in subtitles,
  transitions, source card and final takeaway.
- Save the story-specific video prompt even though the default renderer is local.
- If evidence is weak, return "publish": false.
'''

    client = genai.Client(
        api_key=env("GEMINI_API_KEY", required=True)
    )

    response = client.models.generate_content(
        model=env("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.65,
        ),
    )

    story = json.loads(response.text)

    if not story.get("publish"):
        raise RuntimeError("Editorial gate rejected today's story.")
    if float(story.get("confidence", 0)) < 0.80:
        raise RuntimeError("Editorial confidence below 0.80.")
    if len(story.get("script", "").split()) < 85:
        raise RuntimeError("Script is too short.")
    if len(story.get("scenes", [])) < 8:
        raise RuntimeError("At least 8 scenes are required.")

    write_json(OUTPUT / "story.json", story)
    return story
