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
   # Basic Firewall Hardening
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow ssh
   sudo ufw allow http
   sudo ufw allow https
   echo "y" | sudo ufw enable

   # Install Docker & Docker Compose Plugin
   sudo apt-get update
   sudo apt-get install -y docker.io docker-buildx-plugin docker-compose-plugin

   # Install NVIDIA Container Toolkit
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   
   # Configure Docker to use NVIDIA runtime
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

3. **Clone & Configure:**

   ```bash
   # Clone your repository
   git clone https://github.com/your-username/chat-service.git
   cd chat-service
   
   # Setup environment variables
   cp .env.example .env
   nano .env # Add your NeonDB URL and JWT Secret
   ```
   
   *Whenever you make code changes locally, push them to GitHub and run `git pull origin main` in this folder to deploy the updates!*

4. **Initial Download & Test:**
   _Crucial: Do this BEFORE running the auto-start script._
   Force Docker to pull the `gemma4:26b` model. Because we use a persistent volume, it will save directly to the VM's hard drive and never need to be downloaded again.

   ```bash
   PULL_HEAVY_MODEL=true docker compose up -d
   ```

   > [!TIP]
   > **Will `gemma4:26b` fit on an L4?**
   > Yes! An NVIDIA L4 GPU has 24GB of VRAM. Ollama automatically pulls the 4-bit quantized version of `gemma4:26b` (~16GB), which fits perfectly and leaves a healthy 8GB buffer for processing context windows and image embeddings.

   _Wait for the download to finish, test the API via Postman or Flutter to ensure it works, and then shut it down with `docker compose down`._

5. **Lock in the Auto-Start Script:**
   Now that the environment is fully built, install the systemd background service:
   ```bash
   sudo bash setup_e2e_vm.sh
   ```

**Done!** From now on, your non-technical team members can simply click **Power On** and **Power Off** on the E2E Dashboard. The API and Docker containers will automatically start and stop with the VM.

### 6. 🌐 Exposing a Public HTTPS URL for Production

Mobile apps (iOS/Android) strongly enforce secure `https://` connections. While your E2E VM has a public IP address, it only serves raw `http://` on port 8000. 

For a production environment, you should use one of the following methods to create a permanent, secure connection:

**Option A: NGINX + Certbot (Recommended for Public E2E IPs)**
Since E2E provides a static public IP, you can map your domain directly to it.
1. Map your domain's A-Record to the E2E Public IP.
2. Install NGINX and Certbot:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```
3. Set up a reverse proxy in `/etc/nginx/sites-available/default` that forwards port `80` to `localhost:8000`.
4. Run Certbot to generate the free SSL certificate:
   ```bash
   sudo certbot --nginx -d api.yourdomain.com
   ```

**Option B: Permanent Cloudflare Tunnel (No open ports needed)**
If you prefer not to manage NGINX or SSL certificates manually:
1. Log into your Cloudflare Dashboard and navigate to **Zero Trust > Networks > Tunnels**.
2. Create a new tunnel and follow the instructions to install the `cloudflared` connector on your VM.
3. Route a public hostname (e.g., `api.yourdomain.com`) to `http://localhost:8000`. Cloudflare will handle the SSL entirely!

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
