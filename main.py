"""AJ Content Engine — FastAPI Server + Trending Feed + Video Research + Shorts Rewriter + Dashboard"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os, uvicorn
from datetime import datetime
from crew import ContentEngineCrew
from tools.trending_fetcher import fetch_all_trending
from tools.video_researcher import search_videos, select_and_host_video
from tools.shorts_rewriter import rewrite_for_shorts

app = FastAPI(title="AJ Content Engine", description="Multi-Agent Autonomous Content Production System", version="3.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")
campaigns = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "campaigns": campaigns})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "campaigns": campaigns, "total_campaigns": len(campaigns)})

@app.get("/api/trending")
async def get_trending(page: int = 0):
    """Fetch trending AI/tech topics from Serper, Reddit, HackerNews."""
    try:
        data = await fetch_all_trending(page=page)
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e), "topics": [], "total": 0, "page": page, "has_more": False}, status_code=500)

# ─── SHORTS REWRITER ENDPOINT ─────────────────────────────────────
@app.post("/api/shorts/generate")
async def generate_shorts_ideas(request: Request):
    """Take trending topics and rewrite them into viral YouTube Shorts titles."""
    try:
        body = await request.json()
        topics = body.get("topics", [])
        max_topics = min(body.get("max_topics", 12), 20)
        if not topics:
            # If no topics provided, fetch fresh trending topics
            data = await fetch_all_trending(page=0)
            topics = data.get("topics", [])
        shorts = await rewrite_for_shorts(topics, max_topics=max_topics)
        return JSONResponse({"shorts": shorts, "count": len(shorts)})
    except Exception as e:
        return JSONResponse({"error": str(e), "shorts": []}, status_code=500)

@app.get("/api/shorts/generate")
async def generate_shorts_ideas_get():
    """GET version — fetch trending + rewrite into Shorts titles in one call."""
    try:
        data = await fetch_all_trending(page=0)
        topics = data.get("topics", [])
        shorts = await rewrite_for_shorts(topics, max_topics=12)
        return JSONResponse({"shorts": shorts, "count": len(shorts)})
    except Exception as e:
        return JSONResponse({"error": str(e), "shorts": []}, status_code=500)

# ─── VIDEO RESEARCH ENDPOINTS ─────────────────────────────────────
@app.post("/api/videos/search")
async def video_search(request: Request):
    """Search for videos related to a topic. Returns 3-5 video options."""
    try:
        body = await request.json()
        topic = body.get("topic", "").strip()
        if not topic:
            return JSONResponse({"error": "Topic is required"}, status_code=400)
        max_results = min(body.get("max_results", 5), 8)
        videos = await search_videos(topic, max_results=max_results)
        return JSONResponse({"topic": topic, "videos": videos, "count": len(videos)})
    except Exception as e:
        return JSONResponse({"error": str(e), "videos": []}, status_code=500)

@app.post("/api/videos/select")
async def video_select(request: Request):
    """Download a selected video and upload to Supabase for permanent hosting."""
    try:
        body = await request.json()
        video_url = body.get("url", "").strip()
        if not video_url:
            return JSONResponse({"error": "Video URL is required"}, status_code=400)
        result = await select_and_host_video(video_url)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)

# ─── CAMPAIGN ENDPOINTS ───────────────────────────────────────────
@app.post("/api/campaign/generate")
async def generate_campaign(request: Request):
    try:
        body = await request.json()
        topic = body.get("topic", "").strip()
        if not topic: return JSONResponse({"error": "Topic is required"}, status_code=400)
        engine = ContentEngineCrew()
        result = engine.run_content_only(topic)
        campaign = {"id": len(campaigns)+1, "topic": topic, "status": "generated", "created_at": datetime.now().isoformat(), "result": result}
        campaigns.append(campaign)
        return JSONResponse(campaign)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/campaign/full")
async def full_campaign(request: Request):
    try:
        body = await request.json()
        topic = body.get("topic", "").strip()
        publish = body.get("publish", False)
        if not topic: return JSONResponse({"error": "Topic is required"}, status_code=400)
        engine = ContentEngineCrew()
        result = engine.run_content_pipeline(topic, publish=publish)
        campaign = {"id": len(campaigns)+1, "topic": topic, "status": "published" if publish else "generated", "created_at": datetime.now().isoformat(), "result": result}
        campaigns.append(campaign)
        return JSONResponse(campaign)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/campaign/research")
async def research_only(request: Request):
    try:
        body = await request.json()
        topic = body.get("topic", "").strip()
        if not topic: return JSONResponse({"error": "Topic is required"}, status_code=400)
        return JSONResponse(ContentEngineCrew().run_research_only(topic))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/campaigns")
async def list_campaigns():
    return JSONResponse(campaigns)

@app.get("/api/health")
async def health():
    return {"status": "healthy", "app": "AJ Content Engine", "version": "3.1.0", "agents": 6,
        "features": ["trending_feed", "one_click_generate", "multi_agent_pipeline", "video_research", "shorts_rewriter"],
        "keys": {k: bool(os.getenv(v)) for k, v in {"anthropic": "ANTHROPIC_API_KEY", "serper": "SERPER_API_KEY", "gemini": "GEMINI_API_KEY", "twitter": "TWITTER_API_KEY", "linkedin": "LINKEDIN_ACCESS_TOKEN", "bluesky": "BLUESKY_HANDLE", "reddit": "REDDIT_CLIENT_ID", "telegram": "TELEGRAM_BOT_TOKEN", "sendgrid": "SENDGRID_API_KEY", "supabase": "SUPABASE_URL"}.items()}}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
