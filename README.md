# Chat Backend 🚀

A high-performance, streaming chat backend built specifically to power a mobile Flutter application. It runs completely locally using Ollama, features 0ms latency caching, and is designed to run efficiently on an E2E Networks NVIDIA L4 Instance.

## 🌟 Core Architecture

- **FastAPI**: The asynchronous web framework powering the backend.
- **NeonDB**: Serverless Postgres used for permanent conversation history storage.
- **LRU Cache & Background Tasks**: The system immediately caches chats in RAM for **0ms latency** on subsequent messages, while silently saving to NeonDB in the background.
- **SSE Streaming**: Sends AI text generation back to the Flutter app byte-by-byte (`text/event-stream`) for a seamless typing UI.
- **Dual AI Models**:
  - `gemma3:1b` for fast, standard text conversations.
  - `gemma4:26b` for heavy, image-vision processing.

---

## ☁️ E2E Networks Deployment Guide (For Developers)

This API is designed to be hosted on an E2E Networks NVIDIA L4 Instance. To save costs, it has an automated setup script so non-technical operators can turn it on/off directly from the dashboard without touching the terminal.

### First-Time Setup Instructions

1. **Spin up the VM & Connect:**
   Deploy an Ubuntu NVIDIA L4 VM on E2E Networks and SSH into it:

   ```bash
   ssh root@YOUR_E2E_IP_ADDRESS
   ```

2. **Install Dependencies:**
   Run the following commands to install Docker, Docker Compose, and the **NVIDIA Container Toolkit** so Docker can access the L4 GPU:

   ```bash
   # Install Docker & Docker Compose
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose

   # Install NVIDIA Container Toolkit
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

3. **Clone & Configure:**

   ```bash
   git clone https://github.com/your-username/chat-service.git
   cd chat-service
   cp .env.example .env
   nano .env # Add your NeonDB URL and JWT Secret
   ```

4. **Initial Download & Test:**
   _Crucial: Do this BEFORE running the auto-start script._
   Force Docker to pull the 15GB `gemma4:26b` model. Because we use a persistent volume, it will save directly to the VM's hard drive and never need to be downloaded again.

   ```bash
   PULL_HEAVY_MODEL=true docker-compose up -d
   ```

   _Wait for the download to finish, test the API via Postman or Flutter to ensure it works, and then shut it down with `docker-compose down`._

5. **Lock in the Auto-Start Script:**
   Now that the environment is fully built, install the systemd background service:
   ```bash
   sudo bash setup_e2e_vm.sh
   ```

**Done!** From now on, your non-technical team members can simply click **Power On** and **Power Off** on the E2E Dashboard. The API and Docker containers will automatically start and stop with the VM.

---

## 📡 Flutter API Cheat Sheet

### 1. Authentication

- **`POST /sessions`**
  - **Auth:** None
  - **Returns:** `{ "session_id": "...", "access_token": "..." }`
  - **Purpose:** Call this silently on app launch to create a zero-latency guest session. Store the `access_token` securely.

### 2. Chatting (Streaming)

- **`POST /chat`**
  - **Auth:** Bearer Token (access_token)
  - **Body (Multipart Form-Data):**
    - `content` (string, required)
    - `image` (file, optional)
  - **Query Parameter:** `?conversation_id=UUID` (optional, pass this to continue an old chat)
  - **Returns:** `text/event-stream`
  - **Purpose:** Standard, lightning-fast text chat using `gemma3:1b`.

- **`POST /chat/gemma4`**
  - **Auth:** Bearer Token
  - **Body & Query:** Same as above.
  - **Returns:** `text/event-stream`
  - **Purpose:** The heavy-duty endpoint for the massive `gemma4:26b` vision model (use when the user attaches an image).

_Note: The very first chunk of the stream will yield metadata `{"conversation_id": "...", "title": "..."}` so your Flutter app can instantly grab the ID._

### 3. History & Memory

- **`GET /conversations`**
  - **Auth:** Bearer Token
  - **Returns:** JSON array of `{ "id": "...", "title": "...", "created_at": "..." }`
  - **Purpose:** Populate the history `ListView` on your Flutter app's home screen.

- **`GET /conversations/{conversation_id}`**
  - **Auth:** Bearer Token
  - **Returns:** Flat JSON object containing the conversation details AND the full `messages` array nested inside it.
  - **Purpose:** Call this when a user taps an old conversation to load their chat history into the UI.
