"""Twitter/X Publishing Tool"""
from crewai.tools import BaseTool
import os

class TwitterPublishTool(BaseTool):
    name: str = "twitter_publisher"
    description: str = "Publish tweet or thread to Twitter/X. For threads, separate with \'---\'. Returns URL."

    def _run(self, content: str) -> str:
        try:
            import tweepy
            client = tweepy.Client(
                consumer_key=os.getenv("TWITTER_API_KEY"), consumer_secret=os.getenv("TWITTER_API_SECRET"),
                access_token=os.getenv("TWITTER_ACCESS_TOKEN"), access_token_secret=os.getenv("TWITTER_ACCESS_SECRET"),
            )
            tweets = [t.strip() for t in content.split("---") if t.strip()]
            if len(tweets) == 1:
                r = client.create_tweet(text=tweets[0][:280])
                return f"SUCCESS: https://twitter.com/i/status/{r.data['id']}"
            prev = None
            first_url = None
            for i, txt in enumerate(tweets):
                r = client.create_tweet(text=txt[:280], in_reply_to_tweet_id=prev)
                prev = r.data["id"]
                if i == 0: first_url = f"https://twitter.com/i/status/{prev}"
            return f"SUCCESS: Thread ({len(tweets)} tweets) - {first_url}"
        except Exception as e:
            return f"FAILED: {str(e)}"
