"""Agent 6: Analytics Agent — Tracks performance, generates insights."""
from crewai import Agent, LLM
import os

claude_llm = LLM(model="anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))

def create_analytics_agent():
    return Agent(
        role="Performance Analyst",
        goal="Analyze content performance across platforms, find what works, generate data-driven recommendations",
        backstory="Data-driven marketing analyst who turns metrics into strategy. You explain WHY something worked and HOW to replicate it.",
        tools=[], llm=claude_llm, verbose=True, allow_delegation=False, max_iter=3,
    )
