"""Research Agent Tasks"""
from crewai import Task

def create_research_task(agent, topic):
    return Task(
        description=(
            f"Research this topic deeply: {topic}\n\n"
            "REQUIREMENTS:\n"
            "1. Search for latest developments (last 7 days preferred)\n"
            "2. Find 5+ specific data points/stats WITH sources\n"
            "3. Identify competitor content and GAPS in existing coverage\n"
            "4. Find contrarian or surprising viewpoints\n"
            "5. Identify 3-5 trending subtopics\n"
            "6. Find relevant Reddit/Twitter discussions\n\n"
            "Focus on what is NEW, SURPRISING, and SHAREABLE."
        ),
        expected_output=(
            "Structured research brief:\n"
            "TRENDING ANGLES: [top 5 ranked by virality]\n"
            "KEY STATS: [10+ data points with sources]\n"
            "COMPETITOR GAPS: [what\u2019s missing]\n"
            "CONTRARIAN TAKE: [surprising perspective]\n"
            "SUGGESTED HOOK: [scroll-stopping opener]\n"
            "SOURCES: [all URLs]"
        ),
        agent=agent,
    )
