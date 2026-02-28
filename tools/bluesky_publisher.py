"""Bluesky Publishing Tool"""
from crewai.tools import BaseTool
import os

class BlueskyPublishTool(BaseTool):
    name: str = "bluesky_publisher"
    description: str = "Publish post/thread to Bluesky. Separate posts with \'---\'."

    def _run(self, content: str) -> str:
        handle = os.getenv("BLUESKY_HANDLE")
        pw = os.getenv("BLUESKY_APP_PASSWORD")
        if not handle or not pw: return "FAILED: Bluesky creds not set"
        try:
            from atproto import Client
            client = Client()
            client.login(handle, pw)
            posts = [p.strip() for p in content.split("---") if p.strip()]
            if len(posts) == 1:
                client.send_post(text=posts[0][:300])
                return "SUCCESS: Bluesky post published"
            parent = root = None
            for i, txt in enumerate(posts):
                if parent is None:
                    r = client.send_post(text=txt[:300])
                    root = parent = {"uri": r.uri, "cid": r.cid}
                else:
                    r = client.send_post(text=txt[:300], reply_to={"root": root, "parent": parent})
                    parent = {"uri": r.uri, "cid": r.cid}
            return f"SUCCESS: Bluesky thread ({len(posts)} posts)"
        except Exception as e:
            return f"FAILED: {str(e)}"
