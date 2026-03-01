"""AJ Content Engine — Trending News Fetcher
Sources: Serper API, Reddit, HackerNews, Product Hunt, ArXiv, Twitter/X, RSS Feeds
Total: 7 sources feeding the Netflix-style discovery feed.
"""
import os, asyncio, httpx, logging, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("trending")

SERPER_KEY = os.getenv("SERPER_API_KEY", "")
TWITTER_BEARER = os.getenv("TWITTER_BEARER_TOKEN", "")
REDDIT_SUBS = ["artificial", "MachineLearning", "LocalLLaMA", "ChatGPT"]

SERPER_QUERIES = {
    "breaking": ["AI news today", "artificial intelligence breaking news"],
    "tools": ["new AI tools launched", "AI product launch 2026"],
    "startups": ["AI startup funding", "AI company raised Series"],
    "research": ["AI research paper breakthrough", "large language model new"],
}

RSS_FEEDS = [
    {"url": "https://blog.anthropic.com/rss.xml", "name": "Anthropic Blog", "category": "breaking"},
    {"url": "https://blog.google/technology/ai/rss/", "name": "Google AI Blog", "category": "research"},
    {"url": "https://openai.com/blog/rss.xml", "name": "OpenAI Blog", "category": "breaking"},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "name": "TechCrunch AI", "category": "breaking"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "name": "The Verge AI", "category": "breaking"},
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "name": "Ars Technica", "category": "tools"},
    {"url": "https://deepmind.google/blog/rss.xml", "name": "DeepMind Blog", "category": "research"},
    {"url": "https://huggingface.co/blog/feed.xml", "name": "Hugging Face Blog", "category": "tools"},
    {"url": "https://www.marktechpost.com/feed/", "name": "MarkTechPost", "category": "research"},
    {"url": "https://venturebeat.com/category/ai/feed/", "name": "VentureBeat AI", "category": "startups"},
]


# ================================================================
# SOURCE 1: SERPER API (Google News)
# ================================================================

async def fetch_serper(query: str, num: int = 8) -> list[dict]:
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


# ================================================================
# SOURCE 2: REDDIT
# ================================================================

async def fetch_reddit(subreddit: str, limit: int = 10) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://www.reddit.com/r/{subreddit}/hot.json",
                params={"limit": limit, "raw_json": 1},
                headers={"User-Agent": "AJContentEngine/2.0"},
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


# ================================================================
# SOURCE 3: HACKERNEWS
# ================================================================

async def fetch_hackernews(limit: int = 10) -> list[dict]:
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
                except Exception:
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


# ================================================================
# SOURCE 4: PRODUCT HUNT (daily top AI products)
# ================================================================

async def fetch_producthunt(limit: int = 10) -> list[dict]:
    """Fetch today's top AI products from Product Hunt via their public feed."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.producthunt.com/feed",
                headers={"User-Agent": "AJContentEngine/2.0"},
            )
            results = []
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall(".//atom:entry", ns) or root.findall(".//item")
            if not entries:
                entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for entry in entries[:limit]:
                title = entry.findtext("atom:title", "", ns) or entry.findtext("title", "") or entry.findtext("{http://www.w3.org/2005/Atom}title", "")
                link_el = entry.find("atom:link", ns) or entry.find("link") or entry.find("{http://www.w3.org/2005/Atom}link")
                url = ""
                if link_el is not None:
                    url = link_el.get("href", "") or link_el.text or ""
                summary = entry.findtext("atom:summary", "", ns) or entry.findtext("description", "") or entry.findtext("{http://www.w3.org/2005/Atom}summary", "")
                # Filter for AI-related products
                text = (title + " " + summary).lower()
                ai_keywords = ["ai", "llm", "gpt", "machine learning", "neural", "deep learning",
                               "chatbot", "automation", "agent", "model", "nlp", "generative",
                               "copilot", "assistant", "language model", "diffusion", "transformer"]
                if not any(kw in text for kw in ai_keywords):
                    continue
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": summary[:200] if summary else "",
                    "image": None,
                    "source": "producthunt",
                    "source_name": "Product Hunt",
                    "time_ago": "Today",
                    "score": None,
                })
            return results
    except Exception as e:
        logger.error(f"Product Hunt error: {e}")
        return []


# ================================================================
# SOURCE 5: ARXIV (latest AI research papers)
# ================================================================

async def fetch_arxiv(limit: int = 10) -> list[dict]:
    """Fetch latest AI papers from ArXiv API."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "http://export.arxiv.org/api/query",
                params={
                    "search_query": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.CV",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": limit,
                },
            )
            results = []
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
                summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")[:200]
                link = ""
                for l in entry.findall("atom:link", ns):
                    if l.get("type") == "text/html":
                        link = l.get("href", "")
                        break
                if not link:
                    link_el = entry.find("atom:id", ns)
                    link = link_el.text if link_el is not None else ""
                published = entry.findtext("atom:published", "", ns)
                try:
                    dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    delta = datetime.now(dt.tzinfo) - dt
                    time_ago = f"{delta.days}d ago" if delta.days > 0 else "Today"
                except Exception:
                    time_ago = "Recent"
                # Get authors
                authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
                author_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    author_str += f" +{len(authors)-3} more"
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": summary,
                    "image": None,
                    "source": "arxiv",
                    "source_name": f"ArXiv — {author_str}" if author_str else "ArXiv",
                    "time_ago": time_ago,
                    "score": None,
                })
            return results
    except Exception as e:
        logger.error(f"ArXiv error: {e}")
        return []


