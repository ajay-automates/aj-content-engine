"""LinkedIn Publishing Tool"""
from crewai.tools import BaseTool
import os, requests

class LinkedInPublishTool(BaseTool):
    name: str = "linkedin_publisher"
    description: str = "Publish post to LinkedIn. Returns post ID."

    def _run(self, content: str) -> str:
        token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not token: return "FAILED: LINKEDIN_ACCESS_TOKEN not set"
        try:
            h = {"Authorization": f"Bearer {token}"}
            p = requests.get("https://api.linkedin.com/v2/userinfo", headers=h)
            p.raise_for_status()
            pid = p.json()["sub"]
            payload = {
                "author": f"urn:li:person:{pid}", "lifecycleState": "PUBLISHED",
                "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": content}, "shareMediaCategory": "NONE"}},
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
            r = requests.post("https://api.linkedin.com/v2/ugcPosts", json=payload, headers={**h, "Content-Type": "application/json", "X-Restli-Protocol-Version": "2.0.0"})
            r.raise_for_status()
            return f"SUCCESS: LinkedIn post (ID: {r.headers.get('x-restli-id', 'ok')})"
        except Exception as e:
            return f"FAILED: {str(e)}"
