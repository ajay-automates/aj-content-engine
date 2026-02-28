"""AJ Content Engine — FastAPI Server + Dashboard"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os, uvicorn
from datetime import datetime
from crew import ContentEngineCrew

app = FastAPI(title="AJ Content Engine", description="Multi-Agent Autonomous Content Production System", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")
campaigns = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "campaigns": campaigns})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "campaigns": campaigns, "total_campaigns": len(campaigns)})

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
    return {"status": "healthy", "app": "AJ Content Engine", "version": "1.0.0", "agents": 6,
        "keys": {k: bool(os.getenv(v)) for k, v in {"anthropic": "ANTHROPIC_API_KEY", "serper": "SERPER_API_KEY", "gemini": "GEMINI_API_KEY", "twitter": "TWITTER_API_KEY", "linkedin": "LINKEDIN_ACCESS_TOKEN", "bluesky": "BLUESKY_HANDLE", "reddit": "REDDIT_CLIENT_ID", "telegram": "TELEGRAM_BOT_TOKEN", "sendgrid": "SENDGRID_API_KEY"}.items()}}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
