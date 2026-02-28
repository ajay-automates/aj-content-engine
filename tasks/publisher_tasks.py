"""Publisher Agent Tasks"""
from crewai import Task

def create_publisher_task(agent, topic):
    return Task(
        description=(
            f"Publish all content for: {topic}\n\n"
            "Order: Twitter -> LinkedIn -> Bluesky -> Reddit -> Telegram -> Email\n"
            "For each: use the publishing tool, attach visuals, log URL on success, log error on failure.\n"
            "Wait 2 seconds between platforms. Return a complete status report."
        ),
        expected_output="Publishing report: PLATFORM: [SUCCESS/FAILED] - URL for each. Summary: X/Y published.",
        agent=agent,
    )
