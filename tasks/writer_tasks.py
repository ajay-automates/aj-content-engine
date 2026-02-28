"""Writer Agent Tasks"""
from crewai import Task

def create_writer_task(agent, topic):
    return Task(
        description=(
            f"Write a long-form article about: {topic}\n\n"
            "Using the research brief, create an 800-1500 word article:\n"
            "1. HEADLINE: Compelling, specific, curiosity-driven\n"
            "2. HOOK: First 2 sentences stop the scroll\n"
            "3. CONTEXT: Why this matters NOW\n"
            "4. MAIN BODY: 3-5 sections with subheadings and data\n"
            "5. UNIQUE INSIGHT: Your perspective\n"
            "6. CTA: Clear call-to-action\n\n"
            "RULES: Every claim backed by data. Short paragraphs. Conversational but authoritative. Markdown format."
        ),
        expected_output="Complete 800-1500 word article in Markdown with headline, hook, sections, data, and CTA.",
        agent=agent,
    )
