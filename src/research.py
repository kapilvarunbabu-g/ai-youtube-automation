from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
import feedparser
from googleapiclient.discovery import build

from .common import env, now_iso, write_json, OUTPUT

QUERIES = [
    "AI artificial intelligence",
    "OpenAI",
    "Google Gemini AI",
    "Microsoft Copilot AI",
    "NVIDIA AI",
    "AI agents",
    "AI coding tools",
    "open source AI",
    "robotics AI",
]

def rss_candidates(hours=36):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    seen = set()
    rows = []

    for q in QUERIES:
        url = (
            "https://news.google.com/rss/search?q="
            + quote_plus(q)
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        feed = feedparser.parse(url)

        for entry in feed.entries[:12]:
            t = entry.get("published_parsed") or entry.get("updated_parsed")
            published = (
                datetime(*t[:6], tzinfo=timezone.utc)
                if t
                else datetime.now(timezone.utc)
            )

            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()

            if (
                not title
                or not link
                or link in seen
                or published < cutoff
            ):
                continue

            seen.add(link)

            source_obj = entry.get("source") or {}
            source = (
                source_obj.get("title", "")
                if hasattr(source_obj, "get")
                else ""
            )

            rows.append({
                "kind": "news",
                "query": q,
                "title": title,
                "source": source,
                "url": link,
                "published_at": published.isoformat(),
                "summary": (entry.get("summary") or "")[:1800],
                "freshness_score": 1.0,
            })

    return rows

def youtube_velocity():
    api = build(
        "youtube",
        "v3",
        developerKey=env("YOUTUBE_API_KEY", required=True),
        cache_discovery=False,
    )

    after = (
        datetime.now(timezone.utc) - timedelta(hours=72)
    ).isoformat().replace("+00:00", "Z")

    videos = []

    for q in QUERIES[:7]:
        search = api.search().list(
            part="snippet",
            q=q,
            type="video",
            publishedAfter=after,
            order="viewCount",
            maxResults=5,
            regionCode="IN",
        ).execute()

        ids = [
            item["id"]["videoId"]
            for item in search.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

        if not ids:
            continue

        stats = api.videos().list(
            part="snippet,statistics",
            id=",".join(ids),
        ).execute()

        now = datetime.now(timezone.utc)

        for item in stats.get("items", []):
            published_dt = datetime.fromisoformat(
                item["snippet"]["publishedAt"].replace("Z", "+00:00")
            )

            age_h = max(
                0.25,
                (now - published_dt).total_seconds() / 3600,
            )

            stats_obj = item.get("statistics", {})
            views = int(stats_obj.get("viewCount", 0))
            likes = int(stats_obj.get("likeCount", 0))
            comments = int(stats_obj.get("commentCount", 0))

            engagement = (
                (likes + comments) / views
                if views else 0
            )

            videos.append({
                "kind": "youtube",
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "published_at": item["snippet"]["publishedAt"],
                "views": views,
                "likes": likes,
                "comments": comments,
                "views_per_hour": round(views / age_h, 2),
                "engagement_rate": round(engagement, 5),
            })

    videos.sort(
        key=lambda x: x["views_per_hour"],
        reverse=True,
    )
    return videos[:35]

def build_research_pack():
    news = rss_candidates()
    trends = youtube_velocity()

    top_velocity = (
        trends[0]["views_per_hour"]
        if trends else 1
    )

    candidates = []

    for item in news:
        query_words = set(item["query"].lower().split())
        title_words = set(item["title"].lower().split())

        candidates.append({
            **item,
            "topic_overlap": len(query_words & title_words),
            "source_count_hint": 1,
            "youtube_velocity_proxy": round(top_velocity, 2),
        })

    pack = {
        "generated_at": now_iso(),
        "candidates": candidates,
        "youtube_trends": trends,
    }

    write_json(OUTPUT / "research.json", pack)
    return pack
