"""AJ Content Engine — Twitter Video Scanner
Scans official AI company accounts, AI creators, and AI news accounts
for tweets that contain NATIVE VIDEO attachments. These become
video-ready content topics — the video B-roll is already included.

Flow: Scan accounts → filter for video tweets → return as feed items
with tweet text as topic + video URL ready for yt-dlp download.
"""
import os
import re
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger("twitter_video_scanner")

TWITTER_BEARER = os.getenv("TWITTER_BEARER_TOKEN", "")

# ─── ACCOUNTS TO TRACK ────────────────────────────────────────────
# 3 tiers: official product accounts, AI creators, AI news aggregators

TRACKED_ACCOUNTS = {
    # Tier 1: Official AI company accounts (highest priority)
    "official": [
        "AnthropicAI", "OpenAI", "GoogleAI", "GoogleDeepMind",
        "Meta", "MetaAI", "nvidia", "xaborai", "MistralAI",
        "HuggingFace", "StabilityAI", "midaborney", "RunwayML",
        "peraborexity_ai", "CohereAI", "DeepSeek_AI",
        "Apple",  # occasional AI announcements
    ],
    # Tier 2: AI creators / builders / researchers
    "creators": [
        "mattshumer_", "DrJimFan", "kaborarpathy",
        "emaborllad", "swyx", "AiBreakfast",
        "mattaborolfe", "ElaborI2go", "RichaborardSocher",
        "YannLeCun", "AlaborphaSignalAI", "risaborbSRK",
    ],
    # Tier 3: AI news / aggregator accounts
    "news": [
        "TheAIGRID", "ai_for_success", "aiaborupdate",
        "Sababoroo_Stein", "technaborReview", "vergeabortech",
    ],
}

# Flatten all handles for API query
ALL_HANDLES = []
for tier in TRACKED_ACCOUNTS.values():
    ALL_HANDLES.extend(tier)


# ═══════════════════════════════════════════════════════════════════
#  TWITTER API v2: Search for video tweets from tracked accounts
# ═══════════════════════════════════════════════════════════════════

async def fetch_video_tweets(max_results: int = 20, hours_back: int = 72) -> list[dict]:
    """Fetch recent tweets WITH VIDEO from tracked AI accounts.
    Uses Twitter API v2 recent search with media filtering."""
    if not TWITTER_BEARER:
        logger.warning("TWITTER_BEARER_TOKEN not set — cannot scan Twitter videos")
        return []

    # Build the query: from any tracked account + has video
    # Twitter API limits query to 512 chars, so we batch accounts
    all_results = []

    # Split accounts into batches to stay under query length limit
    batches = _build_account_batches(ALL_HANDLES, max_per_batch=12)

    # Calculate time window
    start_time = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    tasks = [_fetch_batch(batch, start_time, max_results=max_results) for batch in batches]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in batch_results:
        if isinstance(result, list):
            all_results.extend(result)

    # Deduplicate by tweet ID
    seen = set()
    unique = []
    for item in all_results:
        if item["tweet_id"] not in seen:
            seen.add(item["tweet_id"])
            unique.append(item)

    # Sort by engagement (likes + retweets) descending
    unique.sort(key=lambda x: x.get("engagement", 0), reverse=True)

    return unique[:max_results]


