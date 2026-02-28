"""Email Newsletter Tool (SendGrid)"""
from crewai.tools import BaseTool
import os

class EmailPublishTool(BaseTool):
    name: str = "email_publisher"
    description: str = "Send email newsletter. Format: \'subject: X | body: Y\'"

    def _run(self, content: str) -> str:
        api_key = os.getenv("SENDGRID_API_KEY")
        frm = os.getenv("EMAIL_FROM")
        to = os.getenv("EMAIL_TO")
        if not all([api_key, frm, to]): return "FAILED: Email env vars not set"
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            parts = {}
            for p in content.split("|"):
                if ":" in p:
                    k, v = p.split(":", 1)
                    parts[k.strip().lower()] = v.strip()
            msg = Mail(from_email=frm, to_emails=to, subject=parts.get("subject", "AJ Content Engine"),
                html_content=f"<div style='font-family:Arial;max-width:600px;margin:auto'>{parts.get('body', content)}</div>")
            r = SendGridAPIClient(api_key).send(msg)
            return f"SUCCESS: Email sent" if r.status_code in [200,201,202] else f"FAILED: {r.status_code}"
        except Exception as e:
            return f"FAILED: {str(e)}"
