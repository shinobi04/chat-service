# Chat App Backend Plan

## 1. Architecture & Tech Stack

- **Web Framework:** FastAPI (Python) - High performance, async support, and auto-generated API docs.
- **Database:** PostgreSQL (remote via NeonDB) - Serverless Postgres.
- **ORM:** SQLAlchemy (or SQLModel) along with Alembic for migrations.
- **AI Model:** Gemma 3 1B (`gemma3:1b`) - Local inference via **Ollama** for both image and text processing.
- **Environment Management:** Conda - To manage Python dependencies.
- **Containerization:** Docker & Docker Compose - For reproducible, one-click deployments.

## 2. Database Schema (NeonDB)

- **Conversations**: `id`, `session_id` (String extracted from JWT), `title`, `created_at`
- **Messages**: `id`, `conversation_id`, `role` (user/assistant), `content` (text), `image_path` (optional), `created_at`

## 3. API Endpoints

- `GET /health`: Health check (API, DB, and Ollama status).
- `POST /sessions`: Stateless endpoint. Generates a unique UUID and returns it encoded inside a signed JWT. No database interaction.
- `POST /chat`: Main endpoint. Requires the JWT in the `Authorization` header. Accepts text and/or an image, processes it via the Ollama Gemma model, saves the interaction to the database, and returns the response. Creates a new conversation if one doesn't exist.
- `GET /conversations`: Fetch all conversation threads for the session identified by the JWT.
- `GET /conversations/{conversation_id}/messages`: Fetch the history of a specific conversation.

## 4. "One-Click Deployable" Docker Setup

To make the application truly one-click deployable and resilient, the Docker setup will use Docker Compose with two main services: the FastAPI backend and the Ollama server.

### Components:

1. **`environment.yml`**: Defines the Conda environment (FastAPI, SQLAlchemy, psycopg2, `PyJWT`, `ollama` python client, etc.).
2. **`init_ollama.sh`**: A script that runs in the Ollama container to ensure `gemma3:1b` is downloaded before accepting requests.
3. **`entrypoint.sh`**: The startup process for the backend. It will:
   - Wait for the Ollama service to be ready and model to be pulled.
   - Run the database migrations (Alembic).
   - Start the FastAPI application via `uvicorn`.
4. **`Dockerfile`**: Uses `continuumio/miniconda3` as a base, sets up the conda env, and defines `entrypoint.sh` as the entrypoint.
5. **`docker-compose.yml`**: 
   - **Service `app`**: The FastAPI backend.
   - **Service `ollama`**: The official Ollama image, with a volume mapped for model weights so they aren't re-downloaded. It will execute `init_ollama.sh` to pull the model if missing.

## 5. Environment Variables Needed (`.env`)

- `DATABASE_URL`: The NeonDB connection string.
- `OLLAMA_BASE_URL`: URL to the Ollama service (e.g., `http://ollama:11434`).
- `JWT_SECRET_KEY`: Secret string used to sign the session JWTs.

## 6. Execution Steps

1. **Project Setup**: Create the folder structure (routers, models, schemas, services).
2. **Conda & Docker Setup**: Write `environment.yml`, `Dockerfile`, `docker-compose.yml`, `init_ollama.sh`, and `entrypoint.sh`.
3. **Database Setup**: Configure SQLAlchemy, Alembic, and the NeonDB connection.
4. **Model Integration**: Create the inference service using the `ollama` Python client.
5. **API Development**: Wire the endpoints to the DB and Model service.
6. **Testing**: Build the Docker Compose setup and verify the model pull and chat logic.
