import json
import time

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


def is_transient_gemini_error(exc):
    text = str(exc).upper()

    transient_errors = [
        "408",
        "429",
        "500",
        "502",
        "503",
        "504",
        "UNAVAILABLE",
        "RESOURCE_EXHAUSTED",
        "INTERNAL",
        "BAD_GATEWAY",
        "GATEWAY_TIMEOUT",
    ]

    return any(error in text for error in transient_errors)


def generate_with_retry(client, model_names, prompt):
    last_error = None

    for model_name in model_names:
        print(f"Trying Gemini model: {model_name}")

        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.65,
                    ),
                )

                print(f"Gemini success with model: {model_name}")
                return response

            except Exception as exc:
                last_error = exc

                if not is_transient_gemini_error(exc):
                    raise

                if attempt == 3:
                    print(
                        f"Gemini model {model_name} failed after "
                        f"4 attempts. Error: {exc}"
                    )
                    break

                wait_seconds = 5 * (2 ** attempt)

                print(
                    f"Temporary Gemini error on {model_name}. "
                    f"Retrying in {wait_seconds}s "
                    f"(attempt {attempt + 1}/4)..."
                )

                time.sleep(wait_seconds)

        print(f"Trying fallback model after {model_name}.")

    raise last_error


def choose_and_write_story(pack):
    research = {
        "news": pack["candidates"][:90],
        "youtube_trends": pack["youtube_trends"][:25],
    }

    language = env("CONTENT_LANGUAGE", "Telugu")

    prompt = EDITORIAL + "\n\nTARGET LANGUAGE: " + language + "\n"

    prompt += f"""
CRITICAL LANGUAGE RULES:

- The spoken narration MUST be entirely in {language}.
- Write the title, hook, script, scene text, captions and description in {language}.
- Use natural, conversational Telugu suitable for a YouTube Shorts audience.
- Do NOT translate word-for-word from English.
- Technology names such as AI, Gemini, OpenAI, Apple, Microsoft, NVIDIA and ChatGPT may remain in English when that sounds natural.
- Do not use English sentences in the narration.
- The audience should understand the complete story without needing English.

TODAY'S RESEARCH:
""" + json.dumps(
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
  "voice_style": "warm, natural, energetic Telugu technology news presenter",
  "video_prompt": "...",
  "scenes": [
    {
      "on_screen_text": "...",
      "visual_concept": "...",
      "stock_search_query": "...",
      "caption": "...",
      "seconds": 5
    }
  ],
  "description": "...",
  "hashtags": ["#AI", "#Technology", "#తెలుగు"],
  "tags": ["ai", "technology", "telugu tech"],
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
- The narration must be natural Telugu.
- The first sentence must be a strong Telugu hook.
- Each scene must have short, readable Telugu on-screen text, preferably under 45 characters.
- Each scene MUST include a concise English "stock_search_query".
- The stock_search_query must contain 3–7 concrete keywords describing realistic footage relevant to that scene.
- Prefer real-world footage such as data centers, smartphones, developers, robots, factories, offices, chips, servers or people using technology.
- Never use the same stock_search_query for all scenes.
- Captions must match the Telugu narration.
- Avoid long paragraphs on screen.
- Explain what changed and why it matters.
- End with a useful takeaway.
- The video_prompt must describe a polished 9:16 vertical short.
- Include natural camera motion, human-like pacing, clean typography,
  narration, quiet background music, burned-in subtitles,
  transitions, source card and final takeaway.
- If evidence is weak, return "publish": false.
'''

    client = genai.Client(
        api_key=env("GEMINI_API_KEY", required=True)
    )

    primary_model = env(
        "GEMINI_MODEL",
        "gemini-3.8-flash"
    )

    # Stable fallback model if the primary model is temporarily overloaded.
    model_names = [
        primary_model,
        "gemini-3.7-flash",
    ]

    # Remove duplicate model names while preserving order.
    model_names = list(dict.fromkeys(model_names))

    response = generate_with_retry(
        client,
        model_names,
        prompt,
    )

    story = json.loads(response.text)

    if not story.get("publish"):
        raise RuntimeError(
            "Editorial gate rejected today's story."
        )

    if float(story.get("confidence", 0)) < 0.80:
        raise RuntimeError(
            "Editorial confidence below 0.80."
        )

    if len(story.get("script", "").split()) < 85:
        raise RuntimeError(
            "Script is too short."
        )

    if len(story.get("scenes", [])) < 8:
        raise RuntimeError(
            "At least 8 scenes are required."
        )

    if language.lower() == "telugu":
        has_telugu = any(
            "\u0c00" <= ch <= "\u0c7f"
            for ch in story.get("script", "")
        )

        if not has_telugu:
            raise RuntimeError(
                "The generated narration is not in Telugu."
            )

    write_json(
        OUTPUT / "story.json",
        story
    )

    return story
