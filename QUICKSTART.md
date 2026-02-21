# Quick Start Guide

Get your Obsidian OpenAPI Server running in 5 minutes!

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run interactive setup
python scripts/setup.py

# 3. Start the server
python start.py
```

That's it! Your server is now running on port 27150.

## What's Next?

### View the API Documentation
Open your browser to: http://localhost:27150/docs

### Connect to Open WebUI
1. In Open WebUI, go to Admin Settings → Tools → OpenAPI Tool Servers
2. Add server URL: `http://localhost:27150`
3. Add API key from your `.env` file
4. Done! All tools are now available

### Test the API
```bash
# Get your API key from .env file
export API_KEY=$(grep SERVER_API_KEY .env | cut -d= -f2)

# Test health check (no auth required)
curl http://localhost:27150/health

# List vault contents
curl -H "X-API-Key: $API_KEY" http://localhost:27150/vault

# Read a file
curl -H "X-API-Key: $API_KEY" http://localhost:27150/vault/my-note.md
```

## Configuration

All settings are in the `.env` file created by setup. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `OBSIDIAN_API_KEY` | (required) | Your Obsidian API key |
| `OBSIDIAN_API_URL` | http://127.0.0.1:27123 | Obsidian REST API URL |
| `OBSIDIAN_OPENAPI_PORT` | 27150 | Server port |
| `MAX_HISTORY_ENTRIES` | 10 | Write operation history |

## Troubleshooting

### "No module named 'fastapi'"
```bash
pip install -r requirements.txt
```

### "Connection refused to Obsidian"
- Make sure Obsidian is running
- Enable Local REST API plugin in Obsidian
- Check API key in Obsidian settings

### "Port already in use"
Change port in `.env` file:
```env
OBSIDIAN_OPENAPI_PORT=27151
```

## Docker (Optional)

```bash
# Build and run with docker-compose
docker-compose up -d
```

## Need Help?

- Read the full [README.md](README.md)
- Check the API docs at `/docs` when server is running
- View example requests in the Swagger UI

---

**Ready to go!** 🚀