#!/bin/bash
# Jarvis Edge Node Setup Script
# Run on fresh Ubuntu Server 24.04 LTS

set -e

echo "=========================================="
echo "  JARVIS EDGE NODE SETUP"
echo "  StephensCode LLC - Proprietary"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run as normal user, not root${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: System Update${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "${YELLOW}Step 2: Installing Dependencies${NC}"
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    iotop \
    net-tools \
    ufw \
    fail2ban \
    unattended-upgrades

echo -e "${YELLOW}Step 3: Installing Docker${NC}"
# Remove old versions
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

echo -e "${YELLOW}Step 4: Installing Docker Compose${NC}"
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo -e "${YELLOW}Step 5: Installing WireGuard${NC}"
sudo apt install -y wireguard wireguard-tools

echo -e "${YELLOW}Step 6: Enabling IP Forwarding${NC}"
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

echo -e "${YELLOW}Step 7: Creating Jarvis Directories${NC}"
mkdir -p ~/jarvis/{web-agent,profiles,data,logs,backups}
mkdir -p ~/jarvis/data/{redis,sessions,cache}

echo -e "${YELLOW}Step 8: Configuring Firewall${NC}"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 51820/udp  # WireGuard
sudo ufw allow 3000/tcp   # Web Agent API (only if needed externally)
sudo ufw --force enable

echo -e "${YELLOW}Step 9: Configuring Fail2ban${NC}"
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

echo -e "${YELLOW}Step 10: Setting Up Auto-Updates${NC}"
sudo dpkg-reconfigure -plow unattended-upgrades

echo ""
echo -e "${GREEN}=========================================="
echo "  BASE SETUP COMPLETE"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. LOG OUT AND BACK IN (for docker group)"
echo "  2. Run: ./scripts/wireguard-setup.sh"
echo "  3. Configure port forward on router: UDP 51820"
echo "  4. Copy .env.example to .env and configure"
echo "  5. Run: docker-compose up -d"
echo ""
echo -e "${YELLOW}Your external IP: $(curl -s ifconfig.me)${NC}"
echo ""
