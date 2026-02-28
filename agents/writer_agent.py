"""Agent 2: Writer Agent — Creates long-form content (800-1500 words)."""
from crewai import Agent, LLM
import os

claude_llm = LLM(model="anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))

def create_writer_agent():
    return Agent(
        role="Content Strategist & Writer",
        goal="Transform research into viral-worthy long-form content that hooks readers in the first sentence",
        backstory=(
            "Grown 5 tech brands from 0 to 100K+ followers. You understand the psychology of attention \u2014 "
            "hooks that stop the scroll, stories that create emotional investment, CTAs that drive action. "
            "Write with authority, weave in data naturally, deliver unique perspectives."
        ),
        tools=[], llm=claude_llm, verbose=True, allow_delegation=False, max_iter=3,
    )
