FROM python:3.11-slim

WORKDIR /app

# Install curl (needed for our entrypoint.sh healthchecks to wait for Ollama)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies with pip.
# Using psycopg2-binary means we don't need to install heavy GCC/C++ build tools.
# --no-cache-dir keeps the image small by removing leftover downloaded archives.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
