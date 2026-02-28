"""Agent 5: Publisher Agent — Posts to all platforms."""
from crewai import Agent, LLM
from tools.twitter_publisher import TwitterPublishTool
from tools.linkedin_publisher import LinkedInPublishTool
from tools.bluesky_publisher import BlueskyPublishTool
from tools.reddit_publisher import RedditPublishTool
from tools.telegram_publisher import TelegramPublishTool
from tools.email_publisher import EmailPublishTool
import os

claude_llm = LLM(model="anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))

def create_publisher_agent():
    tools = []
    if os.getenv("TWITTER_API_KEY"): tools.append(TwitterPublishTool())
    if os.getenv("LINKEDIN_ACCESS_TOKEN"): tools.append(LinkedInPublishTool())
    if os.getenv("BLUESKY_HANDLE"): tools.append(BlueskyPublishTool())
    if os.getenv("REDDIT_CLIENT_ID"): tools.append(RedditPublishTool())
    if os.getenv("TELEGRAM_BOT_TOKEN"): tools.append(TelegramPublishTool())
    if os.getenv("SENDGRID_API_KEY"): tools.append(EmailPublishTool())
    return Agent(
        role="Distribution Manager",
        goal="Maximize reach by publishing content to all connected platforms with optimal timing",
        backstory="Growth hacker managing multi-platform distribution. Handle rate limits, retries, and scheduling.",
        tools=tools, llm=claude_llm, verbose=True, allow_delegation=False, max_iter=8,
    )
