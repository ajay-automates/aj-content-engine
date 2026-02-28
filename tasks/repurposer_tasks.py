"""Repurposer Agent Tasks"""
from crewai import Task

def create_repurposer_task(agent, topic):
    return Task(
        description=(
            f"Repurpose the article about \'{topic}\' into 8 platform-specific pieces:\n\n"
            "1. TWITTER THREAD: 5-7 tweets, hook first, numbers, hashtags\n"
            "2. LINKEDIN POST: 200-300 words, thought-leadership, end with question\n"
            "3. INSTAGRAM CAROUSEL: 10 slides (8 words max per slide), caption with hashtags\n"
            "4. YOUTUBE SHORTS SCRIPT: 60-90 sec, [PAUSE]/[EMPHASIS] markers\n"
            "5. TIKTOK SCRIPT: 30-60 sec, casual, trending hooks\n"
            "6. EMAIL NEWSLETTER: Subject line + 300-500 word body + CTA\n"
            "7. REDDIT POST: Discussion title + 200-400 word body, suggest subreddits\n"
            "8. BLUESKY THREAD: 3-5 posts, authentic tone\n\n"
            "Each piece must be COMPLETELY adapted for the platform, not copy-pasted.\n"
            "Label each clearly: [TWITTER], [LINKEDIN], [INSTAGRAM], etc."
        ),
        expected_output="8 complete platform-ready content pieces, each clearly labeled and ready to post.",
        agent=agent,
    )
