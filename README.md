# 🎬 ReelScript

Turn any public reel or short video into clean, timestamped English text.
Real audio extraction (yt-dlp + ffmpeg) and speech-to-text via **Groq's free Whisper API**.

Supports Instagram, TikTok, YouTube Shorts, Twitter/X, and Facebook.

---

## ✨ Features
- Paste a link → get a clean transcript with timestamps
- Powered by `whisper-large-v3` on Groq (fast, free tier)
- Premium dark UI, history, copy / download / export
- No per-user API key needed — the server holds one key for everyone

---

## 🚀 Run locally (Windows)

1. **Install ffmpeg** (one time): `winget install ffmpeg`
2. **Install Python deps**: `pip install -r requirements.txt`
3. Set your free Groq key (from <https://console.groq.com/keys>):
   ```powershell
   $env:GROQ_API_KEY = "gsk_your_key_here"
   ```
4. Start the server: `python server.py`
5. Open <http://localhost:5050>

> On Windows you can also just double-click **`Start Server.bat`** (set `GROQ_API_KEY`
> in your environment first, or each visitor can run their own key).

---

## ☁️ Deploy to Railway

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo** → pick this repo.
3. Railway auto-detects the **Dockerfile** (ffmpeg is installed in the image).
4. Add a variable: **`GROQ_API_KEY`** = your Groq key.
5. Deploy. Open the generated URL.

### ⚠️ Important note about cloud hosting
Instagram, TikTok, and Facebook often **block datacenter IPs** and require a login,
so they may fail when the server runs in the cloud. **YouTube links work most reliably**
from a hosted server. Running locally (your home IP) works for more platforms.

---

## 🧱 Tech
- **Backend:** Flask + gunicorn, serves the frontend and `/transcribe`
- **Audio:** yt-dlp + ffmpeg
- **STT:** Groq Whisper (`whisper-large-v3`, OpenAI-compatible API)
- **Frontend:** single-file `index.html` (no build step)

---

## 📋 Endpoints
- `GET /` — the web app
- `GET /health` — `{ status, server_key }`
- `POST /transcribe` — body `{ "url": "...", "groq_key": "gsk_..." (optional) }`

---

Only **public** content can be transcribed. This tool is for personal/educational use —
respect each platform's Terms of Service and creators' rights.
