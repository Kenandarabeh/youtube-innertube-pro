#!/usr/bin/env python3
"""
InnerTube Pro - High-Performance Backend Daemon
-------------------------------------------------
Reverse-engineered YouTube InnerTube (YouTubei) API Server
- Multi-Threaded HTTP Architecture (ThreadingHTTPServer)
- Recursive Server-Driven UI (SDUI) Renderer Traversal
- Infinite Pagination via Continuation Tokens & Qualifiers
- Multi-Quality Stream Multiplexing (yt-dlp + ffmpeg)
- RFC 5987 / RFC 6266 Internationalized Stream Headers
- High-Performance Sub-Second Deduplication & Caching
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import os
import sys
import re
import subprocess
import glob
import shutil
import yt_dlp

PORT = int(os.environ.get("PORT", 5050))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.expanduser('~/Downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def get_cookie_file():
    """Locates YouTube session cookies if available (local, cloud secret file, or env var)."""
    candidates = [
        "/etc/secrets/cookies.txt",
        os.path.join(BASE_DIR, "cookies.txt"),
        os.path.expanduser("~/cookies.txt")
    ]
    for path in candidates:
        try:
            if os.path.exists(path) and os.path.getsize(path) > 50:
                print(f"🍪 Found active cookies file: {path} ({os.path.getsize(path)} bytes)")
                return path
        except Exception as e:
            print(f"Error checking cookie path {path}: {e}")

    # Check environment variable YOUTUBE_COOKIES (for cloud deployments like Render)
    env_cookie = os.environ.get("YOUTUBE_COOKIES")
    if env_cookie and len(env_cookie) > 50:
        target = os.path.join(BASE_DIR, "cookies.txt")
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(env_cookie)
            print(f"🍪 Restored cookies from YOUTUBE_COOKIES env var to {target} ({len(env_cookie)} bytes)")
            return target
        except Exception as e:
            print(f"Error writing env cookie: {e}")

    print(f"⚠️ No cookies found. Candidates: {candidates}")
    return None

# ----------------------------------------------------------------------
# 1. CORE INNERTUBE RECURSIVE SCANNER & QUERY ENGINE
# ----------------------------------------------------------------------

def query_innertube(query="trending", limit=24, mode="videos", continuation=None, page=1):
    """
    Directly queries Google's internal InnerTube API gateway.
    Traverses Server-Driven UI renderers recursively for maximal resilience.
    """
    url = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    effective_query = query
    if page > 1 and not continuation:
        qualifiers = ["new 2026", "official", "highlights", "featured", "top videos"]
        suffix = qualifiers[(page - 2) % len(qualifiers)]
        effective_query = f"{query} {suffix}"

    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20260915.01.00",
                "hl": "en",
                "gl": "US"
            }
        }
    }

    if continuation:
        payload["continuation"] = continuation
    else:
        payload["query"] = effective_query

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as res:
            raw_data = json.loads(res.read().decode("utf-8"))

        results = []
        tokens = []
        seen_ids = set()

        def scan_tree(obj):
            if isinstance(obj, dict):
                # Check for continuation pagination tokens
                if "continuationItemRenderer" in obj:
                    tok = obj["continuationItemRenderer"].get("continuationEndpoint", {}).get("continuationCommand", {}).get("token")
                    if tok and tok not in tokens:
                        tokens.append(tok)

                if len(results) < limit:
                    # Shorts mode
                    if mode == "shorts":
                        if "shortsLockupViewModel" in obj:
                            s = obj["shortsLockupViewModel"]
                            vid = s.get("onTap", {}).get("innertubeCommand", {}).get("reelWatchEndpoint", {}).get("videoId")
                            if not vid:
                                ent = s.get("entityId", "")
                                if ent.startswith("shorts-shelf-item-"):
                                    vid = ent.replace("shorts-shelf-item-", "")
                            if vid and vid not in seen_ids:
                                seen_ids.add(vid)
                                title = s.get("overlayMetadata", {}).get("primaryText", {}).get("content", "Featured Short")
                                views = s.get("overlayMetadata", {}).get("secondaryText", {}).get("content", "100K views")
                                results.append({
                                    "id": vid,
                                    "title": title,
                                    "views": views,
                                    "channel": "YouTube Shorts",
                                    "thumbnail": f"https://i.ytimg.com/vi/{vid}/frame0.jpg",
                                    "type": "short"
                                })
                        elif "reelItemRenderer" in obj:
                            r = obj["reelItemRenderer"]
                            vid = r.get("videoId")
                            if vid and vid not in seen_ids:
                                seen_ids.add(vid)
                                title = r.get("headline", {}).get("simpleText", "Featured Short")
                                views = r.get("viewCountText", {}).get("simpleText", "50K views")
                                results.append({
                                    "id": vid,
                                    "title": title,
                                    "views": views,
                                    "channel": "YouTube Shorts",
                                    "thumbnail": f"https://i.ytimg.com/vi/{vid}/frame0.jpg",
                                    "type": "short"
                                })
                    else:
                        # Standard video renderers
                        for key in ["videoRenderer", "compactVideoRenderer"]:
                            if key in obj:
                                vr = obj[key]
                                vid = vr.get("videoId")
                                if vid and vid not in seen_ids:
                                    seen_ids.add(vid)
                                    title = vr.get("title", {}).get("runs", [{}])[0].get("text") or vr.get("title", {}).get("simpleText", "Untitled Video")
                                    channel = vr.get("ownerText", {}).get("runs", [{}])[0].get("text") or vr.get("shortBylineText", {}).get("runs", [{}])[0].get("text", "YouTube Creator")
                                    views = vr.get("viewCountText", {}).get("simpleText") or vr.get("shortViewCountText", {}).get("simpleText", "15K views")
                                    published = vr.get("publishedTimeText", {}).get("simpleText", "Recently")
                                    length = vr.get("lengthText", {}).get("simpleText", "10:00")
                                    thumbs = vr.get("thumbnail", {}).get("thumbnails", [])
                                    thumb = thumbs[-1].get("url", f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                                    results.append({
                                        "id": vid,
                                        "title": title,
                                        "channel": channel,
                                        "views": views,
                                        "published": published,
                                        "duration": length,
                                        "thumbnail": thumb,
                                        "type": "video"
                                    })
                for v in obj.values():
                    scan_tree(v)
            elif isinstance(obj, list):
                for item in obj:
                    scan_tree(item)

        scan_tree(raw_data)
        next_token = tokens[0] if tokens else None

        if mode == "shorts" and not results:
            vids, _ = query_innertube(f"{query} shorts", limit=limit, mode="videos")
            return vids, None

        return results, next_token
    except Exception as e:
        print(f"Error querying InnerTube gateway: {e}")
        return [], None

# ----------------------------------------------------------------------
# 2. MEDIA DOWNLOAD & MULTIPLEXING ENGINE
# ----------------------------------------------------------------------

def sanitize_filename(title, vid):
    """Sanitizes filename for clean filesystem and RFC 5987 HTTP serialization."""
    cleaned = re.sub(r'[\/\\\:\*\?\"<>\|\r\n\t]', ' ', title)
    cleaned = re.sub(r'[^\w\s\u0600-\u06FF\.\-]', '', cleaned).strip()
    cleaned = re.sub(r'\s+', '_', cleaned)
    if len(cleaned) > 45:
        cleaned = cleaned[:45]
    return cleaned or f"video_{vid}"

def download_video_local(vid, media_type="video", quality="720p", title="video"):
    """
    Downloads media directly onto the local filesystem in ~/Downloads.
    Integrates on-the-fly deduplication and instant caching.
    """
    safe_title = sanitize_filename(title, vid)
    url = f"https://www.youtube.com/watch?v={vid}"

    target_ext = "m4a" if (media_type == "audio" and quality == "m4a") else ("mp3" if media_type == "audio" else "mp4")
    expected_filename = f"{safe_title}.{target_ext}" if media_type == "audio" else f"{safe_title}_{quality}.{target_ext}"
    expected_path = os.path.join(DOWNLOADS_DIR, expected_filename)

    # Instant Caching: check if already downloaded
    if os.path.exists(expected_path) and os.path.getsize(expected_path) > 10240:
        size_mb = os.path.getsize(expected_path) / (1024 * 1024)
        return {
            "status": "success",
            "filename": expected_filename,
            "path": expected_path,
            "size": f"{size_mb:.1f} MB",
            "type": media_type,
            "quality": quality,
            "cached": True
        }

    cookie_file = get_cookie_file()
    resilient_args = []
    if cookie_file:
        resilient_args.extend(["--cookies", cookie_file])
    else:
        resilient_args.extend(["--extractor-args", "youtube:player_client=android,ios"])

    if shutil.which("node"):
        resilient_args.extend(["--js-runtimes", "node"])

    if media_type == "audio":
        if quality == "m4a":
            out_tmpl = os.path.join(DOWNLOADS_DIR, f"{safe_title}.%(ext)s")
            cmd = [
                sys.executable, "-m", "yt_dlp",
                *resilient_args,
                "-f", "ba[ext=m4a]/ba",
                "--no-playlist",
                "--no-mtime",
                "-o", out_tmpl,
                url
            ]
        else:
            out_tmpl = os.path.join(DOWNLOADS_DIR, f"{safe_title}.%(ext)s")
            cmd = [
                sys.executable, "-m", "yt_dlp",
                *resilient_args,
                "-x", "--audio-format", "mp3",
                "--audio-quality", "0",
                "--no-playlist",
                "--no-mtime",
                "-o", out_tmpl,
                url
            ]
    else:
        out_tmpl = os.path.join(DOWNLOADS_DIR, f"{safe_title}_{quality}.%(ext)s")
        if quality == "1080p":
            f_spec = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        elif quality == "720p":
            f_spec = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif quality == "480p":
            f_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        elif quality == "360p":
            f_spec = "bestvideo[height<=360]+bestaudio/best[height<=360]/best"
        else:
            f_spec = "bestvideo+bestaudio/best"

        cmd = [
            sys.executable, "-m", "yt_dlp",
            *resilient_args,
            "-f", f_spec,
            "--merge-output-format", "mp4",
            "--no-playlist",
            "--no-mtime",
            "-o", out_tmpl,
            url
        ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        final_path = expected_path

        if not os.path.exists(final_path):
            prefix = safe_title
            candidates = [
                os.path.join(DOWNLOADS_DIR, f) for f in os.listdir(DOWNLOADS_DIR)
                if f.startswith(prefix) and (f.endswith(f".{target_ext}") or f.endswith(".mp4") or f.endswith(".webm"))
            ]
            if candidates:
                candidates.sort(key=os.path.getmtime, reverse=True)
                final_path = candidates[0]

        if os.path.exists(final_path) and os.path.getsize(final_path) > 1024:
            size_mb = os.path.getsize(final_path) / (1024 * 1024)
            return {
                "status": "success",
                "filename": os.path.basename(final_path),
                "path": final_path,
                "size": f"{size_mb:.1f} MB",
                "type": media_type,
                "quality": quality
            }
        else:
            err_msg = proc.stderr.strip() if proc.stderr else "Media download could not be completed"
            return {
                "status": "error",
                "message": err_msg[:300]
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def inspect_youtube_url(url_or_id):
    """Inspects any YouTube URL or Video ID to extract details and all available qualities."""
    clean_input = url_or_id.strip()
    if len(clean_input) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', clean_input):
        target_url = f"https://www.youtube.com/watch?v={clean_input}"
    else:
        target_url = clean_input

    cookie_file = get_cookie_file()
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True
    }
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file
    else:
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    if shutil.which("node"):
        ydl_opts['js_runtimes'] = {'node': {}}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            vid = info.get('id')
            title = info.get('title') or "YouTube Video"
            duration = info.get('duration_string') or str(info.get('duration') or "10:00")
            thumbnail = info.get('thumbnail') or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            channel = info.get('uploader') or info.get('channel') or "YouTube Creator"
            views = info.get('view_count')
            views_str = f"{views:,} views" if views else "High views"

            return {
                "status": "success",
                "id": vid,
                "title": title,
                "channel": channel,
                "duration": duration,
                "views": views_str,
                "thumbnail": thumbnail,
                "url": target_url,
                "qualities": [
                    {"label": "1080p Full HD (MP4)", "quality": "1080p", "type": "video", "ext": "mp4", "badge": "Full HD ⭐"},
                    {"label": "720p HD (MP4)", "quality": "720p", "type": "video", "ext": "mp4", "badge": "HD Sharp"},
                    {"label": "480p SD (MP4 Balanced)", "quality": "480p", "type": "video", "ext": "mp4", "badge": "Standard"},
                    {"label": "360p Fast Data Saver", "quality": "360p", "type": "video", "ext": "mp4", "badge": "Fast ⚡"},
                    {"label": "320kbps High-Res MP3", "quality": "mp3", "type": "audio", "ext": "mp3", "badge": "MP3 🎵"},
                    {"label": "Original Studio M4A", "quality": "m4a", "type": "audio", "ext": "m4a", "badge": "M4A 🎧"}
                ]
            }
    except Exception as e:
        return {"status": "error", "message": f"Could not inspect link: {str(e)}"}

# ----------------------------------------------------------------------
# 3. HTTP REQUEST DISPATCHER & DAEMON HANDLER
# ----------------------------------------------------------------------

class InnerTubeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/stream_download":
            query_params = urllib.parse.parse_qs(parsed.query)
            vid = query_params.get("id", [""])[0]
            mtype = query_params.get("type", ["video"])[0]
            quality = query_params.get("quality", ["720p"])[0]
            title = query_params.get("title", ["video"])[0]

            dl_res = download_video_local(vid, media_type=mtype, quality=quality, title=title)
            if dl_res.get("status") == "success" and os.path.exists(dl_res["path"]):
                filepath = dl_res["path"]
                filename = dl_res["filename"]
                filesize = os.path.getsize(filepath)
                target_ext = filename.split(".")[-1] if "." in filename else ("mp3" if mtype == "audio" else "mp4")
                mime = "audio/mpeg" if target_ext == "mp3" else ("audio/mp4" if target_ext == "m4a" else "video/mp4")
                safe_ascii_name = f"video_{vid}_{quality}.{target_ext}"
                encoded_filename = urllib.parse.quote(filename, encoding='utf-8')

                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Disposition", f"attachment; filename=\"{safe_ascii_name}\"; filename*=UTF-8''{encoded_filename}")
                self.send_header("Content-Length", str(filesize))
                self.end_cors_headers()
                self.end_headers()
                return
        return super().do_HEAD()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # 1. API: Search with Infinite Scroll
        if path == "/api/search":
            q = query_params.get("q", ["technology trending 2026"])[0]
            continuation = query_params.get("continuation", [None])[0]
            page = int(query_params.get("page", ["1"])[0])
            videos, next_token = query_innertube(q, limit=20, mode="videos", continuation=continuation, page=page)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "query": q,
                "count": len(videos),
                "page": page,
                "continuation": next_token,
                "videos": videos
            }, ensure_ascii=False).encode("utf-8"))
            return

        # 2. API: Shorts Feed
        if path == "/api/shorts":
            q = query_params.get("q", ["shorts viral"])[0]
            if "shorts" not in q.lower():
                q = f"shorts {q}"
            continuation = query_params.get("continuation", [None])[0]
            shorts, next_token = query_innertube(q, limit=20, mode="shorts", continuation=continuation)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "type": "shorts",
                "count": len(shorts),
                "continuation": next_token,
                "shorts": shorts
            }, ensure_ascii=False).encode("utf-8"))
            return

        # 3. API: Trending Categories
        if path == "/api/trending":
            tab = query_params.get("tab", ["general"])[0]
            page = int(query_params.get("page", ["1"])[0])
            continuation = query_params.get("continuation", [None])[0]
            queries = {
                "general": "trending videos today 2026",
                "music": "top new music hits trending",
                "gaming": "best gaming trending gameplay 2026",
                "news": "global world news today live headlines"
            }
            q = queries.get(tab, "trending videos")
            videos, next_token = query_innertube(q, limit=20, mode="videos", continuation=continuation, page=page)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "tab": tab,
                "page": page,
                "count": len(videos),
                "continuation": next_token,
                "videos": videos
            }, ensure_ascii=False).encode("utf-8"))
            return

        # 4. API: Related / Up Next Recommendations
        if path == "/api/related":
            q = query_params.get("q", ["recommended videos"])[0]
            videos, _ = query_innertube(q, limit=14, mode="videos")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"related": videos}, ensure_ascii=False).encode("utf-8"))
            return

        # 5. API: Channel Explorer
        if path == "/api/channel":
            channel_name = query_params.get("name", ["Creator"])[0]
            page = int(query_params.get("page", ["1"])[0])
            continuation = query_params.get("continuation", [None])[0]
            videos, next_token = query_innertube(f'channel "{channel_name}"', limit=20, mode="videos", continuation=continuation, page=page)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "channel": channel_name,
                "page": page,
                "continuation": next_token,
                "videos": videos
            }, ensure_ascii=False).encode("utf-8"))
            return

        # 6. API: Universal Link Inspector
        if path == "/api/inspect_link":
            url = query_params.get("url", [""])[0]
            if not url:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"status":"error","message":"Please provide a valid YouTube link or ID"}')
                return

            result = inspect_youtube_url(url)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        # 7. API: Local Download (Direct to ~/Downloads)
        if path == "/api/download_local":
            vid = query_params.get("id", [""])[0]
            mtype = query_params.get("type", ["video"])[0]
            quality = query_params.get("quality", ["720p"])[0]
            title = query_params.get("title", ["video"])[0]

            result = download_video_local(vid, media_type=mtype, quality=quality, title=title)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            try:
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        # 8. API: Stream Download (RFC 5987 Compliant)
        if path == "/api/stream_download":
            vid = query_params.get("id", [""])[0]
            mtype = query_params.get("type", ["video"])[0]
            quality = query_params.get("quality", ["720p"])[0]
            title = query_params.get("title", ["video"])[0]

            dl_res = download_video_local(vid, media_type=mtype, quality=quality, title=title)
            if dl_res.get("status") == "success" and os.path.exists(dl_res["path"]):
                filepath = dl_res["path"]
                filename = dl_res["filename"]
                filesize = os.path.getsize(filepath)
                target_ext = filename.split(".")[-1] if "." in filename else ("mp3" if mtype == "audio" else "mp4")
                mime = "audio/mpeg" if target_ext == "mp3" else ("audio/mp4" if target_ext == "m4a" else "video/mp4")

                safe_ascii_name = f"video_{vid}_{quality}.{target_ext}"
                encoded_filename = urllib.parse.quote(filename, encoding='utf-8')

                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{safe_ascii_name}\"; filename*=UTF-8''{encoded_filename}"
                )
                self.send_header("Content-Length", str(filesize))
                self.end_cors_headers()
                self.end_headers()

                try:
                    with open(filepath, "rb") as f:
                        while chunk := f.read(128 * 1024):
                            self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            else:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_cors_headers()
                self.end_headers()
                err_text = dl_res.get("message", "Error processing download stream")
                try:
                    self.wfile.write(f"Download Error: {err_text}".encode("utf-8"))
                except Exception:
                    pass
                return

        # 9. API: Download Format Options Matrix
        if path == "/api/download":
            vid = query_params.get("id", [""])[0]
            title = query_params.get("title", ["video"])[0]
            download_options = {
                "id": vid,
                "title": title,
                "downloads_folder": DOWNLOADS_DIR,
                "local_download_url": f"/api/download_local?id={vid}&title={urllib.parse.quote(title)}",
                "stream_download_url": f"/api/stream_download?id={vid}&title={urllib.parse.quote(title)}",
                "qualities": [
                    {"label": "1080p Full HD (MP4)", "type": "video", "ext": "mp4", "quality": "1080p"},
                    {"label": "720p HD (MP4)", "type": "video", "ext": "mp4", "quality": "720p"},
                    {"label": "480p SD (MP4 Balanced)", "type": "video", "ext": "mp4", "quality": "480p"},
                    {"label": "360p Fast Data Saver", "type": "video", "ext": "mp4", "quality": "360p"},
                    {"label": "320kbps High-Res MP3", "type": "audio", "ext": "mp3", "quality": "mp3"},
                    {"label": "Original Studio M4A", "type": "audio", "ext": "m4a", "quality": "m4a"}
                ]
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_cors_headers()
            self.end_headers()
            try:
                self.wfile.write(json.dumps(download_options, ensure_ascii=False).encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        # 10. API: SponsorBlock Segments
        if path == "/api/sponsorblock":
            vid = query_params.get("id", [""])[0]
            if not vid:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"status":"error"}')
                return
            sb_url = f"https://sponsor.ajay.app/api/skipSegments?videoID={vid}"
            req = urllib.request.Request(sb_url, headers={"User-Agent": "InnerTubePro/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    sb_data = json.loads(r.read().decode())
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "segments": sb_data}, ensure_ascii=False).encode("utf-8"))
                    return
            except Exception:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"status": "success", "segments": []}')
                return

        return super().do_GET()

def run_server():
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), InnerTubeHandler) as httpd:
        print(f"⚡ InnerTube Pro Multi-Threaded Daemon is live on http://127.0.0.1:{PORT} and http://0.0.0.0:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down daemon.")

if __name__ == "__main__":
    run_server()
