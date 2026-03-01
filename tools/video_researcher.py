"""AJ Content Engine — Video Research & Download Module
Uses yt-dlp for YouTube search + multi-platform download,
Serper API to find official demo/promo videos,
Supabase Storage for permanent video hosting.

SMART SEARCH: Prioritizes screen recordings, demos, tutorials, and official
product clips over news coverage. Filters out TV news channels (CNN, CNBC, etc.)
to surface usable B-roll content for Shorts creation.
"""
import os
import re
import json
import uuid
import asyncio
import logging
import tempfile
import subprocess
from typing import Optional
from datetime import datetime

import httpx

logger = logging.getLogger("video_researcher")

# ─── CONFIG ───────────────────────────────────────────────────────
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_VIDEO_BUCKET", "videos")

MAX_VIDEO_SIZE_MB = 100
MAX_VIDEO_DURATION = 600  # 10 min cap
ALLOWED_FORMATS = {"mp4", "webm", "mov"}

# ─── NEWS CHANNEL BLOCKLIST ──────────────────────────────────────
# These channels produce news *about* AI but not usable B-roll/demos.
NEWS_CHANNELS_BLOCKLIST = {
    # US TV News
    "cnn", "cnbc", "cnbc television", "fox news", "fox business",
    "msnbc", "abc news", "cbs news", "nbc news", "pbs newshour",
    # International TV
    "bbc news", "bbc", "sky news", "al jazeera", "dw news",
    "france 24", "reuters", "associated press", "ap",
    # Business/Finance TV
    "bloomberg television", "bloomberg", "bloomberg technology",
    "yahoo finance", "the wall street journal", "wsj",
    # Talk shows / Panels
    "the daily show", "last week tonight", "joe rogan",
    "lex fridman",  # long-form interviews, not B-roll
}

# ─── SEARCH QUERY TEMPLATES ──────────────────────────────────────
# Multiple search strategies to find usable content, not news coverage
DEMO_SUFFIXES = [
    "demo",
    "tutorial walkthrough",
    "screen recording how to use",
    "official announcement",
]