async def _fetch_batch(handles: list[str], start_time: str, max_results: int = 20) -> list[dict]:
    """Fetch video tweets for a batch of account handles."""
    # Build query: (from:handle1 OR from:handle2 ...) has:videos -is:retweet
    from_clause = " OR ".join([f"from:{h}" for h in handles])
    query = f"({from_clause}) has:videos -is:retweet"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers={"Authorization": f"Bearer {TWITTER_BEARER}"},
                params={
                    "query": query,
                    "max_results": min(max_results, 100),
                    "start_time": start_time,
                    "sort_order": "relevancy",
                    "tweet.fields": "created_at,public_metrics,author_id,attachments,entities",
                    "expansions": "author_id,attachments.media_keys",
                    "media.fields": "type,url,preview_image_url,duration_ms,variants",
                    "user.fields": "username,name,profile_image_url,verified",
                },
            )

            if resp.status_code == 429:
                logger.warning("Twitter rate limited — skipping this batch")
                return []

            if resp.status_code != 200:
                logger.error("Twitter API error %d: %s", resp.status_code, resp.text[:300])
                return []

            data = resp.json()

        # Build lookups
        users = {}
        for u in data.get("includes", {}).get("users", []):
            users[u["id"]] = u

        media_map = {}
        for m in data.get("includes", {}).get("media", []):
            media_map[m["media_key"]] = m

        results = []
        for tweet in data.get("data", []):
            # Get media keys for this tweet
            media_keys = tweet.get("attachments", {}).get("media_keys", [])
            if not media_keys:
                continue

            # Find video media
            video_info = None
            for mk in media_keys:
                media = media_map.get(mk)
                if media and media.get("type") == "video":
                    video_info = media
                    break

            if not video_info:
                continue  # No video in this tweet

            # Get author info
            author = users.get(tweet.get("author_id"), {})
            username = author.get("username", "")
            name = author.get("name", "")
            avatar = author.get("profile_image_url", "")
            verified = author.get("verified", False)

            # Get engagement metrics
            metrics = tweet.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)
            views = metrics.get("impression_count", 0)
            engagement = likes + retweets

            # Get video URL (best quality variant)
            video_url = _extract_best_video_url(video_info)
            video_thumbnail = video_info.get("preview_image_url", "")
            video_duration_ms = video_info.get("duration_ms", 0)
            video_duration_sec = video_duration_ms // 1000 if video_duration_ms else 0

            # Format time
            time_ago = _format_tweet_time(tweet.get("created_at", ""))

            # Clean tweet text for use as a topic title
            text = tweet.get("text", "")
            clean_title = _clean_tweet_text(text)

            # Determine account tier
            tier = _get_account_tier(username)

            tweet_url = f"https://x.com/{username}/status/{tweet['id']}"

            results.append({
                "tweet_id": tweet["id"],
                "title": clean_title,
                "full_text": text,
                "url": tweet_url,
                "video_url": video_url,
                "video_thumbnail": video_thumbnail,
                "video_duration": video_duration_sec,
                "video_duration_str": f"{video_duration_sec // 60}:{video_duration_sec % 60:02d}" if video_duration_sec else "?",
                "author": name,
                "username": username,
                "avatar": avatar,
                "verified": verified,
                "tier": tier,
                "likes": likes,
                "retweets": retweets,
                "views": views,
                "engagement": engagement,
                "views_str": _format_count(views),
                "likes_str": _format_count(likes),
                "retweets_str": _format_count(retweets),
                "time_ago": time_ago,
                "source": "twitter_video",
                "source_name": f"@{username}",
                "category": "video_ready",
            })

        return results

    except Exception as e:
        logger.error("Twitter batch fetch error: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _build_account_batches(handles: list[str], max_per_batch: int = 12) -> list[list[str]]:
    """Split handles into batches to keep Twitter query under 512 char limit."""
    batches = []
    current = []
    for h in handles:
        current.append(h)
        if len(current) >= max_per_batch:
            batches.append(current)
            current = []
    if current:
        batches.append(current)
    return batches


def _extract_best_video_url(media: dict) -> str:
    """Extract the best quality video URL from Twitter media variants."""
    variants = media.get("variants", [])
    if not variants:
        return ""

    # Filter for mp4 variants and pick highest bitrate
    mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
    if mp4s:
        # Sort by bitrate descending
        mp4s.sort(key=lambda v: v.get("bit_rate", 0), reverse=True)
        return mp4s[0].get("url", "")

    # Fallback to any variant
    return variants[0].get("url", "")


def _clean_tweet_text(text: str) -> str:
    """Clean tweet text into a usable topic title.
    Removes URLs, @mentions at start, and truncates."""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text).strip()
    # Remove leading @mentions
    text = re.sub(r'^(@\w+\s*)+', '', text).strip()
    # Remove trailing whitespace and newlines, take first line
    lines = text.split('\n')
    first_line = lines[0].strip()
    # If first line is short and there's more, combine first two
    if len(first_line) < 30 and len(lines) > 1:
        first_line = first_line + " " + lines[1].strip()
    # Truncate
    if len(first_line) > 120:
        first_line = first_line[:117] + "..."
    return first_line if first_line else text[:120]


def _get_account_tier(username: str) -> str:
    """Determine which tier an account belongs to."""
    lower = username.lower()
    for handle in TRACKED_ACCOUNTS.get("official", []):
        if handle.lower() == lower:
            return "official"
    for handle in TRACKED_ACCOUNTS.get("creators", []):
        if handle.lower() == lower:
            return "creator"
    return "news"


def _format_tweet_time(created_at: str) -> str:
    """Format tweet timestamp into relative time."""
    if not created_at:
        return "Recent"
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        else:
            return f"{max(delta.seconds // 60, 1)}m ago"
    except Exception:
        return "Recent"


def _format_count(count: int) -> str:
    """Format large numbers for display."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    if count > 0:
        return str(count)
    return ""
