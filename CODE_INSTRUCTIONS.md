# Claude Code Implementation Instructions

## Project: Jarvis Web Agent
## Owner: Kyle Stephens, StephensCode LLC

---

## Overview

This is a self-hosted web scraping and browser automation module for Project JARVIS.
All dependencies are open source. No external API costs.

---

## Implementation Phases

### Phase 1: Edge Node Setup [HARDWARE READY CHECKPOINT]

**Prerequisites:**
- Intel i3 with 8GB RAM
- Ubuntu Server 24.04 LTS installed
- Network: 1Gbps Tachus fiber

**Steps:**

1. Clone project to edge node:
```bash
git clone <repo> ~/jarvis/web-agent
cd ~/jarvis/web-agent
```

2. Run base setup:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

3. **LOG OUT AND BACK IN** (docker group membership)

4. Run WireGuard setup:
```bash
chmod +x scripts/wireguard-setup.sh
./scripts/wireguard-setup.sh
```

5. Configure router port forward:
   - Protocol: UDP
   - External Port: 51820
   - Internal IP: (edge node LAN IP)
   - Internal Port: 51820

6. Copy `.env.example` to `.env` and configure

7. Start services:
```bash
docker-compose up -d
```

---

### Phase 2: Core Implementation

The project structure is complete. Key areas to extend:

**Priority 1: Browser Pool Enhancement**
- Add connection pooling with health checks
- Implement browser recycling after N requests
- Add memory monitoring to prevent OOM

**Priority 2: FlareSolverr Integration**
- Create `/src/bypass/flaresolverr.py`
- Auto-fallback when Cloudflare detected
- Cache successful sessions

**Priority 3: Session Persistence**
- Move from in-memory to Redis storage
- Implement session recovery on restart
- Add session encryption for sensitive sites

---

### Phase 3: Jarvis Core Integration

The web agent exposes a REST API. Connect from Jarvis Core:

```python
# In Jarvis Core
import httpx

class WebAgentClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    async def fetch(self, url: str, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/fetch",
                json={"url": url, **kwargs},
                headers=self.headers
            )
            return response.json()
    
    async def browse(self, url: str, actions: list):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/browse",
                json={"url": url, "actions": actions},
                headers=self.headers
            )
            return response.json()
```

---

## API Reference

### POST /fetch
Simple page fetch with auto-protection handling.

```json
{
    "url": "https://example.com",
    "wait_for": "#content",
    "timeout": 30000,
    "proxy_mode": "auto",
    "extract": {
        "title": "h1",
        "price": ".price"
    },
    "screenshot": true
}
```

### POST /browse
Execute browser actions sequence.

```json
{
    "url": "https://example.com/login",
    "actions": [
        {"action": "type", "selector": "#email", "value": "user@example.com"},
        {"action": "type", "selector": "#password", "value": "secret"},
        {"action": "click", "selector": "#submit"},
        {"action": "wait_navigation"},
        {"action": "extract", "selector": ".dashboard-data"}
    ],
    "human_like": true
}
```

### POST /session/create
Create persistent browser session.

```json
{
    "name": "chase-banking",
    "identity": "kyle-primary",
    "proxy_mode": "home"
}
```

### POST /session/{id}/action
Execute action in existing session.

### POST /queue/submit
Submit async background job.

---

## Testing

```bash
# Run tests
docker-compose exec web-agent pytest

# Test fetch endpoint
curl -X POST http://localhost:3000/fetch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"url": "https://httpbin.org/html"}'

# Health check
curl http://localhost:3000/health
```

---

## Monitoring

```bash
# View logs
docker-compose logs -f web-agent

# Check resource usage
docker stats

# Browser pool status
curl http://localhost:3000/health

# Queue status
curl -H "X-API-Key: your-key" http://localhost:3000/queue/stats
```

---

## Troubleshooting

### Browser crashes / OOM
- Reduce MAX_CONCURRENT_BROWSERS in .env
- Add swap space to edge node
- Check for memory leaks in long-running sessions

### CAPTCHA not solving
- Verify Tesseract is installed in container
- Check Whisper model downloaded successfully
- Some CAPTCHAs (hCaptcha image grids) require manual solving

### Proxy connection failed
- Verify WireGuard is running: `sudo wg show`
- Check router port forwarding
- Test home proxy: `curl --proxy socks5://10.10.10.1:1080 https://httpbin.org/ip`

### Cloudflare blocking
- Verify FlareSolverr is running: `docker-compose logs flaresolverr`
- Some sites require residential IP (use home proxy)
- Increase delays between requests

---

## Security Notes

1. **API Key**: Generate strong key, never commit to repo
2. **Profiles**: Contains session data, cookies, auth - encrypt at rest
3. **WireGuard Keys**: Store securely, regenerate if compromised
4. **Banking Sessions**: Use home IP only, never rotate proxies

---

## Future Enhancements

- [ ] Browser extension injection for additional stealth
- [ ] Machine learning for CAPTCHA image selection
- [ ] Distributed browser pool across multiple nodes
- [ ] Real-time proxy health dashboard
- [ ] Automatic fingerprint rotation
- [ ] Integration with Jarvis voice commands

---

## Contact

Kyle Stephens  
Founder & CTO, StephensCode LLC  
kyle@stephenscode.dev  
(936) 323-4527
