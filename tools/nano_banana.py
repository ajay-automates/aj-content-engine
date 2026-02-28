"""Nano Banana Pro 2 — Image Generation via Google Gemini API"""
from crewai.tools import BaseTool
import os, base64, time, requests

class NanoBananaImageTool(BaseTool):
    name: str = "nano_banana_image_generator"
    description: str = "Generate AI images using Nano Banana Pro 2 (Gemini API). Input: detailed text prompt. Returns image file path."

    def _run(self, prompt: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "ERROR: GEMINI_API_KEY not set"
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
            }
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return "ERROR: No image generated"
            for part in candidates[0].get("content", {}).get("parts", []):
                if "inlineData" in part:
                    img_data = part["inlineData"]["data"]
                    ext = "png" if "png" in part["inlineData"].get("mimeType", "") else "jpg"
                    os.makedirs("output/images", exist_ok=True)
                    filename = f"output/images/img_{int(time.time())}.{ext}"
                    with open(filename, "wb") as f:
                        f.write(base64.b64decode(img_data))
                    return f"Image saved: {filename}"
            return "ERROR: No image data in response"
        except Exception as e:
            return f"ERROR: {str(e)}"
