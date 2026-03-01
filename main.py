"""AJ Content Engine — FastAPI Server + Trending Feed + Video Research + Shorts Rewriter + Dashboard"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
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

# ─── SHORTS REWRITER ENDPOINTS ────────────────────────────────────
@app.post("/api/shorts/generate")
async def generate_shorts_ideas(request: Request):
    """Take trending topics and rewrite them into viral YouTube Shorts titles."""
    try:
        body = await request.json()
        topics = body.get("topics", [])
        max_topics = min(body.get("max_topics", 12), 20)
        if not topics:
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

@app.get("/api/shorts/inject.js")
async def shorts_inject_js():
    """Serve the Shorts UI module as a self-contained JS file.
    Include via <script src="/api/shorts/inject.js"></script> at bottom of index.html.
    Auto-injects CSS, HTML section, and JS logic for the Shorts Ideas row."""
    js = r"""
(function(){
/* === SHORTS CSS === */
var css=document.createElement('style');
css.textContent='.shorts-section{padding:20px 0 10px;position:relative;z-index:3}.shorts-section .section-title{color:var(--accent-secondary)}.shorts-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.6rem;font-weight:700;letter-spacing:.5px;text-transform:uppercase;margin-left:8px}.badge-drama{background:rgba(229,9,20,.15);color:var(--accent)}.badge-free_resource{background:rgba(0,212,255,.15);color:var(--accent-secondary)}.badge-tool_discovery{background:rgba(139,92,246,.15);color:#a78bfa}.badge-competition{background:rgba(251,146,60,.15);color:#fb923c}.badge-secret_leak{background:rgba(244,63,94,.15);color:#f43f5e}.badge-how_to{background:rgba(34,197,94,.15);color:#22c55e}.badge-career{background:rgba(59,130,246,.15);color:#3b82f6}.badge-mind_blown{background:rgba(168,85,247,.15);color:#a855f7}.shorts-card .card-title{font-size:1.05rem;line-height:1.3}.shorts-card .card-body{padding:18px 20px}.shorts-original{font-size:.7rem;color:var(--text-muted);margin-top:6px;font-style:italic;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}.btn-shorts-refresh{padding:6px 16px;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text-muted);font-size:.75rem;cursor:pointer;font-family:inherit;transition:all .2s}.btn-shorts-refresh:hover{border-color:var(--accent-secondary);color:var(--accent-secondary)}';
document.head.appendChild(css);

/* === SHORTS HTML SECTION — injected before feedContainer === */
var feed=document.getElementById('feedContainer');
if(feed){
  var sec=document.createElement('div');
  sec.id='shortsSection';
  feed.parentNode.insertBefore(sec,feed);
}

/* === SHORTS LOADER === */
async function loadShortsIdeas(){
  var c=document.getElementById('shortsSection');
  if(!c)return;
  c.innerHTML='<div class="shorts-section"><div class="section-header"><div class="section-title"><span class="icon">\uD83C\uDFAC</span> SHORTS IDEAS <span class="count">AI-rewritten</span></div><button class="btn-shorts-refresh" onclick="window._loadShorts()">\u21BB Refresh</button></div><div class="scroll-row" id="shortsRow">'+Array(5).fill('<div class="skeleton skeleton-card"></div>').join('')+'</div></div>';
  try{
    var r=await fetch('/api/shorts/generate');
    var d=await r.json();
    if(d.shorts&&d.shorts.length>0){renderShortsRow(d.shorts)}
    else{document.getElementById('shortsRow').innerHTML='<div style="padding:30px;color:var(--text-muted);font-size:.9rem">Shorts ideas loading... trending feed may still be warming up. Click Refresh in a moment.</div>'}
  }catch(e){
    console.error('Shorts error:',e);
    var row=document.getElementById('shortsRow');
    if(row)row.innerHTML='<div style="padding:30px;color:var(--text-muted);font-size:.9rem">Could not load shorts ideas. Click Refresh to retry.</div>';
  }
}

function renderShortsRow(shorts){
  var row=document.getElementById('shortsRow');
  if(!row)return;
  row.innerHTML=shorts.map(function(s,i){
    var bc={'drama':'badge-drama','free_resource':'badge-free_resource','tool_discovery':'badge-tool_discovery','competition':'badge-competition','secret_leak':'badge-secret_leak','how_to':'badge-how_to','career':'badge-career','mind_blown':'badge-mind_blown'}[s.hook_type]||'badge-drama';
    var ht=s.hook_type?s.hook_type.replace(/_/g,' '):'';
    var pe=['\uD83C\uDFAC','\uD83D\uDCF1','\u26A1','\uD83D\uDD25','\uD83D\uDCA1','\uD83D\uDE80','\uD83E\uDDE0','\uD83C\uDFAF'][i%8];
    return '<div class="topic-card shorts-card" style="animation:fadeSlide .4s ease '+i*.06+'s both;flex:0 0 360px">'+
      '<div class="card-image"><div class="placeholder">'+pe+'</div><div class="card-gradient"></div>'+
      '<div class="card-source-badge" style="background:rgba(0,212,255,.2);color:var(--accent-secondary);border:1px solid rgba(0,212,255,.3)">\uD83C\uDFAC SHORTS IDEA</div>'+
      (ht?'<div class="card-score"><span class="shorts-badge '+bc+'">'+ht+'</span></div>':'')+
      '</div><div class="card-body">'+
      '<div class="card-title">'+escHtml(s.title)+'</div>'+
      '<div class="card-meta"><span>'+(s.time_ago||'Recent')+'</span><span>'+(s.source_name||s.source||'')+'</span></div>'+
      '<div class="card-why">'+escHtml(s.angle||s.why_trending||'')+'</div>'+
      (s.original_title?'<div class="shorts-original">\u2190 '+escHtml(s.original_title)+'</div>':'')+
      '<div class="card-actions">'+
      '<button class="btn-card btn-campaign" onclick="event.stopPropagation();generate(\''+escAttr(s.title)+'\')">\u26A1 Generate</button>'+
      '<button class="btn-card btn-video" onclick="event.stopPropagation();openVideoPicker(\''+escAttr(s.title)+'\')">\uD83C\uDFAC Video</button>'+
      '<button class="btn-card btn-preview" onclick="event.stopPropagation();window.open(\''+(s.url||'#')+'\',\'_blank\')">\u2197 Source</button>'+
      '</div></div></div>';
  }).join('');
}

/* Expose for refresh button */
window._loadShorts=loadShortsIdeas;

/* Auto-load after a short delay (let trending feed load first) */
setTimeout(loadShortsIdeas, 1500);
})();
"""
    return Response(content=js, media_type="application/javascript")

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
