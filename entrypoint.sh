#!/bin/bash

# Wait for Ollama service to be ready
echo "Waiting for Ollama service at ${OLLAMA_BASE_URL}..."
while ! curl -s ${OLLAMA_BASE_URL}/api/tags > /dev/null; do
    sleep 2
done

echo "Checking if gemma3:1b is available..."
while true; do
  TAGS=$(curl -s ${OLLAMA_BASE_URL}/api/tags)
  if echo "$TAGS" | grep -q '"name":"gemma3:1b"'; then
    echo "gemma3:1b model is ready!"
    break
  else
    echo "Waiting for model to be pulled by Ollama service..."
    sleep 5
  fi
done

# Run alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Start FastAPI server
echo "Starting FastAPI app..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
