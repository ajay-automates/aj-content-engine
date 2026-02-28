"""Agent 3: Repurposer Agent — Splits article into 8 platform pieces."""
from crewai import Agent, LLM
import os

claude_llm = LLM(model="anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))

def create_repurposer_agent():
    return Agent(
        role="Content Repurposing Specialist",
        goal="Maximize reach by adapting one article into 8+ platform-specific content pieces",
        backstory=(
            "Manage content for 50+ brands. LinkedIn wants thought leadership, Twitter wants punchy threads, "
            "Instagram wants visual storytelling, Reddit wants genuine discussion. You reimagine content "
            "for each platform\u2019s culture, format constraints, and engagement patterns."
        ),
        tools=[], llm=claude_llm, verbose=True, allow_delegation=False, max_iter=3,
    )
