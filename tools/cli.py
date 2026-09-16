#!/usr/bin/env python3
"""
InnerTube Pro - Developer CLI Tool
-----------------------------------
Command-line interface for inspecting, downloading, and analyzing
YouTube media streams via the reverse-engineered InnerTube gateway.

Usage:
  python3 tools/cli.py inspect <URL_OR_ID>
  python3 tools/cli.py download <URL_OR_ID> [--quality 1080p|720p|480p|360p|mp3|m4a]
  python3 tools/cli.py transcript <URL_OR_ID> [--lang en|ar]
  python3 tools/cli.py sponsorblock <URL_OR_ID>
"""

import sys
import os
import argparse
import json
import urllib.request
import urllib.parse
import re

# Add parent directory to path so we can import server helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

def cmd_inspect(args):
    print(f"⚡ Inspecting target: {args.target}...")
    res = server.inspect_youtube_url(args.target)
    if res.get("status") == "success":
        print("\n" + "=" * 60)
        print(f"🎬 Title:    {res.get('title')}")
        print(f"👤 Channel:  {res.get('channel')}")
        print(f"⏱️ Duration: {res.get('duration')}")
        print(f"👁️ Views:    {res.get('views')}")
        print(f"🔗 Target:   {res.get('url')}")
        print("=" * 60)
        print("Available Stream Qualities & Formats:")
        for q in res.get("qualities", []):
            print(f"  • [{q['quality'].upper():<6}] {q['label']} ({q['type']})")
        print("=" * 60 + "\n")
    else:
        print(f"❌ Error: {res.get('message')}")

def cmd_download(args):
    target = args.target.strip()
    vid = target
    if "watch?v=" in target:
        vid = target.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in target:
        vid = target.split("youtu.be/")[1].split("?")[0]

    quality = args.quality
    mtype = "audio" if quality in ["mp3", "m4a"] else "video"

    print(f"⚡ Initiating download for ID: {vid} (Quality: {quality})...")
    res = server.download_video_local(vid, media_type=mtype, quality=quality, title="video")
    if res.get("status") == "success":
        print("\n✅ Download Successful!")
        print(f"📁 File: {res.get('filename')}")
        print(f"📦 Size: {res.get('size')}")
        print(f"📍 Path: {res.get('path')}")
        if res.get("cached"):
            print("⚡ Served instantly from local cache (0.003s)")
    else:
        print(f"❌ Download Failed: {res.get('message')}")

def cmd_sponsorblock(args):
    target = args.target.strip()
    vid = target
    if "watch?v=" in target:
        vid = target.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in target:
        vid = target.split("youtu.be/")[1].split("?")[0]

    print(f"🛡️ Checking SponsorBlock segments for: {vid}...")
    url = f"https://sponsor.ajay.app/api/skipSegments?videoID={vid}"
    req = urllib.request.Request(url, headers={"User-Agent": "InnerTubePro-CLI/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            print(f"\n✅ Found {len(data)} Sponsor/Interruption segment(s):")
            for idx, seg in enumerate(data, 1):
                start, end = seg.get("segment", [0, 0])
                duration = end - start
                category = seg.get("category", "sponsor")
                print(f"  {idx}. [{category.upper():<12}] {start:.1f}s -> {end:.1f}s (Length: {duration:.1f}s)")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("✨ Clean video: No sponsor segments reported for this ID.")
        else:
            print(f"⚠️ SponsorBlock server returned code: {e.code}")
    except Exception as e:
        print(f"❌ Error connecting to SponsorBlock API: {e}")

def main():
    parser = argparse.ArgumentParser(description="InnerTube Pro Developer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a YouTube URL or Video ID")
    inspect_parser.add_argument("target", help="YouTube URL or 11-char Video ID")

    # Download
    download_parser = subparsers.add_parser("download", help="Download media stream directly")
    download_parser.add_argument("target", help="YouTube URL or Video ID")
    download_parser.add_argument("--quality", default="720p", choices=["1080p", "720p", "480p", "360p", "mp3", "m4a"], help="Stream quality")

    # SponsorBlock
    sb_parser = subparsers.add_parser("sponsorblock", help="Fetch SponsorBlock segments")
    sb_parser.add_argument("target", help="YouTube URL or Video ID")

    args = parser.parse_args()
    if args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "sponsorblock":
        cmd_sponsorblock(args)

if __name__ == "__main__":
    main()
