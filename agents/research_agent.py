"""Agent 1: Research Agent — Finds trending angles, gaps, stats."""
from crewai import Agent, LLM
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
import os

search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()
claude_llm = LLM(model="anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))

def create_research_agent():
    return Agent(
        role="Senior Research Analyst",
        goal="Find unique angles, trending data, competitor gaps, and compelling statistics that make content stand out",
        backstory=(
            "Elite research analyst with 15 years at top media companies. "
            "You uncover insights others miss \u2014 the contrarian take, the surprising stat, "
            "the emerging trend before it goes mainstream. Always cite sources, prioritize last 7 days."
        ),
        tools=[search_tool, scrape_tool], llm=claude_llm, verbose=True, allow_delegation=False, max_iter=5,
    )
