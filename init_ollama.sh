#!/bin/bash

# Start ollama serve in the background
ollama serve &

# Wait for the server to be ready using the native ollama CLI instead of curl
echo "Waiting for Ollama to start..."
while ! ollama list > /dev/null 2>&1; do
    sleep 2
done

echo "Ollama is up. Pulling gemma3:1b model..."
# Pull the model
ollama pull gemma3:1b

if [ "$PULL_HEAVY_MODEL" = "true" ]; then
    echo "PULL_HEAVY_MODEL is set to true. Pulling heavy vision model gemma4:26b..."
    ollama pull gemma4:26b
fi

echo "Model pulled successfully."

# Keep the container running
wait
