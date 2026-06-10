# Chat API Documentation

Base URL: `http://localhost:8000` (or your E2E Networks IP)

This API uses **Zero-Latency Sessions**. You do not need to build a complex login system. Instead, call `/sessions` on the first app launch to receive a permanent guest token.

---

## 1. Create Session
Generates a new zero-latency session for a user.

- **Endpoint:** `POST /sessions`
- **Auth Required:** No
- **Headers:** None
- **Body:** None

**Response:** `200 OK`
```json
{
  "session_id": "c9284j-23849...",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 2. Standard Text Chat (Streaming)
Streams an AI response using the highly-optimized `gemma3:1b` model.

- **Endpoint:** `POST /chat`
- **Auth Required:** Yes (Bearer Token)
- **Headers:** 
  - `Authorization: Bearer <your_access_token>`
  - `Content-Type: multipart/form-data`
- **Query Parameters:**
  - `conversation_id` (UUID, optional): Provide this to continue an existing conversation. Leave blank to start a new one.
- **Form Data Body:**
  - `content` (String, required): The user's text message.

**Response:** `200 OK` (Content-Type: `text/event-stream`)
The stream yields the conversation metadata first, followed by text chunks. Your Flutter SSE package must read the `data: ` blocks:
```text
data: {"conversation_id": "uuid-here", "title": "Your first message"}

data: {"chunk": "Hello"}

data: {"chunk": " there"}

data: {"chunk": "!"}
```

---

## 3. Heavy Vision Chat (Streaming)
Streams an AI response using the massive `gemma4:26b` model. Use this when the user uploads an image.

- **Endpoint:** `POST /chat/gemma4`
- **Auth Required:** Yes (Bearer Token)
- **Headers:** 
  - `Authorization: Bearer <your_access_token>`
  - `Content-Type: multipart/form-data`
- **Query Parameters:**
  - `conversation_id` (UUID, optional): Provide this to continue an existing conversation.
- **Form Data Body:**
  - `content` (String, required): The user's text message.
  - `image` (File, optional): An image file to be analyzed by the vision model.

**Response:** `200 OK` (Content-Type: `text/event-stream`)
*(Follows the exact same streaming format as standard chat)*

---

## 4. Get All Conversations
Retrieves a list of all chat history threads for the current user.

- **Endpoint:** `GET /conversations`
- **Auth Required:** Yes (Bearer Token)
- **Headers:** 
  - `Authorization: Bearer <your_access_token>`

**Response:** `200 OK`
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "session_id": "c9284j-23849...",
    "title": "Hi, who are you?",
    "created_at": "2024-06-10T12:00:00Z"
  }
]
```

---

## 5. Get Specific Conversation History
Retrieves the full message history for a specific conversation.

- **Endpoint:** `GET /conversations/{conversation_id}`
- **Auth Required:** Yes (Bearer Token)
- **Headers:** 
  - `Authorization: Bearer <your_access_token>`
- **Path Parameters:**
  - `conversation_id` (UUID, required): The ID of the conversation to load.

**Response:** `200 OK`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "session_id": "c9284j-23849...",
  "title": "Hi, who are you?",
  "created_at": "2024-06-10T12:00:00Z",
  "messages": [
    {
      "id": "...",
      "role": "user",
      "content": "Hi, who are you?",
      "created_at": "2024-06-10T12:00:01Z"
    },
    {
      "id": "...",
      "role": "assistant",
      "content": "I am Gemma, an AI assistant.",
      "created_at": "2024-06-10T12:00:05Z"
    }
  ]
}
```
