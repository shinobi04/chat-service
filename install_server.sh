#!/bin/bash
set -e

# Must run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. sudo bash install_server.sh)"
  exit 1
fi

echo "🚀 Starting automated server setup..."

# 1. Firewall
echo "🛡️ Configuring Firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
echo "y" | ufw enable

# 2. Docker & Compose
echo "🐳 Installing Docker & Docker Compose..."
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 3. NVIDIA Container Toolkit
echo "🖥️ Installing NVIDIA Container Toolkit..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update
apt-get install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

# 4. NGINX & Certbot
echo "🌐 Installing NGINX and Certbot..."
apt-get install -y nginx certbot python3-certbot-nginx

# Configure NGINX Reverse Proxy
echo "⚙️ Configuring NGINX for FastAPI..."
cat > /etc/nginx/sites-available/default << 'EOF'
server {
    listen 80;
    server_name _; # Accepts any domain/IP hitting this server

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

systemctl restart nginx

echo "======================================================================"
echo "✅ INITIAL SERVER INFRASTRUCTURE DEPLOYED SUCCESSFULLY"
echo "======================================================================"
echo "NVIDIA Drivers, Docker, Docker Compose, and NGINX are now installed."
echo ""
echo "Next Steps to deploy the actual app:"
echo "1. Clone your repo: git clone https://github.com/your-username/chat-service.git"
echo "2. cd chat-service"
echo "3. cp .env.example .env (and configure it)"
echo "4. docker compose up -d"
echo "5. (Optional) Point your domain's A-Record to this server's IP, then run:"
echo "   sudo certbot --nginx -d api.yourdomain.com"
echo "======================================================================"
