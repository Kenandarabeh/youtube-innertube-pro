# Contributing to InnerTube Pro ⚡

Thank you for your interest in contributing to **InnerTube Pro**! This project is an open-source research initiative designed to reverse-engineer and explore Google's internal InnerTube (YouTubei) streaming gateway.

---

## 🛠️ Development Setup

1. **Prerequisites**:
   * Python 3.10+
   * `ffmpeg` binary installed on system (`sudo apt install ffmpeg`)

2. **Clone & Run**:
   ```bash
   git clone https://github.com/Kenandarabeh/youtube-innertube-pro.git
   cd youtube-innertube-pro
   chmod +x run.sh
   ./run.sh
   ```
   Open `http://127.0.0.1:5050` in your browser.

3. **Run Automated Diagnostics**:
   Verify network latency, itag parsing, and RFC 5987 compliance:
   ```bash
   python3 tools/test_innertube.py
   ```

---

## 🧭 Architecture Map

* **`server.py`**:
  * Multi-threaded HTTP daemon powered by `http.server.ThreadingHTTPServer`.
  * Recursive renderer scanner `scan_tree(obj)` traversing Server-Driven UI responses.
  * Media download and multiplexing pipeline using `yt-dlp` and `ffmpeg`.
  * RFC 5987 UTF-8 header encoder.
* **`app.js`**:
  * Modular client controller.
  * IntersectionObserver infinite pagination.
  * Cinema player and 9:16 Shorts runner.
* **`style.css`**:
  * Pure Vanilla CSS design system (Obsidian Dark, YouTube Crimson glow).
* **`tools/cli.py`**:
  * Terminal CLI utility for inspecting URLs, downloading streams, and querying SponsorBlock.

---

## 🚀 How to Add a New InnerTube Endpoint

If you want to add support for a new YouTube feature (such as Community Posts, Playlist browsing, or Live Chat):

1. **Identify the InnerTube Endpoint**:
   InnerTube endpoints reside under:
   `https://www.youtube.com/youtubei/v1/[ENDPOINT_NAME]`
   Examples:
   * `/youtubei/v1/browse` (Playlists & Channels)
   * `/youtubei/v1/live_chat/get_live_chat` (Live streams)

2. **Add a Helper in `server.py`**:
   Use `query_innertube()` as a reference to formulate the request with the `context.client` envelope.

3. **Expose the REST Route**:
   In `InnerTubeHandler.do_GET()` (or `do_POST()`), map your route:
   ```python
   if path == "/api/my_new_feature":
       data = fetch_my_feature(...)
       self.send_response(200)
       self.send_header("Content-Type", "application/json; charset=utf-8")
       self.end_cors_headers()
       self.end_headers()
       self.wfile.write(json.dumps(data).encode("utf-8"))
       return
   ```

4. **Update Frontend Controller (`app.js`)**:
   Add UI handlers to display your new feature.

---

## 🧪 Testing Guidelines

Before opening a Pull Request:
1. Run syntax check: `python3 -m py_compile server.py tools/cli.py`
2. Run automated test suite: `python3 tools/test_innertube.py`
3. Test terminal CLI: `python3 tools/cli.py inspect "0e3GPea1Tyg"`

---

## 📜 Pull Request Guidelines

1. Fork the repo and create your branch from `main`.
2. Ensure commit messages are clear (e.g. `feat: add live chat extraction support`).
3. Open a Pull Request on GitHub with a description of changes and screenshots if UI is modified.
