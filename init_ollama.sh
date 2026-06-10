#!/bin/bash

# Start ollama serve in the background
ollama serve &

# Wait for the server to be ready
echo "Waiting for Ollama to start..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

echo "Ollama is up. Pulling gemma3:1b model..."
# Pull the model
ollama pull gemma3:1b
echo "Model pulled successfully."

# Keep the container running
wait
