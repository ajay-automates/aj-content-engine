"""Platform configuration for content repurposing."""
PLATFORM_CONFIGS = {
    "twitter": {"name": "Twitter/X", "max_length": 280, "format": "thread", "tone": "punchy, bold", "image_size": "1200x675", "image_aspect": "16:9"},
    "linkedin": {"name": "LinkedIn", "max_length": 3000, "format": "post", "tone": "professional, thought-leadership", "image_size": "1200x627"},
    "instagram": {"name": "Instagram", "max_length": 2200, "format": "carousel", "tone": "visual, snackable", "image_size": "1080x1080", "slides": 10},
    "youtube_shorts": {"name": "YouTube Shorts", "format": "script", "tone": "energetic", "video_aspect": "9:16", "duration": "60-90s"},
    "tiktok": {"name": "TikTok", "format": "script", "tone": "casual, trendy", "video_aspect": "9:16", "duration": "30-60s"},
    "email": {"name": "Email Newsletter", "format": "newsletter", "tone": "personal, direct", "image_size": "600x200"},
    "reddit": {"name": "Reddit", "format": "discussion", "tone": "genuine, no self-promotion"},
    "bluesky": {"name": "Bluesky", "max_length": 300, "format": "thread", "tone": "conversational, authentic"},
}
ALL_PLATFORMS = list(PLATFORM_CONFIGS.keys())