# ================================================================
# SOURCE 6: TWITTER/X (trending AI posts)
# ================================================================

async def fetch_twitter(limit: int = 10) -> list[dict]:
    """Fetch recent popular AI tweets using Twitter API v2 search."""
    if not TWITTER_BEARER:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers={"Authorization": f"Bearer {TWITTER_BEARER}"},
                params={
                    "query": "(AI OR LLM OR GPT OR Claude OR artificial intelligence) -is:retweet lang:en",
                    "max_results": min(limit, 100),
                    "sort_order": "relevancy",
                    "tweet.fields": "created_at,public_metrics,author_id",
                    "expansions": "author_id",
                    "user.fields": "username,name",
                },
            )
            data = resp.json()
            # Build author lookup
            users = {}
            for u in data.get("includes", {}).get("users", []):
                users[u["id"]] = u
            results = []
            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                likes = metrics.get("like_count", 0)
                retweets = metrics.get("retweet_count", 0)
                if likes + retweets < 10:
                    continue  # Skip low-engagement tweets
                author = users.get(tweet.get("author_id"), {})
                username = author.get("username", "")
                name = author.get("name", "")
                created = tweet.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    delta = datetime.now(dt.tzinfo) - dt
                    if delta.days > 0:
                        time_ago = f"{delta.days}d ago"
                    elif delta.seconds > 3600:
                        time_ago = f"{delta.seconds // 3600}h ago"
                    else:
                        time_ago = f"{delta.seconds // 60}m ago"
                except Exception:
                    time_ago = "Recent"
                text = tweet.get("text", "")
                results.append({
                    "title": text[:120] + ("..." if len(text) > 120 else ""),
                    "url": f"https://x.com/{username}/status/{tweet['id']}" if username else "",
                    "snippet": text[:200],
                    "image": None,
                    "source": "twitter",
                    "source_name": f"@{username}" if username else "Twitter/X",
                    "time_ago": time_ago,
                    "score": likes + retweets,
                })
            return results
    except Exception as e:
        logger.error(f"Twitter error: {e}")
        return []


# ================================================================
# SOURCE 7: RSS FEEDS (Anthropic, Google AI, TechCrunch, etc.)
# ================================================================

