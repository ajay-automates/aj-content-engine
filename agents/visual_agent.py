"""Agent 4: Visual Agent — Nano Banana Pro 2 images + Seedance 2.0 videos."""
from crewai import Agent, LLM
from tools.nano_banana import NanoBananaImageTool
import os

claude_llm = LLM(model="anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))

def create_visual_agent():
    tools = []
    if os.getenv("GEMINI_API_KEY"):
        tools.append(NanoBananaImageTool())
    return Agent(
        role="Visual Content Producer",
        goal="Create scroll-stopping visuals for every platform",
        backstory=(
            "Creative director who produced visual content for top tech brands. "
            "You know the visual style for each platform: professional headers for LinkedIn, "
            "bold quote cards for Twitter, carousel slides for Instagram, thumbnails for YouTube."
        ),
        tools=tools, llm=claude_llm, verbose=True, allow_delegation=False, max_iter=5,
    )
