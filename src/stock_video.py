import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUTPUT = Path("output")
STOCK_DIR = OUTPUT / "stock"
STOCK_DIR.mkdir(parents=True, exist_ok=True)

# After Pixabay returns 403 once, stop retrying it during this run.
_pixabay_disabled = False


def _slug(text):
    text = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        str(text),
    ).strip("_")

    return text[:60] or "stock"


def _request_json(url, timeout=30):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "AI-Tech-Daily/1.0 "
                "(https://github.com/kapilvarunbabu-g/"
                "ai-youtube-automation)"
            ),
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def _download_file(
    url,
    destination,
    timeout=120,
):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "AI-Tech-Daily/1.0 "
                "(https://github.com/kapilvarunbabu-g/"
                "ai-youtube-automation)"
            ),
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:

        with destination.open("wb") as output:
            while True:
                chunk = response.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                output.write(chunk)


def _pixabay(
    query,
    index,
):
    global _pixabay_disabled

    api_key = os.getenv(
        "PIXABAY_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "PIXABAY_API_KEY is missing."
        )

    if _pixabay_disabled:
        raise RuntimeError(
            "Pixabay disabled after previous 403."
        )

    params = urllib.parse.urlencode(
        {
            "key": api_key,
            "q": query[:100],
            "video_type": "film",
            "per_page": 12,
            "safesearch": "true",
            "order": "popular",
        }
    )

    url = (
        "https://pixabay.com/api/videos/?"
        + params
    )

    try:
        data = _request_json(
            url,
            timeout=30,
        )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        ).strip()

        if exc.code == 403:
            _pixabay_disabled = True

            raise RuntimeError(
                "Pixabay API returned HTTP 403. "
                f"Response: {body[:300]}"
            ) from exc

        raise RuntimeError(
            f"Pixabay API HTTP {exc.code}: "
            f"{body[:300]}"
        ) from exc

    videos = data.get(
        "hits",
        [],
    )

    ranked = []

    for item in videos:
        files = item.get(
            "videos",
            {},
        )

        video = (
            files.get("medium")
            or files.get("small")
            or files.get("large")
        )

        if not video:
            continue

        if not video.get("url"):
            continue

        width = int(
            video.get("width", 0)
            or 0
        )

        height = int(
            video.get("height", 0)
            or 0
        )

        ranked.append(
            (
                width * height,
                item,
                video,
            )
        )

    if not ranked:
        raise RuntimeError(
            f"No usable Pixabay video for: {query}"
        )

    _, item, video = max(
        ranked,
        key=lambda x: x[0],
    )

    destination = (
        STOCK_DIR
        / f"{index:02d}_{_slug(query)}_pixabay.mp4"
    )

    _download_file(
        video["url"],
        destination,
    )

    return (
        destination,
        {
            "provider": "Pixabay",
            "creator": item.get(
                "user",
                "Pixabay contributor",
            ),
            "page_url": item.get(
                "pageURL",
                "",
            ),
            "query": query,
        },
    )


def _wikimedia_commons(
    query,
    index,
):
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrlimit": 20,
            "gsrsearch": query,
            "prop": "imageinfo",
            "iiprop": (
                "url|mime|size|user|mediatype"
            ),
        }
    )

    url = (
        "https://commons.wikimedia.org/"
        "w/api.php?"
        + params
    )

    data = _request_json(
        url,
        timeout=30,
    )

    pages = (
        data
        .get("query", {})
        .get("pages", {})
    )

    candidates = []

    for page in pages.values():

        infos = (
            page.get("imageinfo")
            or []
        )

        if not infos:
            continue

        info = infos[0]

        mime = str(
            info.get(
                "mime",
                "",
            )
        )

        file_url = info.get(
            "url"
        )

        if not file_url:
            continue

        if not mime.startswith(
            "video/"
        ):
            continue

        size = int(
            info.get(
                "size",
                0,
            )
            or 0
        )

        # Avoid very large archival files.
        if (
            size
            and size > 80 * 1024 * 1024
        ):
            continue

        mp4_webm = (
            1
            if mime in {
                "video/mp4",
                "video/webm",
            }
            else 0
        )

        candidates.append(
            (
                mp4_webm,
                -size if size else 0,
                page,
                info,
            )
        )

    if not candidates:
        raise RuntimeError(
            "No usable Wikimedia Commons "
            f"video found for: {query}"
        )

    _, _, page, info = max(
        candidates,
        key=lambda x: (
            x[0],
            x[1],
        ),
    )

    mime = info.get(
        "mime",
        "video/webm",
    )

    extension = (
        ".mp4"
        if mime == "video/mp4"
        else ".webm"
    )

    destination = (
        STOCK_DIR
        / f"{index:02d}_{_slug(query)}_commons"
        f"{extension}"
    )

    _download_file(
        info["url"],
        destination,
    )

    title = str(
        page.get(
            "title",
            "",
        )
    )

    page_url = (
        "https://commons.wikimedia.org/wiki/"
        + urllib.parse.quote(
            title,
            safe=":/",
        ).replace(
            "%3A",
            ":",
        )
    )

    return (
        destination,
        {
            "provider": "Wikimedia Commons",
            "creator": info.get(
                "user",
                "Wikimedia Commons contributor",
            ),
            "page_url": page_url,
            "query": query,
        },
    )


def search_and_download(
    query,
    index,
):
    query = " ".join(
        str(query).split()
    ).strip()

    if not query:
        query = (
            "technology artificial intelligence"
        )

    # First choice: Pixabay.
    try:
        return _pixabay(
            query,
            index,
        )

    except Exception as exc:
        print(
            f"Pixabay unavailable for "
            f"'{query}': {exc}"
        )

    # Fallback: Wikimedia Commons.
    print(
        f"Using Wikimedia Commons for: {query}"
    )

    return _wikimedia_commons(
        query,
        index,
    )
