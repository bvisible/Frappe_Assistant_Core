# SSE Bridge Quick Reference

## 🚀 Quick Start

### Install Dependencies
```bash
pip install frappe_assistant_core[sse-bridge]
```

### Configure in Frappe
1. Go to **Assistant Core Settings** in Frappe
2. Enable **"Enable SSE Bridge"** checkbox
3. Configure port (default: 8080) and host (default: 0.0.0.0)
4. Use the **Start SSE Bridge** button to launch

### Alternative: Start with Bench
```bash
bench start  # SSE bridge runs automatically if enabled
```

### Health Check
```bash
curl http://localhost:8080/health
```

### Test Ping
```bash
# Send ping request (requires active SSE connection)
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"ping","id":1}' \
  "http://localhost:8080/mcp/messages?cid=CONNECTION_ID"
```

## 📋 Configuration

### Primary: Assistant Core Settings (Recommended)
1. Navigate to **Assistant Core Settings** doctype
2. Configure under **"SSE Bridge Configuration"** section:
   - **Enable SSE Bridge**: Master toggle
   - **SSE Bridge Port**: Server port (default: 8080)
   - **SSE Bridge Host**: Bind address (default: 0.0.0.0)
   - **Enable SSE Bridge Debug Mode**: Debug logging

### Alternative: Environment Variables
```bash
export SSE_BRIDGE_ENABLED=true   # Enable/disable bridge
export SSE_BRIDGE_HOST=0.0.0.0   # Server address
export SSE_BRIDGE_PORT=8080      # Server port
export SSE_BRIDGE_DEBUG=false    # Debug mode
```

### Development (.env file)
```env
HOST=0.0.0.0
PORT=8080
DEBUG=true
LOG_LEVEL=debug
FRAPPE_API_SECRET=your_secret
```

## 🔧 Manual Operations

### Start via Frappe UI (Recommended)
1. Go to **Assistant Core Settings**
2. Click **"Start SSE Bridge"** button
3. Monitor status in the **"SSE Bridge Status"** section

### Start Manually
```bash
python -c "from frappe_assistant_core.services.sse_bridge import main; main()"
```

### Stop via Frappe UI
1. Go to **Assistant Core Settings**
2. Click **"Stop SSE Bridge"** button
3. Confirms graceful shutdown

### Test Module Import
```bash
python -c "from frappe_assistant_core.services.sse_bridge import create_app; print('✅ Ready!')"
```

### Start with Uvicorn
```bash
uvicorn frappe_assistant_core.services.sse_bridge:create_app --factory --host 0.0.0.0 --port 8080
```

## 🏗️ Production Deployment

### Systemd Service
```ini
[Unit]
Description=Frappe SSE Bridge
After=network.target

[Service]
Type=simple
User=frappe
WorkingDirectory=/path/to/frappe-bench
Environment=HOST=0.0.0.0
Environment=PORT=8080
Environment=DEBUG=false
ExecStart=/path/to/frappe-bench/env/bin/python -c "from frappe_assistant_core.services.sse_bridge import main; main()"
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install .[sse-bridge]
EXPOSE 8080
ENV HOST=0.0.0.0 PORT=8080 DEBUG=false
CMD ["python", "-c", "from frappe_assistant_core.services.sse_bridge import main; main()"]
```

## 🔐 Authentication

### Bearer Token
```bash
curl -H "Authorization: Bearer your-token" \
  "http://localhost:8080/mcp/sse?server_url=https://your-site.com&device=my-device"
```

### API Key
```bash
curl -H "Authorization: token api-key:api-secret" \
  "http://localhost:8080/mcp/sse?server_url=https://your-site.com&device=my-device"
```

## 🛠️ Troubleshooting

### Common Issues

**SSE Bridge not starting:**
1. Check **Assistant Core Settings** → **Enable SSE Bridge** is checked
2. Verify port availability: `lsof -i :8080`
3. Check status via **"Check SSE Bridge Status"** button

**Port in use:**
1. Change port in **Assistant Core Settings** → **SSE Bridge Port**
2. Or check what's using port: `lsof -i :8080`

**Module not found:**
```bash
pip install frappe_assistant_core[sse-bridge]  # Install dependencies
```

**Authentication failed:**
```bash
# Check token format and server accessibility
curl https://your-site.com/api/method/frappe.auth.get_logged_user
```

**Process management:**
- **Start**: Use "Start SSE Bridge" button in settings
- **Stop**: Use "Stop SSE Bridge" button in settings
- **Status**: Use "Check SSE Bridge Status" button
- **Debug**: Enable "SSE Bridge Debug Mode" in settings

## 📊 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health and metrics |
| `/mcp/sse` | GET | Establish SSE connection |
| `/mcp/messages` | POST | Send MCP requests |

### MCP Method Routing

| Method | Handling | Description |
|--------|----------|-------------|
| `initialize` | Forward + Local | Gets capabilities from backend |
| `resources/list` | Local | Returns empty resources |
| `ping` | Local | Immediate pong response |
| All others | Forward | Sent to Frappe backend |

## 🔍 Monitoring

### Health Response
```json
{
  "status": "healthy",
  "service": "frappe-assistant-core-sse-bridge-enhanced",
  "active_connections": 5,
  "messages_sent": 150,
  "storage_backend": "redis",
  "total_connections": 25
}
```

### Log Monitoring
```bash
# Development
tail -f logs/sse-bridge.log

# Production (systemd)
journalctl -u frappe-sse-bridge -f

# Production (supervisor)
tail -f /var/log/frappe/sse-bridge.log
```

## 📁 File Locations

```
frappe_assistant_core/
├── services/
│   ├── __init__.py
│   ├── __main__.py
│   ├── sse_bridge.py          # Main SSE bridge service
│   └── config_reader.py       # Configuration coordination
├── assistant_core/doctype/assistant_core_settings/
│   ├── assistant_core_settings.py   # SSE bridge management
│   ├── assistant_core_settings.js   # UI integration
│   └── assistant_core_settings.json # DocType definition
├── pyproject.toml             # Dependencies: [sse-bridge]
└── docs/
    ├── SSE_BRIDGE_INTEGRATION.md    # Complete guide
    └── SSE_BRIDGE_QUICK_REFERENCE.md # This file
```

## 🔗 Related Documentation

- **[Complete SSE Bridge Guide](SSE_BRIDGE_INTEGRATION.md)** - Full documentation
- **[Technical Documentation](TECHNICAL_DOCUMENTATION.md)** - Architecture details
- **[API Reference](API_REFERENCE.md)** - Frappe Assistant Core APIs

---

**Need help?** See the [complete documentation](SSE_BRIDGE_INTEGRATION.md) or contact [jypaulclinton@gmail.com](mailto:jypaulclinton@gmail.com)