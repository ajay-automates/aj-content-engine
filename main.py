"""AJ Content Engine — FastAPI Server + Trending Feed + Video Research + Shorts Rewriter + Twitter Videos + Dashboard"""
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
from tools.twitter_video_scanner import fetch_video_tweets

app = FastAPI(title="AJ Content Engine", description="Multi-Agent Autonomous Content Production System", version="3.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")
campaigns = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main UI. Injects Shorts + Twitter Videos modules automatically."""
    resp = templates.TemplateResponse("index.html", {"request": request, "campaigns": campaigns})
    body = resp.body.decode("utf-8")
    # Inject both modules before </body>
    inject = '<script src="/api/shorts/inject.js"></script>\n<script src="/api/twitter-videos/inject.js"></script>\n'
    body = body.replace("</body>", inject + "</body>")
    return HTMLResponse(content=body)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "campaigns": campaigns, "total_campaigns": len(campaigns)})

@app.get("/api/trending")
async def get_trending(page: int = 0):
    try:
        data = await fetch_all_trending(page=page)
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e), "topics": [], "total": 0, "page": page, "has_more": False}, status_code=500)

# ─── TWITTER VIDEO FEED ENDPOINTS ─────────────────────────────────
@app.get("/api/twitter-videos")
async def get_twitter_videos():
    """Fetch recent tweets with native video from tracked AI accounts."""
    try:
        tweets = await fetch_video_tweets(max_results=20, hours_back=72)
        return JSONResponse({"tweets": tweets, "count": len(tweets)})
    except Exception as e:
        return JSONResponse({"error": str(e), "tweets": []}, status_code=500)

TWITTER_VIDEOS_INJECT_JS = r"""
(function(){
/* === TWITTER VIDEOS CSS === */
var css=document.createElement('style');
css.textContent='.tvid-section{padding:20px 0 10px;position:relative;z-index:3}.tvid-section .section-title{color:#1d9bf0}.tvid-card{flex:0 0 380px!important}.tvid-card .card-image{height:180px}.tvid-card .card-image img{width:100%;height:100%;object-fit:cover}.tvid-play-icon{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:48px;height:48px;background:rgba(0,0,0,.65);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.3rem;pointer-events:none;z-index:2}.tvid-author{display:flex;align-items:center;gap:8px;margin-bottom:8px}.tvid-avatar{width:24px;height:24px;border-radius:50%;object-fit:cover}.tvid-handle{font-size:.72rem;color:var(--text-muted)}.tvid-verified{color:#1d9bf0;font-size:.7rem}.tvid-engagement{display:flex;gap:12px;font-size:.7rem;color:var(--text-muted);margin-top:8px}.tvid-engagement span{display:flex;align-items:center;gap:3px}.tvid-tier-badge{position:absolute;top:12px;right:12px;padding:3px 8px;border-radius:5px;font-size:.6rem;font-weight:700;letter-spacing:.5px;text-transform:uppercase}.tier-official{background:rgba(29,155,240,.25);color:#1d9bf0;border:1px solid rgba(29,155,240,.3)}.tier-creator{background:rgba(168,85,247,.2);color:#a855f7;border:1px solid rgba(168,85,247,.3)}.tier-news{background:rgba(251,146,60,.2);color:#fb923c;border:1px solid rgba(251,146,60,.3)}.tvid-dur{position:absolute;bottom:8px;right:8px;padding:2px 8px;border-radius:4px;background:rgba(0,0,0,.8);color:#fff;font-size:.7rem;font-weight:700}.btn-download{background:rgba(29,155,240,.15);color:#1d9bf0;border:1px solid rgba(29,155,240,.25)}.btn-download:hover{background:rgba(29,155,240,.25);color:#fff;box-shadow:0 0 12px rgba(29,155,240,.2)}.btn-tweet{background:rgba(255,255,255,.06);color:var(--text-secondary);border:1px solid var(--border)}.btn-tweet:hover{background:rgba(255,255,255,.1);color:var(--text-primary)}';
document.head.appendChild(css);

/* === INSERT SECTION — after shortsSection, before feedContainer === */
var anchor=document.getElementById('shortsSection')||document.getElementById('feedContainer');
if(anchor){
  var sec=document.createElement('div');sec.id='twitterVideosSection';
  if(anchor.id==='shortsSection'&&anchor.nextSibling){anchor.parentNode.insertBefore(sec,anchor.nextSibling)}
  else if(anchor.id==='feedContainer'){anchor.parentNode.insertBefore(sec,anchor)}
}

/* === LOADER === */
async function loadTwitterVideos(){
  var c=document.getElementById('twitterVideosSection');if(!c)return;
  c.innerHTML='<div class="tvid-section"><div class="section-header"><div class="section-title"><span class="icon">\uD83D\uDCF9</span> VIDEO READY — FROM TWITTER <span class="count">official clips</span></div><button class="btn-shorts-refresh" onclick="window._loadTVids()">\u21BB Refresh</button></div><div class="scroll-row" id="tvidRow">'+Array(5).fill('<div class="skeleton skeleton-card" style="flex:0 0 380px;height:320px"></div>').join('')+'</div></div>';
  try{
    var r=await fetch('/api/twitter-videos');var d=await r.json();
    if(d.tweets&&d.tweets.length>0){renderTVidRow(d.tweets)}
    else{document.getElementById('tvidRow').innerHTML='<div style="padding:30px;color:var(--text-muted);font-size:.9rem">No video tweets found. Make sure TWITTER_BEARER_TOKEN is set, or click Refresh.</div>'}
  }catch(e){console.error('Twitter videos error:',e);var row=document.getElementById('tvidRow');if(row)row.innerHTML='<div style="padding:30px;color:var(--text-muted);font-size:.9rem">Could not load Twitter videos. Click Refresh to retry.</div>'}
}

function renderTVidRow(tweets){
  var row=document.getElementById('tvidRow');if(!row)return;
  row.innerHTML=tweets.map(function(t,i){
    var tierClass={'official':'tier-official','creator':'tier-creator','news':'tier-news'}[t.tier]||'tier-news';
    var tierLabel={'official':'OFFICIAL','creator':'CREATOR','news':'NEWS'}[t.tier]||'NEWS';
    return '<div class="topic-card tvid-card" style="animation:fadeSlide .4s ease '+i*.06+'s both">'+
      '<div class="card-image" style="height:180px;position:relative">'+
        (t.video_thumbnail?'<img src="'+t.video_thumbnail+'" alt="" loading="lazy" onerror="this.style.display=\'none\'">':'<div class="placeholder">\uD83D\uDCF9</div>')+
        '<div class="card-gradient"></div>'+
        '<div class="tvid-play-icon">\u25B6</div>'+
        '<div class="card-source-badge" style="background:rgba(29,155,240,.25);color:#1d9bf0;border:1px solid rgba(29,155,240,.3)">\uD835\uDD4F @'+escHtml(t.username)+'</div>'+
        '<div class="tvid-tier-badge '+tierClass+'">'+tierLabel+'</div>'+
        (t.video_duration_str&&t.video_duration_str!=='?'?'<div class="tvid-dur">'+t.video_duration_str+'</div>':'')+
      '</div>'+
      '<div class="card-body" style="padding:14px 18px">'+
        '<div class="tvid-author">'+
          (t.avatar?'<img class="tvid-avatar" src="'+t.avatar+'" alt="">':'')+
          '<span style="font-weight:700;font-size:.85rem">'+escHtml(t.author)+'</span>'+
          (t.verified?'<span class="tvid-verified">\u2713</span>':'')+
          '<span class="tvid-handle">@'+escHtml(t.username)+'</span>'+
        '</div>'+
        '<div class="card-title" style="font-size:.9rem;-webkit-line-clamp:3">'+escHtml(t.title)+'</div>'+
        '<div class="tvid-engagement">'+
          (t.likes_str?'<span>\u2764\uFE0F '+t.likes_str+'</span>':'')+
          (t.retweets_str?'<span>\uD83D\uDD01 '+t.retweets_str+'</span>':'')+
          (t.views_str?'<span>\uD83D\uDC41 '+t.views_str+'</span>':'')+
          '<span>\uD83D\uDD52 '+t.time_ago+'</span>'+
        '</div>'+
        '<div class="card-actions" style="margin-top:10px">'+
          '<button class="btn-card btn-download" onclick="event.stopPropagation();downloadTwitterVideo(\''+escAttr(t.url)+'\',\''+escAttr(t.title)+'\')">\u2B07 Download</button>'+
          '<button class="btn-card btn-campaign" onclick="event.stopPropagation();generate(\''+escAttr(t.title)+'\')">\u26A1 Generate</button>'+
          '<button class="btn-card btn-tweet" onclick="event.stopPropagation();window.open(\''+t.url+'\',\'_blank\')">\uD835\uDD4F Tweet</button>'+
        '</div>'+
      '</div></div>';
  }).join('');
}

async function downloadTwitterVideo(tweetUrl,title){
  if(!confirm('Download this video and upload to Supabase?\n\n'+title))return;
  try{
    var resp=await fetch('/api/videos/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:tweetUrl})});
    var data=await resp.json();
    if(data.status==='success'&&data.supabase_url){
      var toast=document.createElement('div');
      toast.style.cssText='position:fixed;bottom:32px;right:32px;z-index:400;background:#1a1a2e;border:1px solid #1d9bf0;border-radius:14px;padding:20px 24px;max-width:420px;box-shadow:0 12px 40px rgba(29,155,240,.2);animation:fadeSlide .4s ease';
      toast.innerHTML='<div style="font-family:\'Bebas Neue\',sans-serif;font-size:1.2rem;letter-spacing:1px;color:#1d9bf0;margin-bottom:8px">\u2705 VIDEO DOWNLOADED</div><div style="font-size:.85rem;color:var(--text-secondary);margin-bottom:6px">'+escHtml(title.substring(0,80))+'</div><div style="font-size:.75rem;color:var(--text-muted);margin-bottom:10px">'+(data.size_mb?data.size_mb+' MB':'')+'</div><a href="'+data.supabase_url+'" target="_blank" style="color:#1d9bf0;font-size:.8rem;word-break:break-all">View hosted video \u2197</a><button onclick="this.parentElement.remove()" style="position:absolute;top:8px;right:12px;background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:1rem">\u2715</button>';
      document.body.appendChild(toast);setTimeout(function(){toast.remove()},12000);
    }else{alert('Download issue: '+(data.error||'Check Supabase credentials'))}
  }catch(e){alert('Download failed: '+e.message)}
}

window._loadTVids=loadTwitterVideos;
setTimeout(loadTwitterVideos,2500);
})();
"""

@app.get("/api/twitter-videos/inject.js")
async def twitter_videos_inject_js():
    """Serve the Twitter Videos UI module as a self-contained JS file."""
    return Response(content=TWITTER_VIDEOS_INJECT_JS, media_type="application/javascript")

# ─── SHORTS REWRITER ENDPOINTS ────────────────────────────────────
@app.post("/api/shorts/generate")
async def generate_shorts_ideas(request: Request):
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
    try:
        data = await fetch_all_trending(page=0)
        topics = data.get("topics", [])
        shorts = await rewrite_for_shorts(topics, max_topics=12)
        return JSONResponse({"shorts": shorts, "count": len(shorts)})
    except Exception as e:
        return JSONResponse({"error": str(e), "shorts": []}, status_code=500)

SHORTS_INJECT_JS = r"""
(function(){
var css=document.createElement('style');
css.textContent='.shorts-section{padding:20px 0 10px;position:relative;z-index:3}.shorts-section .section-title{color:var(--accent-secondary)}.shorts-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.6rem;font-weight:700;letter-spacing:.5px;text-transform:uppercase;margin-left:8px}.badge-drama{background:rgba(229,9,20,.15);color:var(--accent)}.badge-free_resource{background:rgba(0,212,255,.15);color:var(--accent-secondary)}.badge-tool_discovery{background:rgba(139,92,246,.15);color:#a78bfa}.badge-competition{background:rgba(251,146,60,.15);color:#fb923c}.badge-secret_leak{background:rgba(244,63,94,.15);color:#f43f5e}.badge-how_to{background:rgba(34,197,94,.15);color:#22c55e}.badge-career{background:rgba(59,130,246,.15);color:#3b82f6}.badge-mind_blown{background:rgba(168,85,247,.15);color:#a855f7}.shorts-card .card-title{font-size:1.05rem;line-height:1.3}.shorts-card .card-body{padding:18px 20px}.shorts-original{font-size:.7rem;color:var(--text-muted);margin-top:6px;font-style:italic;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}.btn-shorts-refresh{padding:6px 16px;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text-muted);font-size:.75rem;cursor:pointer;font-family:inherit;transition:all .2s}.btn-shorts-refresh:hover{border-color:var(--accent-secondary);color:var(--accent-secondary)}';
document.head.appendChild(css);
var feed=document.getElementById('feedContainer');
if(feed){var sec=document.createElement('div');sec.id='shortsSection';feed.parentNode.insertBefore(sec,feed)}
async function loadShortsIdeas(){
  var c=document.getElementById('shortsSection');if(!c)return;
  c.innerHTML='<div class="shorts-section"><div class="section-header"><div class="section-title"><span class="icon">\uD83C\uDFAC</span> SHORTS IDEAS <span class="count">AI-rewritten</span></div><button class="btn-shorts-refresh" onclick="window._loadShorts()">\u21BB Refresh</button></div><div class="scroll-row" id="shortsRow">'+Array(5).fill('<div class="skeleton skeleton-card"></div>').join('')+'</div></div>';
  try{var r=await fetch('/api/shorts/generate');var d=await r.json();
    if(d.shorts&&d.shorts.length>0){renderShortsRow(d.shorts)}
    else{document.getElementById('shortsRow').innerHTML='<div style="padding:30px;color:var(--text-muted);font-size:.9rem">Shorts ideas loading\u2026 Click Refresh in a moment.</div>'}
  }catch(e){console.error('Shorts error:',e);var row=document.getElementById('shortsRow');if(row)row.innerHTML='<div style="padding:30px;color:var(--text-muted);font-size:.9rem">Could not load shorts ideas. Click Refresh to retry.</div>'}
}
function renderShortsRow(shorts){
  var row=document.getElementById('shortsRow');if(!row)return;
  row.innerHTML=shorts.map(function(s,i){
    var bc={'drama':'badge-drama','free_resource':'badge-free_resource','tool_discovery':'badge-tool_discovery','competition':'badge-competition','secret_leak':'badge-secret_leak','how_to':'badge-how_to','career':'badge-career','mind_blown':'badge-mind_blown'}[s.hook_type]||'badge-drama';
    var ht=s.hook_type?s.hook_type.replace(/_/g,' '):'';
    var pe=['\uD83C\uDFAC','\uD83D\uDCF1','\u26A1','\uD83D\uDD25','\uD83D\uDCA1','\uD83D\uDE80','\uD83E\uDDE0','\uD83C\uDFAF'][i%8];
    return '<div class="topic-card shorts-card" style="animation:fadeSlide .4s ease '+i*.06+'s both;flex:0 0 360px"><div class="card-image"><div class="placeholder">'+pe+'</div><div class="card-gradient"></div><div class="card-source-badge" style="background:rgba(0,212,255,.2);color:var(--accent-secondary);border:1px solid rgba(0,212,255,.3)">\uD83C\uDFAC SHORTS IDEA</div>'+(ht?'<div class="card-score"><span class="shorts-badge '+bc+'">'+ht+'</span></div>':'')+'</div><div class="card-body"><div class="card-title">'+escHtml(s.title)+'</div><div class="card-meta"><span>'+(s.time_ago||'Recent')+'</span><span>'+(s.source_name||s.source||'')+'</span></div><div class="card-why">'+escHtml(s.angle||s.why_trending||'')+'</div>'+(s.original_title?'<div class="shorts-original">\u2190 '+escHtml(s.original_title)+'</div>':'')+'<div class="card-actions"><button class="btn-card btn-campaign" onclick="event.stopPropagation();generate(\''+escAttr(s.title)+'\')">\u26A1 Generate</button><button class="btn-card btn-video" onclick="event.stopPropagation();openVideoPicker(\''+escAttr(s.title)+'\')">\uD83C\uDFAC Video</button><button class="btn-card btn-preview" onclick="event.stopPropagation();window.open(\''+(s.url||'#')+'\',\'_blank\')">\u2197 Source</button></div></div></div>'
  }).join('')}
window._loadShorts=loadShortsIdeas;
setTimeout(loadShortsIdeas,1500);
})();
"""

@app.get("/api/shorts/inject.js")
async def shorts_inject_js():
    return Response(content=SHORTS_INJECT_JS, media_type="application/javascript")

# ─── VIDEO RESEARCH ENDPOINTS ─────────────────────────────────────
@app.post("/api/videos/search")
async def video_search(request: Request):
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
    return {"status": "healthy", "app": "AJ Content Engine", "version": "3.2.0", "agents": 6,
        "features": ["trending_feed", "one_click_generate", "multi_agent_pipeline", "video_research", "shorts_rewriter", "twitter_video_feed"],
        "keys": {k: bool(os.getenv(v)) for k, v in {"anthropic": "ANTHROPIC_API_KEY", "serper": "SERPER_API_KEY", "gemini": "GEMINI_API_KEY", "twitter": "TWITTER_BEARER_TOKEN", "linkedin": "LINKEDIN_ACCESS_TOKEN", "bluesky": "BLUESKY_HANDLE", "reddit": "REDDIT_CLIENT_ID", "telegram": "TELEGRAM_BOT_TOKEN", "sendgrid": "SENDGRID_API_KEY", "supabase": "SUPABASE_URL"}.items()}}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
