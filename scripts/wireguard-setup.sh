#!/bin/bash
# WireGuard Exit Node Setup for Jarvis Edge Node
# This allows Jarvis Core (wherever it runs) to exit traffic through home residential IP

set -e

echo "=========================================="
echo "  WIREGUARD EXIT NODE SETUP"
echo "=========================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
WG_INTERFACE="wg0"
WG_PORT="51820"
WG_NETWORK="10.10.10.0/24"
SERVER_WG_IP="10.10.10.1"
CLIENT_WG_IP="10.10.10.2"

# Detect primary network interface
PRIMARY_IFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
echo -e "${CYAN}Detected primary interface: ${PRIMARY_IFACE}${NC}"

# Generate keys
echo -e "${YELLOW}Generating WireGuard keys...${NC}"
WG_DIR="/etc/wireguard"
sudo mkdir -p $WG_DIR
cd $WG_DIR

# Server keys
sudo wg genkey | sudo tee server_private.key | sudo wg pubkey | sudo tee server_public.key > /dev/null
sudo chmod 600 server_private.key

# Client keys (for Jarvis Core)
sudo wg genkey | sudo tee client_private.key | sudo wg pubkey | sudo tee client_public.key > /dev/null
sudo chmod 600 client_private.key

SERVER_PRIVATE=$(sudo cat server_private.key)
SERVER_PUBLIC=$(sudo cat server_public.key)
CLIENT_PRIVATE=$(sudo cat client_private.key)
CLIENT_PUBLIC=$(sudo cat client_public.key)

echo -e "${YELLOW}Creating server configuration...${NC}"

# Create server config
sudo tee /etc/wireguard/${WG_INTERFACE}.conf > /dev/null << EOF
# Jarvis Edge Node - WireGuard Exit Configuration
# Generated: $(date)

[Interface]
Address = ${SERVER_WG_IP}/24
ListenPort = ${WG_PORT}
PrivateKey = ${SERVER_PRIVATE}

# NAT masquerade - traffic exits through home IP
PostUp = iptables -t nat -A POSTROUTING -s ${WG_NETWORK} -o ${PRIMARY_IFACE} -j MASQUERADE
PostUp = iptables -A FORWARD -i ${WG_INTERFACE} -j ACCEPT
PostUp = iptables -A FORWARD -o ${WG_INTERFACE} -j ACCEPT

PostDown = iptables -t nat -D POSTROUTING -s ${WG_NETWORK} -o ${PRIMARY_IFACE} -j MASQUERADE
PostDown = iptables -D FORWARD -i ${WG_INTERFACE} -j ACCEPT
PostDown = iptables -D FORWARD -o ${WG_INTERFACE} -j ACCEPT

[Peer]
# Jarvis Core Server
PublicKey = ${CLIENT_PUBLIC}
AllowedIPs = ${CLIENT_WG_IP}/32
EOF

sudo chmod 600 /etc/wireguard/${WG_INTERFACE}.conf

# Enable and start WireGuard
echo -e "${YELLOW}Enabling WireGuard service...${NC}"
sudo systemctl enable wg-quick@${WG_INTERFACE}
sudo systemctl start wg-quick@${WG_INTERFACE}

# Get external IP
EXTERNAL_IP=$(curl -s ifconfig.me)

# Generate client config for Jarvis Core
echo -e "${YELLOW}Generating client configuration...${NC}"

CLIENT_CONFIG_PATH="${HOME}/jarvis-core-wireguard.conf"
cat > ${CLIENT_CONFIG_PATH} << EOF
# Jarvis Core - WireGuard Client Configuration
# Copy this to Jarvis Core server at /etc/wireguard/jarvis-home.conf
# Generated: $(date)

[Interface]
Address = ${CLIENT_WG_IP}/24
PrivateKey = ${CLIENT_PRIVATE}

# Optional: Use home DNS
# DNS = 1.1.1.1

[Peer]
# Jarvis Edge Node (Home)
PublicKey = ${SERVER_PUBLIC}
Endpoint = ${EXTERNAL_IP}:${WG_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

chmod 600 ${CLIENT_CONFIG_PATH}

echo ""
echo -e "${GREEN}=========================================="
echo "  WIREGUARD SETUP COMPLETE"
echo "==========================================${NC}"
echo ""
echo -e "${CYAN}Server Status:${NC}"
sudo wg show
echo ""
echo -e "${CYAN}Your External IP: ${EXTERNAL_IP}${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Configure your router to forward:${NC}"
echo "  Protocol: UDP"
echo "  External Port: ${WG_PORT}"
echo "  Internal IP: $(hostname -I | awk '{print $1}')"
echo "  Internal Port: ${WG_PORT}"
echo ""
echo -e "${YELLOW}Client config saved to:${NC}"
echo "  ${CLIENT_CONFIG_PATH}"
echo ""
echo "Copy this file to your Jarvis Core server and run:"
echo "  sudo cp jarvis-home.conf /etc/wireguard/"
echo "  sudo wg-quick up jarvis-home"
echo ""
echo -e "${YELLOW}To set up SOCKS5 proxy through tunnel, install dante-server:${NC}"
echo "  sudo apt install dante-server"
echo "  (See scripts/dante-setup.sh for configuration)"
echo ""
echo -e "${GREEN}Keys stored in /etc/wireguard/${NC}"
echo ""
