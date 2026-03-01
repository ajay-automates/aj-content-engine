"""AJ Content Engine — Shorts Topic Rewriter
Takes trending AI news and rewrites them into viral YouTube Shorts titles
inspired by creators like Vishnu Vijayan and Matt Wolfe.

Hook formulas derived from analyzing 200+ viral AI shorts:
- "[Company] just [shocking verb] [product]"
- "China's new [X] is beating [Western product]"  
- "Free [valuable thing] !!"
- "This [tool/secret/prompt] is [superlative]"
- "[Number]+ [valuable resources]"
- "You can [amazing thing] for FREE"
- "[Company]'s secret [X] is out"
- "This [AI update] changes everything"
"""
import os
import json
import logging
import httpx
from typing import Optional

logger = logging.getLogger("shorts_rewriter")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

REWRITE_SYSTEM_PROMPT = """You are a viral YouTube Shorts title generator for an AI/tech news channel.

Your job: Take a list of trending AI news headlines and rewrite each one into a punchy, 
scroll-stopping YouTube Shorts title (under 60 characters ideally, max 80).

RULES:
1. Every title must trigger curiosity, urgency, or FOMO
2. Use these proven hook formulas:
   - "[Company] just [did something wild]" 
   - "China's new [X] is beating [Y]" (geopolitical drama)
   - "Free [valuable thing] !!" (free resources)
   - "This [secret/tool] changes everything" (mystery/hype)
   - "[Number]+ [resources] for [audience]" (listicle hooks)
   - "You can [do X] for FREE" (value hooks)
   - "[Company]'s secret [X] is out" (leaked/insider feel)
   - "This [tool] is beating [competitor]" (competition frame)
   - "[Company] just killed [product]" (disruption hook)
   - "How to [achieve result] with AI" (tutorial hook)
3. Keep it casual, no formal language
4. Use sentence case (not Title Case)
5. Add ".." or "!!" for emphasis sparingly
6. Never use hashtags or emojis in titles
7. Each title should work as a standalone hook — someone should WANT to click

Also generate a "hook_type" label for each: one of "drama", "free_resource", "tool_discovery", 
"competition", "secret_leak", "how_to", "career", "mind_blown"

Also generate a brief "angle" (1 sentence) describing what the short video should cover.

Respond ONLY in JSON array format:
[
  {
    "original": "the original headline",
    "shorts_title": "the rewritten shorts title",
    "hook_type": "drama",
    "angle": "Brief description of what to cover in the short"
  }
]
"""


async def rewrite_for_shorts(topics: list[dict], max_topics: int = 12) -> list[dict]:
    """Take trending topics and rewrite them into viral Shorts titles using Claude."""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — using fallback rewriter")
        return _fallback_rewrite(topics[:max_topics])

    # Pick the best topics for shorts (high engagement, recent, interesting)
    selected = _select_best_for_shorts(topics, max_topics)
    
    if not selected:
        return []

    headlines = "\n".join([f"- {t['title']}" for t in selected])
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "system": REWRITE_SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": f"Rewrite these trending AI headlines into viral YouTube Shorts titles:\n\n{headlines}"}
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract text from response
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        # Parse JSON from response
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        
        rewritten = json.loads(text)
        
        # Merge rewritten data back with original topic metadata
        results = []
        for i, item in enumerate(rewritten):
            if i >= len(selected):
                break
            original = selected[i]
            results.append({
                "title": item.get("shorts_title", original["title"]),
                "original_title": original["title"],
                "url": original.get("url", ""),
                "image": original.get("image"),
                "source": original.get("source", ""),
                "source_name": original.get("source_name", ""),
                "time_ago": original.get("time_ago", "Recent"),
                "score": original.get("score"),
                "category": "shorts",
                "hook_type": item.get("hook_type", "drama"),
                "angle": item.get("angle", ""),
                "why_trending": item.get("angle", original.get("snippet", "")),
                "snippet": item.get("angle", ""),
            })
        
        return results

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude response as JSON: %s", e)
        return _fallback_rewrite(selected)
    except Exception as e:
        logger.error("Shorts rewriter error: %s", e)
        return _fallback_rewrite(selected)


def _select_best_for_shorts(topics: list[dict], limit: int = 12) -> list[dict]:
    """Select the most shorts-worthy topics from the feed."""
    scored = []
    for t in topics:
        title = (t.get("title") or "").lower()
        score = t.get("score") or 0
        
        # Boost topics that naturally fit shorts format
        shorts_score = score
        
        # Boost: company news (Google, OpenAI, Anthropic, Meta, Microsoft, Apple)
        companies = ["google", "openai", "anthropic", "meta", "microsoft", "apple", 
                     "nvidia", "amazon", "deepseek", "mistral", "hugging face"]
        if any(c in title for c in companies):
            shorts_score += 500
        
        # Boost: tool launches and free stuff
        if any(w in title for w in ["launch", "release", "free", "open source", "tool", "app"]):
            shorts_score += 400
        
        # Boost: competition/drama
        if any(w in title for w in ["beat", "kill", "vs", "war", "race", "leak", "secret"]):
            shorts_score += 600
        
        # Boost: China/geopolitical
        if any(w in title for w in ["china", "chinese", "deepseek", "qwen", "baidu"]):
            shorts_score += 300
        
        # Boost: model names (people search for these)
        if any(w in title for w in ["gpt", "claude", "gemini", "llama", "sora", "veo", "midjourney"]):
            shorts_score += 200
        
        # Penalize: academic/dry titles
        if any(w in title for w in ["arxiv", "proceedings", "symposium", "et al"]):
            shorts_score -= 500
        
        # Penalize: very long titles (shorts titles should be punchy)
        if len(title) > 120:
            shorts_score -= 200
        
        scored.append((shorts_score, t))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:limit]]


def _fallback_rewrite(topics: list[dict]) -> list[dict]:
    """Simple rule-based fallback when Claude API is unavailable."""
    results = []
    for t in topics:
        title = t.get("title", "")
        # Simple transformations
        shorts_title = title
        if len(title) > 60:
            shorts_title = title[:57] + "..."
        
        results.append({
            "title": shorts_title,
            "original_title": title,
            "url": t.get("url", ""),
            "image": t.get("image"),
            "source": t.get("source", ""),
            "source_name": t.get("source_name", ""),
            "time_ago": t.get("time_ago", "Recent"),
            "score": t.get("score"),
            "category": "shorts",
            "hook_type": "drama",
            "angle": t.get("snippet", ""),
            "why_trending": t.get("snippet", ""),
            "snippet": t.get("snippet", ""),
        })
    return results
