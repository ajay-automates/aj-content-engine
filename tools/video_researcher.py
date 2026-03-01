"""AJ Content Engine — Video Research & Download Module
Uses yt-dlp for YouTube search + multi-platform download,
Serper API to find official demo/promo videos,
Supabase Storage for permanent video hosting.
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
                    "channel": data.get("channel") or data.get("uploader") or "Unknown",
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
#  2. SERPER VIDEO SEARCH (Google, Twitter, Web)
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
                json={"q": f"{query} official video demo", "num": max_results}
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
#  3. COMBINED SEARCH — Returns 3-5 deduplicated options
# ═══════════════════════════════════════════════════════════════════
async def search_videos(topic: str, max_results: int = 5) -> list[dict]:
    """Search YouTube + Serper in parallel, deduplicate, return top results."""
    yt_task = asyncio.create_task(search_youtube(topic, max_results=4))
    serper_task = asyncio.create_task(search_serper_videos(topic, max_results=4))

    yt_results, serper_results = await asyncio.gather(yt_task, serper_task, return_exceptions=True)

    all_videos = []
    if isinstance(yt_results, list):
        all_videos.extend(yt_results)
    if isinstance(serper_results, list):
        all_videos.extend(serper_results)

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

    # Sort: YouTube first (more reliable download), then by views
    unique.sort(key=lambda v: (0 if v["source"] == "youtube" else 1, -(v.get("views") or 0)))
    return unique[:max_results]


# ═══════════════════════════════════════════════════════════════════
#  4. DOWNLOAD VIDEO VIA yt-dlp
# ═══════════════════════════════════════════════════════════════════
async def download_video(url: str, max_duration: int = MAX_VIDEO_DURATION) -> Optional[dict]:
    """Download video to temp file using yt-dlp. Returns file info dict."""
    tmp_dir = tempfile.mkdtemp(prefix="ajvideo_")
    output_template = os.path.join(tmp_dir, "%(title).50s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--max-filesize", f"{MAX_VIDEO_SIZE_MB}M",
        "--socket-timeout", "30",
        "--no-playlist",
        "--no-warnings",
        "--output", output_template,
    ]
    if max_duration:
        cmd.extend(["--match-filter", f"duration<={max_duration}"])
    cmd.append(url)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            err_msg = stderr.decode()[:500]
            logger.error("yt-dlp download failed (code %d): %s", proc.returncode, err_msg)
            return None

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
        result["error"] = "Download failed — video may be too long, too large, or geo-restricted."
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
