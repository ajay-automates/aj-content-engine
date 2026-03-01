# AJ Content Engine

**Multi-Agent Autonomous Content Production System**

6 AI agents that turn ONE topic into a full content campaign across 10+ platforms — with a Netflix-style trending news feed and built-in video research.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![CrewAI](https://img.shields.io/badge/CrewAI-1.9+-green) ![Claude](https://img.shields.io/badge/LLM-Claude-orange) ![FastAPI](https://img.shields.io/badge/API-FastAPI-teal) ![Railway](https://img.shields.io/badge/Deploy-Railway-purple) ![Version](https://img.shields.io/badge/Version-3.0.0-red)

## What It Does

Input a topic like "AI agents replacing SaaS" and the engine:

1. **Research Agent** — Scans the web for trending angles, stats, competitor gaps
2. **Writer Agent** — Creates a polished 800-1500 word article
3. **Repurposer Agent** — Splits it into 8 platform-specific pieces (Twitter thread, LinkedIn post, Instagram carousel, YouTube script, TikTok script, email newsletter, Reddit post, Bluesky thread)
4. **Visual Agent** — Generates images via **Nano Banana Pro 2** (Gemini API) and videos via **Seedance 2.0**
5. **Publisher Agent** — Posts to Twitter, LinkedIn, Bluesky, Reddit, Telegram, and email
6. **Analytics Agent** — Tracks performance and feeds insights back for the next campaign

## Netflix-Style Trending Feed

No more manually thinking of topics. The engine aggregates AI/tech news from **7 data sources** into a cinematic discovery interface:

- **Serper API** — Google News across 8 targeted AI queries
- **Reddit** — Hot posts from r/MachineLearning, r/artificial, r/LocalLLaMA, r/singularity
- **HackerNews** — Top AI stories via Algolia API
- **Product Hunt** — Daily AI product launches
- **ArXiv** — Latest research papers
- **Twitter/X** — Trending AI posts with engagement filtering
- **RSS Feeds** — 10 major AI blogs (Anthropic, Google AI, OpenAI, TechCrunch, etc.)

Topics are categorized into horizontal scrolling rows: Breaking in AI, New Tools & Launches, Research & Papers, Startups & Funding, Trending in Community. Each card shows source badges, engagement scores, and one-click campaign generation.

## Video Research & Download Module

Every topic card includes a **🎬 Video** button that opens a full-screen video picker:

- **YouTube search** via yt-dlp — searches and returns metadata for top results
- **Serper Video Search** — finds official demos, promo videos, and announcements from Google Videos
- **Multi-platform support** — YouTube, Twitter/X, Vimeo, TikTok, Dailymotion
- **Parallel search** — YouTube + Serper run simultaneously, results are deduplicated
- **One-click download** — yt-dlp downloads at up to 1080p, max 100MB, 10-minute cap
- **Supabase Storage hosting** — downloaded videos are permanently hosted with public URLs
- **Video picker UI** — grid layout with thumbnails, platform badges, duration, channel name, view counts, animated download progress overlay, and success toast notification

### How It Works

1. Click **🎬 Video** on any topic card
2. Modal opens with pre-filled search — edit the query if needed
3. 3-5 video options appear from YouTube + Google
4. Click to select, then **"Use This Video"**
5. Video downloads via yt-dlp → uploads to Supabase Storage → you get a permanent hosted URL

## Why This Can't Be Replaced By ChatGPT

- **Persistent state** across campaigns
- **Real API connections** — actually posts to platforms
- **Autonomous scheduling** — runs on cron without human intervention
- **Feedback loop** — analytics improve future content
- **Multi-modal** — text + images + video in one pipeline
- **Live trending feed** — 7 sources, zero manual topic hunting
- **Video research** — find, download, and host videos in one click
- **~$0.50/campaign** replaces a 3-person content team

## Quick Start

```bash
git clone https://github.com/ajay-automates/aj-content-engine.git
cd aj-content-engine
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
python main.py
```

Open `http://localhost:8000` — browse trending topics, find videos, or type your own topic and hit Generate.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI with Netflix-style trending feed |
| `/dashboard` | GET | Campaign dashboard |
| `/api/trending` | GET | Fetch trending AI/tech topics (paginated) |
| `/api/videos/search` | POST | Search for videos related to a topic (3-5 results) |
| `/api/videos/select` | POST | Download selected video + upload to Supabase |
| `/api/campaign/generate` | POST | Research + Write + Repurpose |
| `/api/campaign/full` | POST | Full pipeline with visuals + publishing |
| `/api/campaign/research` | POST | Research only |
| `/api/campaigns` | GET | List all campaigns |
| `/api/health` | GET | System health check |

## Tech Stack

| Layer | Tech |
|-------|------|
| Agents | CrewAI (sequential pipeline) |
| LLM | Claude (Anthropic API) |
| Images | Nano Banana Pro 2 (Gemini 3.1 Flash) |
| Videos | Seedance 2.0 (ByteDance) |
| Video Research | yt-dlp + Serper Video API |
| Video Hosting | Supabase Storage |
| Backend | FastAPI |
| Frontend | Jinja2 + vanilla JS (dark cinema-grade UI) |
| Hosting | Railway |
| Scheduling | APScheduler |

## Environment Variables

```env
ANTHROPIC_API_KEY=        # Claude API key (required)
SERPER_API_KEY=           # Google search + video search
GEMINI_API_KEY=           # Nano Banana image generation
SUPABASE_URL=             # Supabase project URL
SUPABASE_KEY=             # Supabase anon/service key
SUPABASE_VIDEO_BUCKET=videos  # Storage bucket name for videos
TWITTER_API_KEY=          # Twitter publishing
LINKEDIN_ACCESS_TOKEN=    # LinkedIn publishing
BLUESKY_HANDLE=           # Bluesky publishing
REDDIT_CLIENT_ID=         # Reddit publishing
TELEGRAM_BOT_TOKEN=       # Telegram publishing
SENDGRID_API_KEY=         # Email newsletter
```

## Deploy to Railway

```bash
railway login
railway init
railway up
```

Add environment variables in Railway dashboard. The app auto-deploys on push to `main`.

## Project Structure

```
aj-content-engine/
├── agents/              # 6 AI agent definitions
├── tasks/               # Task specs for each agent
├── tools/
│   ├── trending_fetcher.py   # 7-source trending news aggregator
│   ├── video_researcher.py   # yt-dlp search/download + Serper + Supabase upload
│   ├── nano_banana.py        # Image generation (Gemini)
│   ├── seedance.py           # Video generation (ByteDance)
│   ├── twitter_publisher.py  # Twitter/X posting
│   ├── linkedin_publisher.py # LinkedIn posting
│   ├── bluesky_publisher.py  # Bluesky posting
│   ├── reddit_publisher.py   # Reddit posting
│   ├── telegram_publisher.py # Telegram posting
│   └── email_publisher.py    # SendGrid email
├── config/              # Platform templates, brand voices
├── templates/
│   ├── index.html       # Netflix-style UI + video picker
│   └── dashboard.html   # Campaign dashboard
├── crew.py              # CrewAI orchestrator
├── main.py              # FastAPI server (v3.0.0)
├── scheduler.py         # APScheduler cron
└── requirements.txt
```

## Built By

**Ajay Kumar Reddy Nelavetla** — AI Engineer | [@ajay-automates](https://github.com/ajay-automates)
