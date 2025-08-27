FROM python:3.10-slim

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2

# System dependencies untuk mysqlclient, opencv, mediapipe, tensorflow, sounddevice
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libportaudio2 \
    ffmpeg \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python deps (pakai requirements kamu apa adanya)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source
COPY . .

EXPOSE 5000

# Jalankan via gunicorn (Flask app ada di app.py -> objek 'app')
CMD ["sh", "-c", "gunicorn app:app -b 0.0.0.0:5000 --workers 2 --threads 4 --timeout 180"]
