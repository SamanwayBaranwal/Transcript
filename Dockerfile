# ReelScript — production image (Flask + ffmpeg + yt-dlp + Groq Whisper)
FROM python:3.12-slim

# ffmpeg is required by yt-dlp to extract audio
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# Long timeout: download + Whisper transcription can take a while
CMD ["sh", "-c", "gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 300"]
