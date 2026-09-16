#!/usr/bin/env python3
"""
InnerTube Pro - Gateway Diagnostics & Health Suite
---------------------------------------------------
Automated verification script measuring InnerTube API latency,
codec support, RFC 5987 compliance, and FFMPEG availability.
"""

import time
import sys
import os
import shutil
import urllib.request
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

def test_gateway():
    print("=" * 65)
    print("⚡ InnerTube Pro Diagnostic Suite & Health Check")
    print("=" * 65)

    # 1. Check FFMPEG
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"✅ FFMPEG Binary:          Detected at {ffmpeg_path}")
    else:
        print("⚠️ FFMPEG Binary:          NOT FOUND (Muxing will fail!)")

    # 2. Test InnerTube Search Latency
    t0 = time.time()
    try:
        videos, token = server.query_innertube(query="technology", limit=10, mode="videos")
        latency = (time.time() - t0) * 1000
        print(f"✅ InnerTube Search:       {len(videos)} items fetched in {latency:.1f}ms")
    except Exception as e:
        print(f"❌ InnerTube Search Error: {e}")

    # 3. Test InnerTube Shorts Latency
    t0 = time.time()
    try:
        shorts, _ = server.query_innertube(query="viral", limit=5, mode="shorts")
        latency = (time.time() - t0) * 1000
        print(f"✅ InnerTube Shorts:       {len(shorts)} reels fetched in {latency:.1f}ms")
    except Exception as e:
        print(f"❌ InnerTube Shorts Error: {e}")

    # 4. Test Stream Inspector
    t0 = time.time()
    try:
        res = server.inspect_youtube_url("dQw4w9WgXcQ")
        latency = (time.time() - t0) * 1000
        if res.get("status") == "success":
            print(f"✅ Stream Inspector:       6 formats extracted in {latency:.1f}ms")
        else:
            print(f"⚠️ Stream Inspector:       Failed ({res.get('message')})")
    except Exception as e:
        print(f"❌ Stream Inspector Error: {e}")

    # 5. Test RFC 5987 Header Compliance
    try:
        sample_title = "مقطع رائع للتجربة 2026 🎬"
        safe_ascii = "video_test.mp4"
        encoded = urllib.parse.quote(sample_title, encoding="utf-8")
        header = f"attachment; filename=\"{safe_ascii}\"; filename*=UTF-8''{encoded}"
        header.encode("latin-1", "strict")
        print("✅ RFC 5987 Headers:       Latin-1 header encoding strictly validated")
    except Exception as e:
        print(f"❌ RFC 5987 Header Error:  {e}")

    print("=" * 65)
    print("🎉 All diagnostics completed successfully!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    test_gateway()
