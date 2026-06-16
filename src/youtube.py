"""YouTube Data API v3 fetcher for MoveUp Content Ops Bot."""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from googleapiclient.discovery import build

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

MOVEUP_CHANNELS = {
    "Netflu": "@Netflu",
    "ThePlayoffsTV": "@ThePlayoffsTV",
}

COMPETITOR_CHANNELS = {
    "BeFootball": "@BeFootball",
    "Oh My Goal": "@OhMyGoal",
}

ALL_CHANNELS = {**MOVEUP_CHANNELS, **COMPETITOR_CHANNELS}


def get_youtube_client():
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY environment variable is not set.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def resolve_channel_id(youtube, handle: str) -> str:
    """Resolve @handle to channel ID."""
    username = handle.lstrip("@")
    resp = youtube.channels().list(
        part="id,snippet",
        forHandle=username,
    ).execute()
    items = resp.get("items", [])
    if not items:
        raise ValueError(f"Channel not found for handle: {handle}")
    return items[0]["id"]


def fetch_last_n_videos(youtube, channel_id: str, n: int = 10) -> list[dict]:
    """Fetch the last n video IDs from a channel via the search endpoint."""
    search_resp = youtube.search().list(
        part="id",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=n,
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
    if not video_ids:
        return []

    videos_resp = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids),
    ).execute()

    results = []
    for item in videos_resp.get("items", []):
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        engagement_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0

        results.append({
            "video_id": item["id"],
            "title": snippet.get("title", ""),
            "published_at": snippet.get("publishedAt", ""),
            "description": snippet.get("description", "")[:300],
            "tags": snippet.get("tags", [])[:10],
            "duration": content.get("duration", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": engagement_rate,
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
        })
    return results


def fetch_channel_stats(youtube, channel_id: str) -> dict:
    """Fetch overall channel statistics."""
    resp = youtube.channels().list(
        part="statistics,snippet",
        id=channel_id,
    ).execute()
    items = resp.get("items", [])
    if not items:
        return {}
    stats = items[0].get("statistics", {})
    snippet = items[0].get("snippet", {})
    return {
        "name": snippet.get("title", ""),
        "description": snippet.get("description", "")[:200],
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "total_videos": int(stats.get("videoCount", 0)),
    }


def collect_all_data(channels: dict | None = None, n: int = 10) -> dict:
    """Collect data for all channels. Returns dict keyed by channel name."""
    if channels is None:
        channels = MOVEUP_CHANNELS

    youtube = get_youtube_client()
    result = {}
    for name, handle in channels.items():
        channel_id = resolve_channel_id(youtube, handle)
        stats = fetch_channel_stats(youtube, channel_id)
        videos = fetch_last_n_videos(youtube, channel_id, n)
        result[name] = {
            "channel_id": channel_id,
            "handle": handle,
            "stats": stats,
            "videos": videos,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    return result


def save_data(data: dict, path: str = "data/reports/latest.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_data(path: str = "data/reports/latest.json") -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)
