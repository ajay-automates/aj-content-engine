"""Analytics Agent Tasks"""
from crewai import Task

def create_analytics_task(agent, campaign_data):
    return Task(
        description=(
            f"Analyze campaign performance:\n{campaign_data}\n\n"
            "Provide: metrics per platform, best/worst performer with WHY, "
            "content patterns, posting time analysis, 5 specific recommendations for next campaign, "
            "3 predicted best topics to research next."
        ),
        expected_output="Performance report with metrics, top/bottom performers, patterns, and 5 actionable recommendations.",
        agent=agent,
    )
