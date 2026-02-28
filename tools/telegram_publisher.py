"""Telegram Publishing Tool"""
from crewai.tools import BaseTool
import os, requests

class TelegramPublishTool(BaseTool):
    name: str = "telegram_publisher"
    description: str = "Send message to Telegram channel."

    def _run(self, content: str) -> str:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        ch = os.getenv("TELEGRAM_CHANNEL_ID")
        if not token or not ch: return "FAILED: Telegram creds not set"
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": ch, "text": content[:4096], "parse_mode": "Markdown"}, timeout=30)
            r.raise_for_status()
            d = r.json()
            return f"SUCCESS: Telegram msg (ID: {d['result']['message_id']})" if d.get("ok") else f"FAILED: {d}"
        except Exception as e:
            return f"FAILED: {str(e)}"