# ═══════════════════════════════════════════════════════════════════
#  1. YOUTUBE SEARCH VIA yt-dlp
# ═══════════════════════════════════════════════════════════════════
async def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """Search YouTube via yt-dlp and return metadata for top results."""
    search_url = f"ytsearch{max_results}:{query}"
    cmd = [
        "yt-dlp", "--dump-json", "--no-download", "--flat-playlist",
        "--no-warnings", "--quiet", search_url
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        results = []
        for line in stdout.decode().strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                duration = data.get("duration") or 0
                channel = data.get("channel") or data.get("uploader") or "Unknown"
                results.append({
                    "id": str(uuid.uuid4())[:8],
                    "source": "youtube",
                    "platform": "YouTube",
                    "video_id": data.get("id", ""),
                    "title": data.get("title", "Untitled"),
                    "url": data.get("url") or f"https://www.youtube.com/watch?v={data.get('id', '')}",
                    "thumbnail": data.get("thumbnail") or data.get("thumbnails", [{}])[-1].get("url", ""),
                    "duration": duration,
                    "duration_str": f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "?",
                    "channel": channel,
                    "views": data.get("view_count") or 0,
                    "views_str": _format_views(data.get("view_count") or 0),
                    "upload_date": data.get("upload_date", ""),
                    "description": (data.get("description") or "")[:200],
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return results
    except asyncio.TimeoutError:
        logger.warning("YouTube search timed out for: %s", query)
        return []
    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        return []
    except Exception as e:
        logger.error("YouTube search error: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════════
#  2. SERPER VIDEO SEARCH (Google Videos)
# ═══════════════════════════════════════════════════════════════════
async def search_serper_videos(query: str, max_results: int = 5) -> list[dict]:
    """Search for videos via Serper API (Google Videos endpoint)."""
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set — skipping Serper video search")
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://google.serper.dev/videos",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": max_results}
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for v in data.get("videos", [])[:max_results]:
            link = v.get("link", "")
            platform = _detect_platform(link)
            duration = _parse_duration(v.get("duration", ""))
            results.append({
                "id": str(uuid.uuid4())[:8],
                "source": "serper",
                "platform": platform,
                "video_id": _extract_video_id(link),
                "title": v.get("title", "Untitled"),
                "url": link,
                "thumbnail": v.get("imageUrl") or v.get("thumbnailUrl", ""),
                "duration": duration,
                "duration_str": v.get("duration", "?"),
                "channel": v.get("channel") or v.get("source", "Unknown"),
                "views": 0,
                "views_str": "",
                "upload_date": v.get("date", ""),
                "description": (v.get("snippet") or "")[:200],
            })
        return results
    except Exception as e:
        logger.error("Serper video search error: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════════
#  3. SMART SEARCH — Multi-strategy, filtered, scored
# ═══════════════════════════════════════════════════════════════════
async def search_videos(topic: str, max_results: int = 5) -> list[dict]:
    """Smart video search: runs multiple query strategies in parallel,
    filters out news channels, scores by usability for Shorts B-roll,
    and returns the best options."""

    # Extract the core subject for smarter queries
    core_topic = _extract_core_subject(topic)

    # Strategy 1: Direct topic + "demo" (finds product demos)
    # Strategy 2: Core subject + "tutorial walkthrough" (finds screen recordings)
    # Strategy 3: Core subject + "official announcement" (finds launch clips)
    # Strategy 4: Serper with demo focus
    tasks = [
        search_youtube(f"{core_topic} demo", max_results=4),
        search_youtube(f"{core_topic} tutorial walkthrough", max_results=3),
        search_youtube(f"{core_topic} official announcement", max_results=3),
        search_serper_videos(f"{core_topic} demo tutorial screen recording", max_results=4),
    ]

    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_videos = []
    for result in raw_results:
        if isinstance(result, list):
            all_videos.extend(result)

    # Deduplicate by video_id or similar title
    seen_ids = set()
    seen_titles = set()
    unique = []
    for v in all_videos:
        vid = v.get("video_id", "")
        title_key = re.sub(r'[^a-z0-9]', '', v["title"].lower())[:40]
        if vid and vid in seen_ids:
            continue
        if title_key in seen_titles:
            continue
        seen_ids.add(vid)
        seen_titles.add(title_key)
        unique.append(v)

    # Filter out news channels
    filtered = [v for v in unique if not _is_news_channel(v.get("channel", ""))]

    # If filtering removed everything, keep originals but deprioritize news
    if not filtered and unique:
        filtered = unique

    # Score each video for B-roll usability
    scored = []
    for v in filtered:
        score = _compute_broll_score(v)
        scored.append((score, v))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in scored[:max_results]]


# ═══════════════════════════════════════════════════════════════════
#  4. DOWNLOAD VIDEO VIA yt-dlp
# ═══════════════════════════════════════════════════════════════════
async def download_video(url: str, max_duration: int = MAX_VIDEO_DURATION) -> Optional[dict]:
    """Download video to temp file using yt-dlp. Returns file info dict."""
    tmp_dir = tempfile.mkdtemp(prefix="ajvideo_")
    output_template = os.path.join(tmp_dir, "%(title).50s.%(ext)s")

    cmd = [
        "yt-dlp",
        # Use iOS player client — bypasses YouTube bot detection on server IPs
        "--extractor-args", "youtube:player_client=ios,web",
        # Simplified format selector: prefer mp4 ≤720p, fall back to anything
        "--format", "best[height<=720][ext=mp4]/best[height<=720]/best",
        "--merge-output-format", "mp4",
        "--max-filesize", f"{MAX_VIDEO_SIZE_MB}M",
        "--socket-timeout", "30",
        "--no-playlist",
        "--no-warnings",
        "--no-check-certificates",
        "--geo-bypass",
        "--add-header", "Accept-Language:en-US,en;q=0.9",
        "--output", output_template,
    ]
    cmd.append(url)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)

        if proc.returncode != 0:
            err_msg = stderr.decode()[:800]
            logger.error("yt-dlp download failed (code %d): %s", proc.returncode, err_msg)
            return {"_error": err_msg}  # Return error details for caller

        # Find the downloaded file
        downloaded = None
        for f in os.listdir(tmp_dir):
            if f.endswith((".mp4", ".webm", ".mov", ".mkv")):
                downloaded = os.path.join(tmp_dir, f)
                break

        if not downloaded or not os.path.exists(downloaded):
            logger.error("No video file found after download")
            return None

        size_mb = os.path.getsize(downloaded) / (1024 * 1024)
        return {
            "filepath": downloaded,
            "filename": os.path.basename(downloaded),
            "size_mb": round(size_mb, 2),
            "tmp_dir": tmp_dir,
        }

    except asyncio.TimeoutError:
        logger.error("Video download timed out for: %s", url)
        return None
    except Exception as e:
        logger.error("Video download error: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════
#  5. UPLOAD TO SUPABASE STORAGE
# ═══════════════════════════════════════════════════════════════════
async def upload_to_supabase(filepath: str, filename: str = None) -> Optional[str]:
    """Upload video file to Supabase Storage, return public URL."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase credentials not set — skipping upload")
        return None

    if not filename:
        filename = os.path.basename(filepath)

    # Clean filename + add unique prefix
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    storage_path = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid.uuid4().hex[:8]}_{safe_name}"

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{storage_path}"

    try:
        with open(filepath, "rb") as f:
            file_data = f.read()

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                upload_url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "video/mp4",
                    "x-upsert": "true",
                },
                content=file_data,
            )
            resp.raise_for_status()

        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_path}"
        logger.info("Uploaded to Supabase: %s (%.1f MB)", storage_path, len(file_data)/(1024*1024))
        return public_url

    except Exception as e:
        logger.error("Supabase upload error: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════
#  6. FULL PIPELINE: Search → Pick → Download → Upload
# ═══════════════════════════════════════════════════════════════════
async def select_and_host_video(video_url: str) -> dict:
    """Download a selected video and upload to Supabase for permanent hosting."""
    result = {"status": "error", "url": None, "supabase_url": None, "error": None}

    dl = await download_video(video_url)
    if not dl:
        result["error"] = "Download failed — yt-dlp returned no output. Check server logs."
        return result
    if "_error" in dl:
        # Surface the actual yt-dlp error message
        raw_err = dl["_error"]
        if "Sign in" in raw_err or "bot" in raw_err.lower():
            result["error"] = "YouTube blocked the download (bot detection). Try a different video or a direct MP4 URL."
        elif "This video is not available" in raw_err or "unavailable" in raw_err.lower():
            result["error"] = "Video is unavailable or geo-restricted in the server's region."
        elif "File is larger" in raw_err or "filesize" in raw_err.lower():
            result["error"] = f"Video exceeds {MAX_VIDEO_SIZE_MB}MB size limit."
        else:
            result["error"] = f"Download failed: {raw_err[:300]}"
        return result

    result["local_file"] = dl["filename"]
    result["size_mb"] = dl["size_mb"]

    # Upload to Supabase
    public_url = await upload_to_supabase(dl["filepath"], dl["filename"])
    if public_url:
        result["status"] = "success"
        result["supabase_url"] = public_url
    else:
        result["status"] = "downloaded"
        result["error"] = "Upload to Supabase failed — check credentials. Video was downloaded successfully."

    # Cleanup temp file
    try:
        import shutil
        shutil.rmtree(dl["tmp_dir"], ignore_errors=True)
    except Exception:
        pass

    return result


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════
def _format_views(count: int) -> str:
    if count >= 1_000_000:
        return f"{count/1_000_000:.1f}M views"
    if count >= 1_000:
        return f"{count/1_000:.1f}K views"
    if count > 0:
        return f"{count} views"
    return ""

def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "Twitter/X"
    if "vimeo.com" in url_lower:
        return "Vimeo"
    if "tiktok.com" in url_lower:
        return "TikTok"
    if "dailymotion.com" in url_lower:
        return "Dailymotion"
    return "Web"

def _extract_video_id(url: str) -> str:
    yt_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if yt_match:
        return yt_match.group(1)
    return url.split("/")[-1].split("?")[0][:20]

def _parse_duration(dur_str: str) -> int:
    """Parse duration strings like '3:45' or '1:02:30' into seconds."""
    if not dur_str or dur_str == "?":
        return 0
    parts = dur_str.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0])
    except (ValueError, IndexError):
        return 0

def _is_news_channel(channel: str) -> bool:
    """Check if a channel is in the TV news blocklist."""
    return channel.strip().lower() in NEWS_CHANNELS_BLOCKLIST

def _extract_core_subject(topic: str) -> str:
    """Extract the core product/company/tool name from a topic title.
    E.g. 'Anthropic just rejected the Pentagon' -> 'Anthropic Pentagon AI'
    E.g. 'China\\'s new model beating GPT 5.2' -> 'China AI model GPT'
    """
    # Remove common filler words to get the searchable core
    filler = {"just", "the", "this", "that", "is", "are", "was", "were", "has", "have",
              "had", "been", "being", "a", "an", "of", "in", "on", "for", "to", "and",
              "but", "or", "so", "yet", "with", "from", "by", "at", "it", "its",
              "might", "could", "would", "should", "will", "can", "may", "do", "does",
              "did", "not", "all", "very", "really", "here", "there", "now", "new",
              "just", "out", "about", "how", "what", "when", "where", "who", "why",
              "every", "some", "any", "no", "only", "own", "your", "our", "my"}
    words = re.sub(r'[^\w\s]', ' ', topic).split()
    core = [w for w in words if w.lower() not in filler and len(w) > 1]
    # Keep max 5 core words to make a focused query
    result = " ".join(core[:5])
    return result if result else topic

def _compute_broll_score(video: dict) -> float:
    """Score a video for B-roll usability in Shorts creation.
    Higher = more likely to be a usable demo/screen recording.
    Lower = more likely to be news coverage / talking heads."""
    score = 0.0
    title = (video.get("title") or "").lower()
    channel = (video.get("channel") or "").lower()
    desc = (video.get("description") or "").lower()
    duration = video.get("duration") or 0
    views = video.get("views") or 0
    text = title + " " + desc

    # ── BOOST: Demo/tutorial/screen recording indicators ──
    demo_words = ["demo", "tutorial", "walkthrough", "how to", "screen recording",
                  "hands on", "hands-on", "first look", "getting started",
                  "overview", "features", "introduction", "intro to",
                  "using", "setup", "guide", "showcase", "preview"]
    for w in demo_words:
        if w in text:
            score += 200

    # ── BOOST: Official product channels ──
    official_channels = ["google", "openai", "anthropic", "microsoft", "apple",
                        "nvidia", "meta", "amazon", "hugging face", "stability ai",
                        "midjourney", "runway", "google deepmind", "google ai"]
    for ch in official_channels:
        if ch in channel:
            score += 300
            break

    # ── BOOST: Tech creator channels (not news) ──
    creator_words = ["matt wolfe", "fireship", "two minute papers", "ai explained",
                     "all about ai", "matt vdm", "corbin brown", "riley brown",
                     "web dev simplified", "theo", "coding in flow"]
    for cw in creator_words:
        if cw in channel:
            score += 150
            break

    # ── BOOST: Short videos (ideal for B-roll, under 3 min) ──
    if 0 < duration <= 60:
        score += 250  # Under 1 min = perfect for shorts
    elif 60 < duration <= 180:
        score += 200  # 1-3 min = great
    elif 180 < duration <= 300:
        score += 100  # 3-5 min = okay
    elif 300 < duration <= 600:
        score += 0    # 5-10 min = meh
    elif duration > 600:
        score -= 200  # Over 10 min = probably not B-roll

    # ── PENALIZE: News coverage indicators ──
    news_words = ["breaking news", "breaking:", "live:", "exclusive:",
                  "report", "reporting", "anchor", "coverage", "interview",
                  "panel discussion", "press conference", "testimony",
                  "hearing", "committee", "correspondent", "analysis"]
    for w in news_words:
        if w in text:
            score -= 300

    # ── PENALIZE: News channels that slipped through blocklist ──
    if _is_news_channel(video.get("channel", "")):
        score -= 500

    # ── PENALIZE: News-like channel patterns ──
    news_patterns = ["news", "tv", "television", "broadcast", "daily", "times",
                     "post", "journal", "herald", "tribune", "gazette"]
    for p in news_patterns:
        if p in channel and channel not in {"product hunt", "hacker news"}:
            score -= 150

    # ── Small view count boost (some signal, not dominant) ──
    if views > 0:
        score += min(views / 10000, 50)  # Cap at +50

    return score
