"""
ReelScript Backend Server
─────────────────────────
Local:  python server.py   ->  open http://localhost:5050
Cloud:  runs under gunicorn on Railway (see Dockerfile)

Transcription uses Groq's free Whisper API (OpenAI-compatible).
The Groq key is read from the GROQ_API_KEY environment variable so
end users never need their own key. A key sent in the request body
is used as a fallback (handy for local testing).
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import openai
import os
import glob
import shutil
import tempfile
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
CORS(app)

# Server-side Groq key (set this as a secret on Railway: GROQ_API_KEY)
SERVER_GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()


def find_ffmpeg():
    """Locate ffmpeg even if it isn't on PATH (e.g. winget install on Windows)."""
    on_path = shutil.which("ffmpeg")
    if on_path:
        return os.path.dirname(on_path)
    pattern = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "WinGet", "Packages",
        "Gyan.FFmpeg*", "**", "bin", "ffmpeg.exe",
    )
    matches = glob.glob(pattern, recursive=True)
    return os.path.dirname(matches[0]) if matches else None


FFMPEG_DIR = find_ffmpeg()


# ─────────────────────────────────────────
#  FRONTEND
# ─────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


# ─────────────────────────────────────────
#  HEALTH CHECK
# ─────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "message": "ReelScript server is live",
        "server_key": bool(SERVER_GROQ_KEY),
    })


# ─────────────────────────────────────────
#  TRANSCRIBE ENDPOINT
#  POST /transcribe   Body: { "url": "...", "groq_key": "gsk_..." (optional) }
# ─────────────────────────────────────────
@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    api_key = (data.get("groq_key") or data.get("openai_key") or "").strip() or SERVER_GROQ_KEY
    # Ignore empty/placeholder keys — a real Groq key starts with "gsk_"
    if not api_key.startswith("gsk_"):
        api_key = ""

    if not url:
        return jsonify({"error": "No URL provided"}), 400
    if not url.startswith("http"):
        return jsonify({"error": "Please enter a valid URL"}), 400
    if not api_key:
        return jsonify({"error": "Server has no valid Groq API key. Set GROQ_API_KEY to a real gsk_ key."}), 503

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.mp3")

            # ── STEP 1: Download audio ──
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "96",
                }],
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                # YouTube now needs a JS runtime; allow deno or node
                "js_runtimes": {"deno": None, "node": None},
            }
            if FFMPEG_DIR:
                ydl_opts["ffmpeg_location"] = FFMPEG_DIR

            # Optional: pass cookies for sites that require login / bot-checks.
            #   YTDLP_COOKIES_FROM_BROWSER = chrome | edge | firefox
            #   YTDLP_COOKIES_FILE         = /path/to/cookies.txt
            cb = os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "").strip()
            if cb:
                ydl_opts["cookiesfrombrowser"] = (cb,)
            cf = os.environ.get("YTDLP_COOKIES_FILE", "").strip()
            if cf and os.path.exists(cf):
                ydl_opts["cookiefile"] = cf

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Untitled")
                duration = info.get("duration", 0)
                for f in os.listdir(tmpdir):
                    if f.endswith(".mp3"):
                        audio_path = os.path.join(tmpdir, f)
                        break

            # ── STEP 2: Transcribe with Groq Whisper ──
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            with open(audio_path, "rb") as audio_file:
                result = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    language="en",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            # ── STEP 3: Format transcript ──
            lines = []
            segments = getattr(result, "segments", None)
            if segments:
                for seg in segments:
                    s = seg["start"] if isinstance(seg, dict) else seg.start
                    txt = seg["text"] if isinstance(seg, dict) else seg.text
                    s = int(s)
                    lines.append(f"[{s // 60}:{s % 60:02d}] {txt.strip()}")
                transcript = "\n\n".join(lines)
            else:
                transcript = result.text

            return jsonify({
                "success": True,
                "transcript": transcript,
                "title": title,
                "duration": duration,
                "words": len(transcript.split()),
                "platform": detect_platform(url),
            })

    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        low = err.lower()
        if "private" in low:
            msg = "This reel is private. Only public reels can be transcribed."
        elif "login" in low or "rate-limit" in low or "cookies" in low or "sign in" in low:
            msg = "This platform is blocking the server (login required). Public YouTube links work most reliably from the cloud."
        elif "unavailable" in low or "removed" in low or "deleted" in low:
            msg = "Video is unavailable, removed, or deleted."
        else:
            msg = f"Could not download video: {err[:200]}"
        return jsonify({"error": msg}), 400

    except openai.AuthenticationError:
        return jsonify({"error": "Invalid Groq API key. Check it at console.groq.com/keys"}), 401
    except openai.RateLimitError:
        return jsonify({"error": "Groq rate limit hit. Wait a moment and try again."}), 429
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"Unexpected error: {str(e)[:300]}"}), 500


def detect_platform(url):
    if "instagram.com" in url: return "Instagram"
    if "tiktok.com" in url: return "TikTok"
    if "youtube.com" in url or "youtu.be" in url: return "YouTube"
    if "twitter.com" in url or "x.com" in url: return "Twitter/X"
    if "facebook.com" in url: return "Facebook"
    return "Video"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print("\n" + "=" * 50)
    print("  ReelScript Server Running")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    print("\n  Open that URL in your browser.\n")
    app.run(host="0.0.0.0", port=port, debug=False)
