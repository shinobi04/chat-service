#!/bin/bash
# ==============================================================================
# File:        setup_e2e_vm.sh
# Description: Production-Hardened Systemd Service Generator for Docker Apps
# Automation:  Runs ONCE to bind Docker Compose cycles to server power states.
# Compatibility: Ubuntu 20.04+, Debian 11+, RHEL/Rocky Linux 9+
# ==============================================================================

# Halt script on any unforeseen multi-pipeline structural error
set -eo pipefail

# --- PHASE 1: PRIVILEGE VALIDATION ---
if [ "$EUID" -ne 0 ]; then
  echo "======================================================================"
  echo "❌ CRITICAL ERROR: Execution Perms Denied."
  echo "======================================================================"
  echo "This configuration wrapper writes directly to systemd unit runlevels."
  echo "Please elevate privileges by running: sudo bash $0"
  echo ""
  exit 1
fi

echo "🚀 Starting Production Environment Provisioning..."

# --- PHASE 2: PATHWAY DISCOVERY ENGINE ---
echo "🔍 Searching for system container engine paths..."

# Identify where Docker or historical Docker Compose binaries reside across standard bin rings
DOCKER_BIN=$(which docker 2>/dev/null || true)
DOCKER_COMPOSE_BIN=$(which docker-compose 2>/dev/null || true)

if [ -n "$DOCKER_BIN" ] && "$DOCKER_BIN" compose version >/dev/null 2>&1; then
  # Modern Docker Compose V2 Plugin Setup detected
  START_CMD="$DOCKER_BIN compose up -d"
  STOP_CMD="$DOCKER_BIN compose down"
  echo " -> Found Docker Compose V2 Integration: $DOCKER_BIN compose"
elif [ -n "$DOCKER_COMPOSE_BIN" ]; then
  # Historical Legacy V1 standalone binary detected
  START_CMD="$DOCKER_COMPOSE_BIN up -d"
  STOP_CMD="$DOCKER_COMPOSE_BIN down"
  echo " -> Found Standalone Docker Compose V1 Binary: $DOCKER_COMPOSE_BIN"
else
  echo "======================================================================"
  echo "❌ CRITICAL ERROR: Missing Dependency Layer."
  echo "======================================================================"
  echo "Could not resolve a valid Docker installation or Docker Compose plugin."
  echo "Please execute your platform's Docker engine setup sequence before running this wrapper."
  echo ""
  exit 1
fi

# --- PHASE 3: IMMUTABLE WORKING DIRECTORY DETERMINATION ---
# Resolves the absolute directory path where this specific execution script is stored, 
# preventing context pollution from arbitrary terminal locations.
REAL_SCRIPT_PATH=$(readlink -f "$0")
PROJECT_DIR=$(dirname "$REAL_SCRIPT_PATH")

if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
  echo "⚠️  WARNING: No 'docker-compose.yml' discovered in target directory:"
  echo "    [$PROJECT_DIR]"
  echo "    Ensure your project file configuration is deployed here before initiating the service."
fi

# --- PHASE 4: SYSTEMD GENERATION MATRIX ---
echo "🛠️  Writing systemd unit definitions into /etc/systemd/system/chat-service.service..."

cat <<EOF > /etc/systemd/system/chat-service.service
[Unit]
Description=Automated Cloud Chat Service API & Ollama Core Supervisor
Requires=docker.service
After=docker.service
Documentation=[https://docs.docker.com](https://docs.docker.com)

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=$START_CMD
ExecStop=$STOP_CMD
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# --- PHASE 5: RUNLEVEL REGISTRATION ---
echo "🔄 Reloading systemd manager configurations..."
systemctl daemon-reload

echo "⚙️  Enabling chat-service.service for system boot targets..."
systemctl enable chat-service.service

echo "======================================================================"
echo "✅ INFRASTRUCTURE DEPLOYMENT COMPLETION SUMMARY"
echo "======================================================================"
echo "Target Folder Configured : $PROJECT_DIR"
echo "Resolved Engine Pipeline : $START_CMD"
echo "System Unit Profile Path : /etc/systemd/system/chat-service.service"
echo "======================================================================"
echo "System initialized successfully. Cloud control dashboard triggers are now synced."
echo "Whenever the host VM reboots, your AI service pipeline will automatically run."
echo "======================================================================"
