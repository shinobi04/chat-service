# System Architecture

## 1. System Overview
The Chat Service is a backend application designed to handle AI-powered chat interactions. It leverages FastAPI for the web layer, PostgreSQL (hosted on NeonDB) for persistent storage, and an Ollama container running the `gemma3:1b` model for local inference. The entire system is containerized and orchestrated via Docker Compose for a seamless, "one-click deployable" experience.

## 2. Core Components

### 2.1 FastAPI Backend (App Service)
- **Role:** Acts as the primary interface for clients. Handles routing, session management, database interactions, and proxies inference requests to the Ollama service.
- **Key Libraries:** `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `ollama` (Python client).
- **Execution Environment:** Runs inside a Conda environment within a Docker container to ensure consistent Python and system dependency management.

### 2.2 Relational Database (NeonDB)
- **Role:** Serves as the source of truth for session and conversation history. 
- **Setup:** Hosted remotely on NeonDB. The application communicates with it via SQLAlchemy ORM.
- **Migrations:** Managed through Alembic to allow seamless and version-controlled schema updates.

### 2.3 AI Inference Engine (Ollama Service)
- **Role:** Handles all Natural Language Processing (NLP) and multimodal image processing tasks locally.
- **Model:** `gemma3:1b`.
- **Initialization:** A custom startup script (`init_ollama.sh`) guarantees that the `gemma3:1b` model is pulled and loaded before the FastAPI backend starts accepting traffic.

## 3. Data Flow & Request Lifecycle

### 3.1 Session Initialization
1. Client sends a request to `POST /sessions`.
2. Backend generates a unique UUID for the new session.
3. Backend creates a JSON Web Token (JWT) containing this UUID and signs it using a secret key.
4. Backend returns the JWT to the client. No database lookup or insertion occurs, making this step zero-latency.

### 3.2 Chat Interaction
1. Client sends `POST /chat` containing the JWT in the `Authorization` header, along with the user's message (text and/or image).
2. **Session Validation:** The backend decodes and cryptographically verifies the JWT to extract the `session_id`.
3. **Conversation Lookup:** The backend retrieves the active conversation for the given `session_id`. If one does not exist, a new `Conversation` record is instantiated.
3. **Save User Message:** The user's raw prompt is saved to the `Messages` table.
4. **Inference Call:** The backend formats the conversation history (system prompts, previous turns) and streams it to the Ollama container via HTTP API.
5. **Save AI Response:** Once Ollama generates the complete response, the backend saves the AI's generated message to the `Messages` table.
6. Backend returns the AI's response back to the client.

## 4. Database Schema Details

The system uses a normalized relational schema built for chat persistence:
- **Conversations:** 
  - `id` (UUID/Integer, Primary Key)
  - `session_id` (String extracted from the validated JWT)
  - `title` (String, auto-generated based on the first message)
  - `created_at` (Timestamp)
- **Messages:** 
  - `id` (UUID/Integer, Primary Key)
  - `conversation_id` (Foreign Key referencing Conversations.id)
  - `role` (Enum: 'user' or 'assistant')
  - `content` (Text)
  - `image_path` (String, nullable)
  - `created_at` (Timestamp)

## 5. Container & Networking Architecture

The architecture relies on a multi-container Docker Compose setup for isolation:
- **Networking:** The `app` service communicates with the `ollama` service over a shared internal Docker network using `http://ollama:11434`.
- **Volumes:** The `ollama` container maps a persistent Docker volume (`ollama_data`) to its internal `/root/.ollama` directory. This ensures that the parameter weights for Gemma 3 are downloaded only once and persist safely across container restarts.

## 6. Configuration Management (`.env`)

To securely manage environment variables, the application uses `pydantic-settings`. 
- A local `.env` file (which is ignored by Git) stores sensitive keys and URLs.
- On startup, `pydantic` automatically parses the `.env` file, validates the data types (e.g., ensuring `DATABASE_URL` is a valid Postgres string), and exposes them as strongly-typed Python objects to the rest of the application.

**Required Environment Variables:**
- `DATABASE_URL`: Connection string for the NeonDB Postgres instance.
- `OLLAMA_BASE_URL`: URL to the Ollama container (e.g., `http://ollama:11434`).
- `JWT_SECRET_KEY`: A high-entropy, randomly generated string used strictly by the backend to sign and verify session JWTs.

## 7. Design Principles
- **Stateless & Zero-Latency Sessions:** By adopting JWTs instead of a database-backed Sessions table, the API guarantees zero database latency for session validation.
- **Stateless Backend:** The FastAPI application itself is completely stateless, relying entirely on NeonDB for persisting history and Ollama for compute. This allows the backend to be horizontally scaled across multiple instances if needed.
- **Data Privacy & Cost Efficiency:** By isolating the model in an Ollama container, the architecture removes external rate limits, eliminates token-based pricing, and keeps user prompts within the local network.
