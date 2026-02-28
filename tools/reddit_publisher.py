"""Reddit Publishing Tool"""
from crewai.tools import BaseTool
import os

class RedditPublishTool(BaseTool):
    name: str = "reddit_publisher"
    description: str = "Publish to Reddit. Format: \'subreddit: X | title: Y | body: Z\'"

    def _run(self, content: str) -> str:
        try:
            import praw
            reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"), client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                username=os.getenv("REDDIT_USERNAME"), password=os.getenv("REDDIT_PASSWORD"),
                user_agent="aj-content-engine/1.0",
            )
            parts = {}
            for p in content.split("|"):
                if ":" in p:
                    k, v = p.split(":", 1)
                    parts[k.strip().lower()] = v.strip()
            sub = reddit.subreddit(parts.get("subreddit", "test"))
            s = sub.submit(title=parts.get("title", "Untitled"), selftext=parts.get("body", content))
            return f"SUCCESS: https://reddit.com{s.permalink}"
        except Exception as e:
            return f"FAILED: {str(e)}"
