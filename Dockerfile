FROM python:3.11-slim

WORKDIR /app

# Install curl (healthchecks) and ffmpeg (audio decoding for faster-whisper)
RUN apt-get update && apt-get install -y --no-install-recommends curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies with pip.
# Using psycopg2-binary means we don't need to install heavy GCC/C++ build tools.
# --no-cache-dir keeps the image small by removing leftover downloaded archives.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the faster-whisper model so there's no cold-start delay at runtime.
# The model is cached into /root/.cache/huggingface/hub/
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Copy the actual application code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

