"""Brand voice profiles."""
DEFAULT_BRAND_VOICE = {
    "name": "AJ Automates",
    "tone": "confident, technical but accessible, builder-mindset",
    "style": "Write like a builder who ships real products. Specific numbers. Real tools. Opinionated but data-backed. Short paragraphs. No fluff.",
    "audience": "AI engineers, startup founders, tech professionals",
    "avoid": ["corporate jargon", "buzzwords without substance", "generic AI hype", "passive voice"],
}

def get_brand_voice(brand_name=None):
    return DEFAULT_BRAND_VOICE
