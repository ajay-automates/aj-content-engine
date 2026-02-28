# AJ Content Engine

**Multi-Agent Autonomous Content Production System**

6 AI agents that turn ONE topic into a full content campaign across 10+ platforms.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![CrewAI](https://img.shields.io/badge/CrewAI-1.9+-green) ![Claude](https://img.shields.io/badge/LLM-Claude-orange) ![FastAPI](https://img.shields.io/badge/API-FastAPI-teal) ![Railway](https://img.shields.io/badge/Deploy-Railway-purple)

## What It Does

Input a topic like "AI agents replacing SaaS" and the engine:

1. **Research Agent** — Scans the web for trending angles, stats, competitor gaps
2. **Writer Agent** — Creates a polished 800-1500 word article
3. **Repurposer Agent** — Splits it into 8 platform-specific pieces (Twitter thread, LinkedIn post, Instagram carousel, YouTube script, TikTok script, email newsletter, Reddit post, Bluesky thread)
4. **Visual Agent** — Generates images via **Nano Banana Pro 2** (Gemini API) and videos via **Seedance 2.0**
5. **Publisher Agent** — Posts to Twitter, LinkedIn, Bluesky, Reddit, Telegram, and email
6. **Analytics Agent** — Tracks performance and feeds insights back for the next campaign

## Why This Can\'t Be Replaced By ChatGPT

- **Persistent state** across campaigns
- **Real API connections** — actually posts to platforms
- **Autonomous scheduling** — runs on cron without human intervention
- **Feedback loop** — analytics improve future content
- **Multi-modal** — text + images + video in one pipeline
- **~$0.50/campaign** replaces a 3-person content team

## Quick Start

```bash
git clone https://github.com/ajay-automates/aj-content-engine.git
cd aj-content-engine
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
python main.py
```

Open `http://localhost:8000` — enter a topic, hit Generate.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/dashboard` | GET | Campaign dashboard |
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
| Backend | FastAPI |
| Hosting | Railway |
| Scheduling | APScheduler |

## Deploy to Railway

```bash
railway login
railway init
railway up
```

Add environment variables in Railway dashboard.

## Project Structure

```
aj-content-engine/
\u251c\u2500\u2500 agents/          # 6 AI agent definitions
\u251c\u2500\u2500 tasks/           # Task specs for each agent
\u251c\u2500\u2500 tools/           # Platform tools (Nano Banana, Seedance, Twitter, LinkedIn, etc.)
\u251c\u2500\u2500 config/          # Platform templates, brand voices
\u251c\u2500\u2500 templates/       # HTML dashboard
\u251c\u2500\u2500 crew.py          # CrewAI orchestrator
\u251c\u2500\u2500 main.py          # FastAPI server
\u251c\u2500\u2500 scheduler.py     # APScheduler cron
\u2514\u2500\u2500 requirements.txt
```

## Built By

**Ajay Kumar Reddy Nelavetla** — AI Engineer | [@ajay-automates](https://github.com/ajay-automates)
