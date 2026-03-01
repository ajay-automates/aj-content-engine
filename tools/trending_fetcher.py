"""AJ Content Engine — Trending News Fetcher
Sources: Serper API (Google), Reddit (r/artificial, r/MachineLearning, r/LocalLLaMA), HackerNews
"""
import os, asyncio, httpx, logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("trending")

SERPER_KEY = os.getenv("SERPER_API_KEY", "")
REDDIT_SUBS = ["artificial", "MachineLearning", "LocalLLaMA", "ChatGPT"]

SERPER_QUERIES = {
    "breaking": ["AI news today", "artificial intelligence breaking news"],
    "tools": ["new AI tools launched", "AI product launch 2026"],
    "startups": ["AI startup funding", "AI company raised Series"],
    "research": ["AI research paper breakthrough", "large language model new"],
}


async def fetch_serper(query: str, num: int = 8) -> list[dict]:
    """Search Google via Serper API."""
    if not SERPER_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://google.serper.dev/news",
                headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": num, "tbs": "qdr:d"},
            )
            data = resp.json()
            results = []
            for item in data.get("news", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "image": item.get("imageUrl") or item.get("thumbnailUrl"),
                    "source": "serper",
                    "source_name": item.get("source", ""),
                    "time_ago": item.get("date", "Recent"),
                    "score": None,
                })
            return results
    except Exception as e:
        logger.error(f"Serper error for '{query}': {e}")
        return []


async def fetch_reddit(subreddit: str, limit: int = 10) -> list[dict]:
    """Fetch hot posts from a subreddit."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://www.reddit.com/r/{subreddit}/hot.json",
                params={"limit": limit, "raw_json": 1},
                headers={"User-Agent": "AJContentEngine/1.0"},
            )
            data = resp.json()
            results = []
            for post in data.get("data", {}).get("children", []):
                d = post.get("data", {})
                if d.get("stickied"):
                    continue
                created = d.get("created_utc", 0)
                delta = datetime.utcnow() - datetime.utcfromtimestamp(created) if created else timedelta(0)
                if delta.days > 0:
                    time_ago = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    time_ago = f"{delta.seconds // 3600}h ago"
                else:
                    time_ago = f"{delta.seconds // 60}m ago"
                thumb = d.get("thumbnail")
                image = thumb if thumb and thumb.startswith("http") else None
                results.append({
                    "title": d.get("title", ""),
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                    "snippet": (d.get("selftext") or "")[:200],
                    "image": image,
                    "source": "reddit",
                    "source_name": f"r/{subreddit}",
                    "subreddit": subreddit,
                    "time_ago": time_ago,
                    "score": d.get("score", 0),
                })
            return results
    except Exception as e:
        logger.error(f"Reddit error for r/{subreddit}: {e}")
        return []


async def fetch_hackernews(limit: int = 10) -> list[dict]:
    """Fetch top AI-related stories from HackerNews via Algolia."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": "AI OR LLM OR GPT OR Claude OR artificial intelligence",
                    "tags": "story",
                    "numericFilters": "points>50",
                    "hitsPerPage": limit,
                },
            )
            data = resp.json()
            results = []
            for hit in data.get("hits", []):
                created = hit.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    delta = datetime.now(dt.tzinfo) - dt
                    if delta.days > 0:
                        time_ago = f"{delta.days}d ago"
                    elif delta.seconds > 3600:
                        time_ago = f"{delta.seconds // 3600}h ago"
                    else:
                        time_ago = f"{delta.seconds // 60}m ago"
                except:
                    time_ago = "Recent"
                results.append({
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "snippet": "",
                    "image": None,
                    "source": "hackernews",
                    "source_name": "Hacker News",
                    "time_ago": time_ago,
                    "score": hit.get("points", 0),
                })
            return results
    except Exception as e:
        logger.error(f"HackerNews error: {e}")
        return []


def categorize_topic(topic: dict, query_category: Optional[str] = None) -> str:
    """Assign a topic to a feed category."""
    if query_category:
        return query_category
    title = (topic.get("title") or "").lower()
    snippet = (topic.get("snippet") or "").lower()
    text = title + " " + snippet
    if any(w in text for w in ["launch", "release", "tool", "app", "product", "api", "open source", "github"]):
        return "tools"
    if any(w in text for w in ["paper", "research", "arxiv", "benchmark", "model", "training", "weights"]):
        return "research"
    if any(w in text for w in ["funding", "raise", "startup", "series", "valuation", "yc", "vc"]):
        return "startups"
    if topic.get("source") in ("reddit", "hackernews"):
        return "community"
    return "breaking"


async def fetch_all_trending(page: int = 0, per_page: int = 40) -> dict:
    """Fetch trending topics from all sources, categorized for the feed."""
    tasks = []
    for cat, queries in SERPER_QUERIES.items():
        for q in queries:
            tasks.append(("serper", cat, fetch_serper(q, num=6)))
    for sub in REDDIT_SUBS:
        tasks.append(("reddit", None, fetch_reddit(sub, limit=8)))
    tasks.append(("hackernews", None, fetch_hackernews(limit=12)))

    raw_results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

    all_topics = []
    seen_titles = set()
    for i, result in enumerate(raw_results):
        if isinstance(result, Exception):
            logger.error(f"Source error: {result}")
            continue
        source_type, forced_cat, _ = tasks[i]
        for topic in result:
            title_key = topic["title"].lower().strip()[:60]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            topic["category"] = categorize_topic(topic, forced_cat)
            if not topic.get("why_trending"):
                topic["why_trending"] = topic.get("snippet") or f"Trending on {topic.get('source_name', topic.get('source', 'the web'))}"
            all_topics.append(topic)

    all_topics.sort(key=lambda t: (t.get("score") or 0), reverse=True)
    start = page * per_page
    end = start + per_page
    return {"topics": all_topics[start:end], "total": len(all_topics), "page": page, "has_more": end < len(all_topics)}
