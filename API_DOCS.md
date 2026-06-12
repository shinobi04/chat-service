# Chat API Documentation

Base URL: `http://localhost:8000` (or your E2E Networks IP)

This is a **backend-to-backend** service. Only whitelisted server IPs can access the API (configured via `ALLOWED_IPS`). It uses **Zero-Latency Sessions** — call `POST /sessions` once from your backend to receive a signed JWT, then include it in the `Authorization` header for all subsequent requests.

All authenticated endpoints require the header:
```
Authorization: Bearer <your_access_token>
```

---

## 1. Health Check
Returns the service status. Use this to verify the API is running.

- **Endpoint:** `GET /health`
- **Auth Required:** No
- **Rate Limit:** None

**Response:** `200 OK`
```json
{
  "status": "ok",
  "service": "chat-backend"
}
```

---

## 2. Create Session
Generates a new zero-latency session and returns a signed JWT.

- **Endpoint:** `POST /sessions`
- **Auth Required:** No
- **Rate Limit:** 10 requests/minute per IP

**Response:** `200 OK`
```json
{
  "session_id": "c9284f3a-2384-4e9b-a1d2-7f8e6d5c4b3a",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 3. Standard Text Chat (Streaming)
Streams an AI response using the fast `gemma3:1b` model.

- **Endpoint:** `POST /chat`
- **Auth Required:** Yes (Bearer Token)
- **Rate Limit:** 20 requests/minute per IP
- **Headers:**
  - `Authorization: Bearer <your_access_token>`
  - `Content-Type: multipart/form-data`
- **Query Parameters:**
  - `conversation_id` (UUID, optional): Provide this to continue an existing conversation. Omit to start a new one.
- **Form Data Body:**
  - `content` (string, required): The user's text message.
  - `system_prompt` (string, optional): System prompt to set the AI persona for this request.

**Response:** `200 OK` (Content-Type: `text/event-stream`)

The stream yields the conversation metadata first, followed by text chunks. Your calling service should read the SSE `data:` blocks:
```text
data: {"conversation_id": "123e4567-e89b-12d3-a456-426614174000", "title": "Your first message"}

data: {"chunk": "Hello"}

data: {"chunk": " there"}

data: {"chunk": "!"}
```

**Error during stream:**
```text
data: {"error": "An internal error occurred."}
```

---

## 4. Heavy Vision Chat (Streaming)
Streams an AI response using the larger `gemma4:26b` model. Use this endpoint when an image needs to be analyzed.

- **Endpoint:** `POST /chat/gemma4`
- **Auth Required:** Yes (Bearer Token)
- **Rate Limit:** 5 requests/minute per IP
- **Headers:**
  - `Authorization: Bearer <your_access_token>`
  - `Content-Type: multipart/form-data`
- **Query Parameters:**
  - `conversation_id` (UUID, optional): Provide this to continue an existing conversation.
- **Form Data Body:**
  - `content` (string, required): The user's text message.
  - `system_prompt` (string, optional): System prompt to set the AI persona for this request.
  - `image` (file, optional): An image file to be analyzed by the vision model.

**Response:** `200 OK` (Content-Type: `text/event-stream`)

*(Follows the exact same streaming format as standard chat above.)*

---

## 5. Get All Conversations
Retrieves a list of all conversation threads for the authenticated session, ordered by most recent first.

- **Endpoint:** `GET /conversations`
- **Auth Required:** Yes (Bearer Token)
- **Rate Limit:** 30 requests/minute per IP

**Response:** `200 OK`
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "session_id": "c9284f3a-2384-4e9b-a1d2-7f8e6d5c4b3a",
    "title": "Hi, who are you?",
    "created_at": "2026-06-10T12:00:00Z"
  }
]
```

---

## 6. Get Conversation History
Retrieves the full message history for a specific conversation.

- **Endpoint:** `GET /conversations/{conversation_id}`
- **Auth Required:** Yes (Bearer Token)
- **Rate Limit:** 30 requests/minute per IP
- **Path Parameters:**
  - `conversation_id` (UUID, required): The ID of the conversation to load.

**Response:** `200 OK`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "session_id": "c9284f3a-2384-4e9b-a1d2-7f8e6d5c4b3a",
  "title": "Hi, who are you?",
  "created_at": "2026-06-10T12:00:00Z",
  "messages": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
      "role": "user",
      "content": "Hi, who are you?",
      "image_path": null,
      "created_at": "2026-06-10T12:00:01Z"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
      "role": "assistant",
      "content": "I am a helpful AI assistant. How can I help you today?",
      "image_path": null,
      "created_at": "2026-06-10T12:00:05Z"
    }
  ]
}
```

---

## Error Responses

All endpoints return standard HTTP error codes with a JSON body:

| Status | Meaning | Example |
|--------|---------|---------|
| `401` | Missing or invalid JWT | `{"detail": "Invalid token"}` |
| `403` | IP not whitelisted | `{"detail": "Forbidden: your IP is not whitelisted."}` |
| `404` | Conversation not found or not owned by session | `{"detail": "Conversation not found"}` |
| `429` | Rate limit exceeded | `{"error": "Rate limit exceeded: 20 per 1 minute"}` |
| `500` | Internal server error | `{"detail": "Internal Server Error"}` |

---

### System Prompt

The AI model persona is controlled per-request by the calling backend via the `system_prompt` form field on both `/chat` and `/chat/gemma4`. If omitted, no system prompt is prepended and the model uses its default behavior.

### IP Whitelisting

Since this is a backend-to-backend service, access is restricted by IP. Configure the `ALLOWED_IPS` environment variable with a comma-separated list of trusted server IPs:

```env
ALLOWED_IPS=192.168.65.1,172.18.0.4,203.0.113.10,10.0.0.5
```

- **Empty value (default):** All IPs are allowed (development mode).
- **When set:** Only listed IPs can access the API. All others receive `403 Forbidden`.
- **Exempt paths:** `/health`, `/docs`, `/openapi.json`, and `/redoc` are always accessible regardless of whitelist (for load balancers and monitoring).
