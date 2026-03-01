"""AJ Content Engine — Twitter Video Scanner (Serper-powered)
Finds tweets with native video from AI company accounts using Serper API
(Google search for site:x.com). No Twitter API needed — uses your existing
Serper key at zero extra cost.

Flow: Search Serper for "site:x.com [account] video" → filter results that
are actual tweet URLs → return as video-ready feed items for yt-dlp download.
"""
import os
import re
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("twitter_video_scanner")

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# ─── ACCOUNTS TO TRACK ────────────────────────────────────────────
TRACKED_ACCOUNTS = {
    "official": [
        "AnthropicAI", "OpenAI", "GoogleAI", "GoogleDeepMind",
        "MetaAI", "nvidia", "MistralAI",
        "HuggingFace", "StabilityAI", "RunwayML",
        "perplexity_ai", "CohereAI", "Apple",
    ],
    "creators": [
        "mattshumer_", "DrJimFan", "karpathy",
        "swyx", "AiBreakfast", "maboreshumer_",
        "ElaborI2go", "YannLeCun",
    ],
    "news": [
        "TheAIGRID", "ai_for_success",
        "technaborReview",
    ],
}

# Build search queries — group accounts by tier for focused searches
SEARCH_QUERIES = [
    # Official company announcements with video
    "site:x.com (AnthropicAI OR OpenAI OR GoogleAI OR GoogleDeepMind) video",
    "site:x.com (MetaAI OR nvidia OR MistralAI OR HuggingFace) video",
    "site:x.com (StabilityAI OR RunwayML OR perplexity_ai OR Apple) AI video",
    # Creator posts with demos/videos
    "site:x.com (DrJimFan OR karpathy OR mattshumer_ OR swyx) AI demo video",
    # Broader AI video tweets (catches trending posts)
    "site:x.com AI announcement video demo 2025",
    "site:x.com new AI tool launch video demo",
]


# ═══════════════════════════════════════════════════════════════════
#  SERPER-POWERED TWITTER VIDEO SEARCH
# ═══════════════════════════════════════════════════════════════════

async def fetch_video_tweets(max_results: int = 20, hours_back: int = 72) -> list[dict]:
    """Fetch recent tweets with video from AI accounts via Serper API.
    Uses Google search with site:x.com to find tweet URLs, then
    enriches them with metadata for the feed."""
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set — cannot scan Twitter videos")
        return []

    # Run all search queries in parallel
    tasks = [_search_serper_twitter(q, num=8) for q in SEARCH_QUERIES]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for result in batch_results:
        if isinstance(result, list):
            all_results.extend(result)

    # Deduplicate by tweet URL
    seen_urls = set()
    unique = []
    for item in all_results:
        url_key = item.get("url", "").split("?")[0].lower()
        if url_key and url_key not in seen_urls:
            seen_urls.add(url_key)
            unique.append(item)

    # Sort by position score (Serper rank) — higher ranked = more relevant
    unique.sort(key=lambda x: x.get("rank_score", 0), reverse=True)

    return unique[:max_results]