async def fetch_rss_feed(feed: dict, limit: int = 5) -> list[dict]:
    """Fetch items from a single RSS/Atom feed."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(feed["url"], headers={"User-Agent": "AJContentEngine/2.0"})
            results = []
            root = ET.fromstring(resp.text)
            # Handle both RSS and Atom feeds
            items = root.findall(".//item")  # RSS
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            if not items:
                items = root.findall("atom:entry", ns)  # Atom
            if not items:
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:limit]:
                title = (
                    item.findtext("title") or
                    item.findtext("atom:title", "", ns) or
                    item.findtext("{http://www.w3.org/2005/Atom}title", "")
                ).strip()
                link = item.findtext("link") or ""
                if not link:
                    link_el = item.find("atom:link", ns) or item.find("{http://www.w3.org/2005/Atom}link")
                    if link_el is not None:
                        link = link_el.get("href", "") or link_el.text or ""
                desc = (
                    item.findtext("description") or
                    item.findtext("atom:summary", "", ns) or
                    item.findtext("{http://www.w3.org/2005/Atom}summary", "") or
                    ""
                )
                # Strip HTML tags from description
                import re
                desc = re.sub(r"<[^>]+>", "", desc).strip()[:200]
                # Try to get image from media/enclosure
                image = None
                enclosure = item.find("enclosure")
                if enclosure is not None and "image" in (enclosure.get("type") or ""):
                    image = enclosure.get("url")
                media = item.find("{http://search.yahoo.com/mrss/}thumbnail")
                if media is not None:
                    image = media.get("url")
                pub_date = (
                    item.findtext("pubDate") or
                    item.findtext("atom:published", "", ns) or
                    item.findtext("{http://www.w3.org/2005/Atom}published", "") or
                    item.findtext("atom:updated", "", ns) or
                    ""
                )
                # Parse date
                time_ago = "Recent"
                if pub_date:
                    try:
                        # Try ISO format
                        dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                        delta = datetime.now(dt.tzinfo) - dt
                        time_ago = f"{delta.days}d ago" if delta.days > 0 else "Today"
                    except Exception:
                        time_ago = "Recent"
                if title:
                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": desc,
                        "image": image,
                        "source": "rss",
                        "source_name": feed["name"],
                        "time_ago": time_ago,
                        "score": None,
                    })
            return results
    except Exception as e:
        logger.error(f"RSS error for {feed['name']}: {e}")
        return []


async def fetch_all_rss() -> list[dict]:
    """Fetch from all RSS feeds concurrently."""
    tasks = [fetch_rss_feed(feed, limit=5) for feed in RSS_FEEDS]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for r in raw:
        if isinstance(r, list):
            results.extend(r)
    return results


# ================================================================
# CATEGORIZER
# ================================================================

def categorize_topic(topic: dict, query_category: Optional[str] = None) -> str:
    if query_category:
        return query_category
    title = (topic.get("title") or "").lower()
    snippet = (topic.get("snippet") or "").lower()
    text = title + " " + snippet
    if any(w in text for w in ["launch", "release", "tool", "app", "product", "api", "open source", "github"]):
        return "tools"
    if any(w in text for w in ["paper", "research", "arxiv", "benchmark", "model", "training", "weights", "transformer", "diffusion"]):
        return "research"
    if any(w in text for w in ["funding", "raise", "startup", "series", "valuation", "yc", "vc", "acquisition"]):
        return "startups"
    if topic.get("source") in ("reddit", "hackernews", "twitter"):
        return "community"
    if topic.get("source") == "producthunt":
        return "tools"
    if topic.get("source") == "arxiv":
        return "research"
    return "breaking"


# ================================================================
# MAIN: FETCH ALL TRENDING
# ================================================================

async def fetch_all_trending(page: int = 0, per_page: int = 50) -> dict:
    """Fetch trending topics from ALL 7 sources, categorized for the feed."""
    tasks = []

    # Source 1: Serper (Google News)
    for cat, queries in SERPER_QUERIES.items():
        for q in queries:
            tasks.append(("serper", cat, fetch_serper(q, num=6)))

    # Source 2: Reddit
    for sub in REDDIT_SUBS:
        tasks.append(("reddit", None, fetch_reddit(sub, limit=8)))

    # Source 3: HackerNews
    tasks.append(("hackernews", None, fetch_hackernews(limit=12)))

    # Source 4: Product Hunt
    tasks.append(("producthunt", "tools", fetch_producthunt(limit=10)))

    # Source 5: ArXiv
    tasks.append(("arxiv", "research", fetch_arxiv(limit=10)))

    # Source 6: Twitter/X
    tasks.append(("twitter", None, fetch_twitter(limit=15)))

    # Source 7: RSS Feeds
    tasks.append(("rss", None, fetch_all_rss()))

    # Run ALL concurrently
    raw_results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

    all_topics = []
    seen_titles = set()

    for i, result in enumerate(raw_results):
        if isinstance(result, Exception):
            logger.error(f"Source error: {result}")
            continue
        source_type, forced_cat, _ = tasks[i]
        for topic in result:
            # Deduplicate by title
            title_key = topic["title"].lower().strip()[:60]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            topic["category"] = categorize_topic(topic, forced_cat)
            if not topic.get("why_trending"):
                topic["why_trending"] = topic.get("snippet") or f"Trending on {topic.get('source_name', topic.get('source', 'the web'))}"
            all_topics.append(topic)

    # Sort by score (highest first), then non-scored items
    all_topics.sort(key=lambda t: (t.get("score") or 0), reverse=True)

    start = page * per_page
    end = start + per_page
    paginated = all_topics[start:end]

    return {
        "topics": paginated,
        "total": len(all_topics),
        "page": page,
        "has_more": end < len(all_topics),
        "sources": {
            "serper": bool(SERPER_KEY),
            "reddit": True,
            "hackernews": True,
            "producthunt": True,
            "arxiv": True,
            "twitter": bool(TWITTER_BEARER),
            "rss": len(RSS_FEEDS),
        },
    }
