import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

OUTPUT = Path("output")
STOCK_DIR = OUTPUT / "stock"
STOCK_DIR.mkdir(parents=True, exist_ok=True)


def _slug(text):
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(text)).strip("_")
    return text[:60] or "stock"


def search_and_download(query, index):
    api_key = os.getenv("PIXABAY_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "PIXABAY_API_KEY is missing."
        )

    query = " ".join(str(query).split()).strip()

    if not query:
        query = "technology artificial intelligence"

    params = urllib.parse.urlencode(
        {
            "key": api_key,
            "q": query[:100],
            "video_type": "film",
            "per_page": 20,
        }
    )

    url = "https://pixabay.com/api/videos/?" + params

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AI-Tech-Daily/1.0"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    videos = data.get("hits", [])

    if not videos:
        raise RuntimeError(
            f"No Pixabay video found for: {query}"
        )

    ranked = []

    for item in videos:
        files = item.get("videos", {})

        candidates = []

        for name in ("large", "medium", "small"):
            video = files.get(name)

            if video and video.get("url"):
                candidates.append(video)

        if not candidates:
            continue

        chosen = max(
            candidates,
            key=lambda x: (
                x.get("width", 0)
                * x.get("height", 0),
                x.get("size", 0),
            ),
        )

        area = (
            chosen.get("width", 0)
            * chosen.get("height", 0)
        )

        ranked.append(
            (
                area,
                item,
                chosen,
            )
        )

    if not ranked:
        raise RuntimeError(
            f"Pixabay returned no usable video for: {query}"
        )

    _, item, video_file = max(
        ranked,
        key=lambda x: x[0]
    )

    destination = (
        STOCK_DIR
        / f"{index:02d}_{_slug(query)}.mp4"
    )

    with urllib.request.urlopen(
        video_file["url"],
        timeout=60
    ) as response:

        with destination.open(
            "wb"
        ) as output:

            while True:
                chunk = response.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                output.write(chunk)

    attribution = {
        "provider": "Pixabay",
        "creator": item.get(
            "user",
            "Pixabay contributor"
        ),
        "page_url": item.get(
            "pageURL",
            ""
        ),
        "query": query,
    }

    print(
        f"Downloaded Pixabay video: {query}"
    )

    return destination, attribution
