"""Visual Agent Tasks"""
from crewai import Task

def create_visual_task(agent, topic):
    return Task(
        description=(
            f"Generate visual assets for: {topic}\n\n"
            "Create images using Nano Banana Pro 2 for:\n"
            "1. TWITTER: Bold quote card (1200x675, 16:9)\n"
            "2. LINKEDIN: Professional header (1200x627)\n"
            "3. INSTAGRAM: 10 carousel slides (1080x1080)\n"
            "4. YOUTUBE: Eye-catching thumbnail (1280x720)\n"
            "5. EMAIL: Hero banner (600x200)\n\n"
            "For TikTok/YouTube Shorts, generate a first-frame image then describe the video prompt for Seedance 2.0.\n"
            "Craft detailed prompts for professional results. Return all image paths mapped to platforms."
        ),
        expected_output="List of visual assets per platform with file paths and prompts used.",
        agent=agent,
    )
