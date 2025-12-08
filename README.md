# Jarvis Web Agent

Self-hosted web scraping and browser automation module for Project JARVIS.
Fully self-hosted, no external API dependencies. Open source under MIT License.

## Part of the JARVIS Ecosystem

| Repository | Description | Deployment |
|------------|-------------|------------|
| [jarvis](https://github.com/kstephens0331/jarvis) | Core backend API (Node.js/TypeScript) | Railway Cloud |
| **jarvis-web-agent** | Browser automation service (Python) | Edge Node (Self-hosted) |
| jarvis-dashboard | PWA Dashboard (Next.js) | Coming Soon |

## Integration with JARVIS Core

The Web Agent runs on your local edge node and communicates with JARVIS Core via REST API.
JARVIS Core connects to the Web Agent using the built-in `webAgentService` client.

See [JARVIS_INTEGRATION.md](./JARVIS_INTEGRATION.md) for detailed integration documentation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS WEB AGENT                         │
├─────────────────────────────────────────────────────────────┤
│  API Layer (:3000)                                          │
│    └── FastAPI server for Jarvis Core communication         │
├─────────────────────────────────────────────────────────────┤
│  Browser Engine                                             │
│    ├── Playwright (Chromium)                                │
│    ├── Stealth patches                                      │
│    ├── Fingerprint injection                                │
│    └── Human behavior simulation                            │
├─────────────────────────────────────────────────────────────┤
│  Session Manager                                            │
│    ├── Persistent browser profiles                          │
│    ├── Cookie/auth state storage                            │
│    └── Identity management                                  │
├─────────────────────────────────────────────────────────────┤
│  Proxy Router                                               │
│    ├── Home exit (residential IP via WireGuard)             │
│    ├── SACVPN nodes (rotation/geo)                          │
│    └── Direct connection                                    │
├─────────────────────────────────────────────────────────────┤
│  Protection Bypass                                          │
│    ├── FlareSolverr (Cloudflare)                            │
│    ├── CAPTCHA solver (Tesseract + Whisper)                 │
│    └── Rate limit management                                │
├─────────────────────────────────────────────────────────────┤
│  Job Queue (Redis)                                          │
│    └── Async task processing                                │
└─────────────────────────────────────────────────────────────┘
```

## Hardware Requirements

- **Edge Node**: Intel i3, 8GB RAM, Ubuntu Server 24.04 LTS
- **Network**: 1Gbps fiber (Tachus)
- **Storage**: 50GB+ for browser profiles

## Quick Start

```bash
# 1. Clone to edge node
git clone <repo> ~/jarvis/web-agent
cd ~/jarvis/web-agent

# 2. Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Configure environment
cp .env.example .env
nano .env

# 4. Start services
docker-compose up -d
```

## [HARDWARE READY] Checkpoint

Before deploying, ensure:
- [ ] Ubuntu Server 24.04 installed on i3
- [ ] WireGuard configured (see scripts/wireguard-setup.sh)
- [ ] Router port forward: UDP 51820
- [ ] Docker and Docker Compose installed

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/fetch` | POST | Simple page fetch |
| `/browse` | POST | Full browser session |
| `/session/create` | POST | Create persistent session |
| `/session/{id}/action` | POST | Execute action in session |
| `/queue/submit` | POST | Submit async job |
| `/queue/{job_id}` | GET | Get job status/result |

## Environment Variables

```env
# Core
REDIS_URL=redis://redis:6379
FLARESOLVERR_URL=http://flaresolverr:8191

# Proxy
HOME_PROXY_ENABLED=true
HOME_PROXY_URL=socks5://10.10.10.1:1080
SACVPN_NODES=node1.sacvpn.com:1080,node2.sacvpn.com:1080

# Browser
MAX_CONCURRENT_BROWSERS=3
BROWSER_TIMEOUT=30000
HEADLESS=true

# Security
API_KEY=<generate-strong-key>
```

## Directory Structure

```
jarvis-web-agent/
├── src/
│   ├── api/              # FastAPI routes
│   ├── browser/          # Playwright engine
│   ├── stealth/          # Anti-detection
│   ├── proxy/            # Proxy routing
│   ├── captcha/          # CAPTCHA solving
│   ├── session/          # Profile management
│   └── queue/            # Redis job queue
├── scripts/              # Setup and utility scripts
├── profiles/             # Browser profiles (gitignored)
├── data/                 # Persistent data (gitignored)
├── tests/                # Test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Security Notes

1. **API Key**: Generate a strong key, never commit to repo
2. **Profiles**: Contains session data, cookies, auth - encrypt at rest
3. **WireGuard Keys**: Store securely, regenerate if compromised
4. **Banking Sessions**: Use home IP only, never rotate proxies

## License

MIT License - StephensCode LLC

## Related Documentation

- [JARVIS_INTEGRATION.md](./JARVIS_INTEGRATION.md) - Integration with JARVIS Core
- [CLAUDE_CODE_INSTRUCTIONS.md](./CLAUDE_CODE_INSTRUCTIONS.md) - Implementation guide