async def _search_serper_twitter(query: str, num: int = 8) -> list[dict]:
    """Search Serper for Twitter/X posts matching query."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": num, "tbs": "qdr:w"},  # Last week
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        organic = data.get("organic", [])

        for i, item in enumerate(organic):
            link = item.get("link", "")

            # Only keep actual tweet URLs (not profile pages, lists, etc.)
            if not _is_tweet_url(link):
                continue

            # Extract username and tweet ID from URL
            username, tweet_id = _parse_tweet_url(link)
            if not username:
                continue

            title = item.get("title", "")
            snippet = item.get("snippet", "")

            # Check if this looks like it has video content
            # (Serper snippets often mention "video" or the title indicates media)
            text_lower = (title + " " + snippet).lower()
            has_video_signal = any(w in text_lower for w in [
                "video", "watch", "demo", "launch", "introducing", "announcing",
                "new", "released", "shipped", "built", "check out", "here's",
                "thread", "clip", "preview", "reveal", "showcase",
            ])

            # Get thumbnail if available
            thumbnail = ""
            if item.get("thumbnailUrl"):
                thumbnail = item["thumbnailUrl"]
            elif item.get("imageUrl"):
                thumbnail = item["imageUrl"]

            # Determine tier
            tier = _get_account_tier(username)

            # Clean title — remove "on X" / "on Twitter" suffixes
            clean_title = _clean_serper_title(title, snippet, username)

            # Rank score: position in results + video signal bonus + tier bonus
            rank_score = (num - i) * 10  # Higher rank = more points
            if has_video_signal:
                rank_score += 50
            if tier == "official":
                rank_score += 30
            elif tier == "creator":
                rank_score += 15

            results.append({
                "tweet_id": tweet_id or str(uuid.uuid4())[:12],
                "title": clean_title,
                "full_text": snippet,
                "url": link,
                "video_url": "",  # Will be resolved by yt-dlp on download
                "video_thumbnail": thumbnail,
                "video_duration": 0,
                "video_duration_str": "",
                "author": _format_display_name(username),
                "username": username,
                "avatar": "",
                "verified": tier == "official",
                "tier": tier,
                "likes": 0,
                "retweets": 0,
                "views": 0,
                "engagement": 0,
                "views_str": "",
                "likes_str": "",
                "retweets_str": "",
                "time_ago": item.get("date", "Recent"),
                "rank_score": rank_score,
                "has_video_signal": has_video_signal,
                "source": "twitter_video",
                "source_name": f"@{username}",
                "category": "video_ready",
            })

        return results

    except Exception as e:
        logger.error("Serper Twitter search error: %s", e)
        return []


# Also search Serper Videos endpoint for Twitter video content
async def _search_serper_twitter_videos(query: str, num: int = 5) -> list[dict]:
    """Search Serper Videos endpoint for Twitter/X video content."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://google.serper.dev/videos",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": num},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for i, v in enumerate(data.get("videos", [])):
            link = v.get("link", "")
            if not _is_tweet_url(link):
                continue

            username, tweet_id = _parse_tweet_url(link)
            if not username:
                continue

            tier = _get_account_tier(username)
            duration = v.get("duration", "")

            results.append({
                "tweet_id": tweet_id or str(uuid.uuid4())[:12],
                "title": _clean_serper_title(v.get("title", ""), v.get("snippet", ""), username),
                "full_text": v.get("snippet", ""),
                "url": link,
                "video_url": "",
                "video_thumbnail": v.get("imageUrl") or v.get("thumbnailUrl", ""),
                "video_duration": 0,
                "video_duration_str": duration or "",
                "author": _format_display_name(username),
                "username": username,
                "avatar": "",
                "verified": tier == "official",
                "tier": tier,
                "likes": 0,
                "retweets": 0,
                "views": 0,
                "engagement": 0,
                "views_str": "",
                "likes_str": "",
                "retweets_str": "",
                "time_ago": v.get("date", "Recent"),
                "rank_score": (num - i) * 10 + 40,  # Video endpoint gets bonus
                "has_video_signal": True,
                "source": "twitter_video",
                "source_name": f"@{username}",
                "category": "video_ready",
            })

        return results
    except Exception as e:
        logger.error("Serper Twitter videos error: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _is_tweet_url(url: str) -> bool:
    """Check if URL is an actual tweet (not a profile, list, search, etc.)."""
    patterns = [
        r'https?://(x\.com|twitter\.com)/\w+/status/\d+',
    ]
    return any(re.match(p, url) for p in patterns)


def _parse_tweet_url(url: str) -> tuple[str, str]:
    """Extract username and tweet ID from a tweet URL."""
    match = re.search(r'(?:x\.com|twitter\.com)/(\w+)/status/(\d+)', url)
    if match:
        return match.group(1), match.group(2)
    return "", ""


def _clean_serper_title(title: str, snippet: str, username: str) -> str:
    """Clean Serper search result title into a usable topic title."""
    # Remove common suffixes
    for suffix in [" on X", " / X", " / Twitter", " on Twitter",
                   f" (@{username})", f"({username})", " - X", " - Twitter"]:
        title = title.replace(suffix, "")

    # Remove username prefix patterns
    title = re.sub(r'^[\w\s]+ on X:\s*["\u201c]?', '', title)
    title = re.sub(r'^[\w\s]+ \(@\w+\):\s*', '', title)

    # Remove surrounding quotes
    title = title.strip('""\u201c\u201d\'')

    # If title is too short after cleaning, use snippet
    if len(title) < 15 and snippet:
        title = snippet.split('.')[0].strip()

    # Remove URLs from title
    title = re.sub(r'https?://\S+', '', title).strip()

    # Truncate
    if len(title) > 120:
        title = title[:117] + "..."

    return title if title else f"Post by @{username}"


def _get_account_tier(username: str) -> str:
    """Determine which tier an account belongs to."""
    lower = username.lower()
    for handle in TRACKED_ACCOUNTS.get("official", []):
        if handle.lower() == lower:
            return "official"
    for handle in TRACKED_ACCOUNTS.get("creators", []):
        if handle.lower() == lower:
            return "creator"
    for handle in TRACKED_ACCOUNTS.get("news", []):
        if handle.lower() == lower:
            return "news"
    # Default: check if it looks like a company account
    company_keywords = ["ai", "lab", "tech", "deep", "meta", "google", "open", "nvidia"]
    if any(kw in lower for kw in company_keywords):
        return "official"
    return "creator"


def _format_display_name(username: str) -> str:
    """Convert username to a display-friendly name."""
    known = {
        "anthropicai": "Anthropic", "openai": "OpenAI",
        "googleai": "Google AI", "googledeepmind": "Google DeepMind",
        "metaai": "Meta AI", "nvidia": "NVIDIA",
        "mistralai": "Mistral AI", "huggingface": "Hugging Face",
        "stabilityai": "Stability AI", "runwayml": "Runway",
        "perplexity_ai": "Perplexity", "cohereai": "Cohere",
        "apple": "Apple", "drjimfan": "Jim Fan",
        "karpathy": "Andrej Karpathy", "yannlecun": "Yann LeCun",
        "swyx": "swyx", "mattshumer_": "Matt Shumer",
        "theaigrid": "The AI Grid", "ai_for_success": "AI for Success",
    }
    return known.get(username.lower(), username)


def _format_count(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    if count > 0:
        return str(count)
    return ""
