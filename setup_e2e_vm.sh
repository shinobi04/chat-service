#!/bin/bash
# Run this file ONCE on the E2E Networks server using: sudo bash setup_e2e_vm.sh

# Get the absolute path to where docker-compose.yml lives
PROJECT_DIR=$(pwd)

echo "🛠️ Creating Systemd Auto-Start Service..."
cat <<EOF > /etc/systemd/system/chat-service.service
[Unit]
Description=Chat Service API and Ollama Container
Requires=docker.service
After=docker.service

[Service]
Restart=always
WorkingDirectory=$PROJECT_DIR
# Start Docker Compose when the VM boots
ExecStart=/usr/local/bin/docker-compose up
# Stop Docker Compose cleanly when the VM shuts down
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

# Enable the service so it runs on VM Boot
systemctl daemon-reload
systemctl enable chat-service.service

echo "✅ E2E Networks VM setup complete!"
echo "Whenever the operator clicks 'Start' on the E2E Dashboard, the service will boot up entirely on its own."
echo "When they are done for the day, they can just click the Power Off button on the dashboard to safely shut it down!"
