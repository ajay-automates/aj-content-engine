"""Seedance 2.0 — Video Generation (ByteDance)"""
from crewai.tools import BaseTool
import os, time, requests

class SeedanceVideoTool(BaseTool):
    name: str = "seedance_video_generator"
    description: str = "Generate AI videos using Seedance 2.0. Input: text prompt. Returns video file path."

    def _run(self, prompt: str, image_path: str = None) -> str:
        api_key = os.getenv("SEEDANCE_API_KEY")
        base_url = os.getenv("SEEDANCE_BASE_URL", "https://dreamina.capcut.com")
        if not api_key:
            return "VIDEO SKIPPED: SEEDANCE_API_KEY not set. Sign up at dreamina.capcut.com for free daily credits."
        try:
            url = f"{base_url}/api/v1/video/generate"
            payload = {"prompt": prompt, "model": "seedance-2.0", "duration": 10, "resolution": "1080p", "aspect_ratio": "9:16"}
            if image_path and os.path.exists(image_path):
                import base64
                with open(image_path, "rb") as f:
                    payload["reference_image"] = base64.b64encode(f.read()).decode()
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=300)
            response.raise_for_status()
            data = response.json()
            video_url = data.get("video_url") or data.get("url")
            if video_url:
                os.makedirs("output/videos", exist_ok=True)
                filename = f"output/videos/vid_{int(time.time())}.mp4"
                vid = requests.get(video_url, timeout=120)
                with open(filename, "wb") as f:
                    f.write(vid.content)
                return f"Video saved: {filename}"
            return f"Submitted. Response: {data}"
        except Exception as e:
            return f"ERROR: {str(e)}"
