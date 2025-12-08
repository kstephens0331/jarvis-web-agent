# JARVIS Core Integration Guide

This document describes how the Web Agent integrates with JARVIS Core.

## Architecture Overview

```
+-------------------------------------------------------------------------+
|                           JARVIS ECOSYSTEM                               |
+-------------------------------------------------------------------------+
|                                                                          |
|   +----------------------+         +--------------------------------+    |
|   |   JARVIS CORE        |         |      JARVIS WEB AGENT          |    |
|   |   (Railway Cloud)    |  REST   |      (Edge Node)               |    |
|   |                      |<------->|                                |    |
|   |   Node.js/TypeScript |  API    |      Python/FastAPI            |    |
|   |                      |         |      Playwright                |    |
|   |   +----------------+ |         |                                |    |
|   |   |webAgentService | |         |  +----------------------------+|    |
|   |   |   (Client)     |-|---------|->| /fetch, /browse, /session  ||    |
|   |   +----------------+ |         |  +----------------------------+|    |
|   +----------------------+         +--------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

## Network Configuration

### Edge Node Setup

The Web Agent runs on your local edge node (Intel i3) and needs to be accessible from Railway:

1. **WireGuard VPN Tunnel** (Recommended)
   - Set up WireGuard on edge node
   - Configure Railway environment to connect via VPN
   - Most secure option

2. **Port Forwarding** (Alternative)
   - Forward port 3000 from router to edge node
   - Use API key authentication
   - Enable HTTPS via reverse proxy

### Environment Variables (JARVIS Core)

Add to Railway environment:

```env
# Web Agent Connection
WEB_AGENT_URL=http://10.10.10.2:3000  # WireGuard IP
WEB_AGENT_API_KEY=your-secure-api-key
WEB_AGENT_TIMEOUT=60000
```

## Client Service (JARVIS Core)

JARVIS Core includes a `webAgentService` module at `src/modules/webagent/`:

### Basic Fetch

```typescript
import { webAgentService } from './modules/webagent';

// Simple page fetch
const result = await webAgentService.fetch({
  url: 'https://example.com',
  waitFor: '#content',
  extract: {
    title: 'h1',
    price: '.price'
  }
});
```

### Browser Automation

```typescript
// Full browser session with actions
const result = await webAgentService.browse({
  url: 'https://example.com/login',
  actions: [
    { action: 'type', selector: '#email', value: 'user@example.com' },
    { action: 'type', selector: '#password', value: 'password' },
    { action: 'click', selector: '#submit' },
    { action: 'wait_navigation' },
    { action: 'extract', selector: '.dashboard-data' }
  ],
  humanLike: true
});
```

### Persistent Sessions

```typescript
// Create persistent session for banking
const session = await webAgentService.createSession({
  name: 'chase-banking',
  identity: 'kyle-primary',
  proxyMode: 'home'  // Always use home IP for banking
});

// Execute actions in session
const result = await webAgentService.sessionAction(session.id, {
  actions: [
    { action: 'goto', url: 'https://chase.com/accounts' },
    { action: 'extract', selector: '.account-balance' }
  ]
});
```

### Background Jobs

```typescript
// Submit long-running job
const job = await webAgentService.queueSubmit({
  type: 'scrape',
  url: 'https://example.com/large-page',
  options: {
    screenshot: true,
    fullPage: true
  }
});

// Check job status
const status = await webAgentService.getJobStatus(job.id);
```

## Use Cases

### 1. Bill Scraping

```typescript
// Scrape utility bill from provider portal
const bill = await webAgentService.browse({
  url: 'https://utility-provider.com/login',
  sessionName: 'utility-account',
  actions: [
    { action: 'type', selector: '#username', value: process.env.UTILITY_USER },
    { action: 'type', selector: '#password', value: process.env.UTILITY_PASS },
    { action: 'click', selector: '#login-btn' },
    { action: 'wait_navigation' },
    { action: 'goto', url: '/billing/current' },
    { action: 'extract', selector: '.amount-due', as: 'amountDue' },
    { action: 'extract', selector: '.due-date', as: 'dueDate' }
  ]
});

// Create bill in JARVIS
await billsService.create({
  name: 'Electric',
  amount: parseFloat(bill.data.amountDue),
  dueDate: new Date(bill.data.dueDate),
  source: 'web-agent'
});
```

### 2. Medical Portal Integration

```typescript
// Check MyChart for new messages
const messages = await webAgentService.browse({
  url: 'https://mychart.example.com',
  sessionName: 'mychart-family',
  proxyMode: 'home',
  actions: [
    { action: 'wait_for', selector: '.message-list' },
    { action: 'extract_all', selector: '.message-item', fields: {
      date: '.msg-date',
      from: '.msg-from',
      subject: '.msg-subject',
      unread: '.unread-indicator'
    }}
  ]
});
```

### 3. School Portal Monitoring

```typescript
// Check school grades
const grades = await webAgentService.browse({
  url: 'https://school-portal.edu/grades',
  sessionName: 'school-portal',
  actions: [
    { action: 'wait_for', selector: '.grade-table' },
    { action: 'screenshot', filename: 'grades.png' },
    { action: 'extract_all', selector: '.grade-row', fields: {
      class: '.class-name',
      grade: '.current-grade',
      lastUpdated: '.last-update'
    }}
  ]
});
```

## Health Monitoring

JARVIS Core periodically checks Web Agent health:

```typescript
// Health check (automatic via scheduler)
const health = await webAgentService.getHealth();
// Returns: { status: 'healthy', browsers: 2, queue: 5 }
```

Integrated into JARVIS health endpoint:

```json
GET /api/health
{
  "modules": {
    "webagent": {
      "status": "healthy",
      "message": "2 browsers active, 5 jobs queued",
      "details": {
        "connected": true,
        "activeBrowsers": 2,
        "queuedJobs": 5
      }
    }
  }
}
```

## Error Handling

```typescript
try {
  const result = await webAgentService.fetch({ url: 'https://example.com' });
} catch (error) {
  if (error.code === 'ECONNREFUSED') {
    // Web Agent not reachable
    log.error('Web Agent offline');
  } else if (error.code === 'CAPTCHA_REQUIRED') {
    // Need manual CAPTCHA solving
    await notificationsService.send({
      title: 'CAPTCHA Required',
      message: 'Manual intervention needed for example.com'
    });
  } else if (error.code === 'RATE_LIMITED') {
    // Site is rate limiting
    await webAgentService.queueSubmit({
      ...originalRequest,
      delay: 300000 // Retry in 5 minutes
    });
  }
}
```

## Security Best Practices

1. **API Key Rotation**: Rotate Web Agent API key monthly
2. **Session Isolation**: Use separate browser profiles per identity
3. **Proxy Selection**:
   - Banking/Financial: Always home IP
   - General scraping: Can use SACVPN rotation
4. **Credential Storage**: Store site credentials in Railway env vars, not in Web Agent
5. **Audit Logging**: All Web Agent requests logged with timestamps

## Troubleshooting

### Web Agent Unreachable

```bash
# On edge node
docker-compose logs web-agent
sudo wg show  # Check WireGuard status
```

### Browser Crashes

```bash
# Check container resources
docker stats jarvis-web-agent

# Reduce concurrent browsers
# In .env: MAX_CONCURRENT_BROWSERS=2
```

### CAPTCHA Issues

Some CAPTCHAs require manual intervention. The Web Agent will:
1. Take screenshot
2. Send notification via JARVIS
3. Wait for manual solve or timeout
