# Obsidian OpenAPI Server

A modern, fast, and cross-platform OpenAPI Tool Server for Obsidian integration. Optimized for Open WebUI with secure API key authentication, write operation history, and a beautiful interactive setup experience.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **OpenAPI Standard**: Native OpenAPI 3.0 spec for seamless Open WebUI integration
- **Secure Authentication**: Auto-generated cryptographically secure API keys
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Interactive Setup**: Beautiful Inquirer-based configuration wizard
- **CLI Mode**: Non-interactive mode for Docker/CI deployments
- **Fast & Modern**: Built with FastAPI and Pydantic v2 for maximum performance
- **Write History**: Optional rollback capability for write operations
- **Docker Ready**: Production-ready Docker and docker-compose configurations
- **Health Checks**: Built-in health monitoring with Obsidian connectivity verification

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Obsidian** with the **Local REST API** plugin installed and enabled
- **Obsidian API Key** from the plugin settings

### Installation

1. **Clone or download the repository**:
   ```bash
   git clone https://github.com/derrikjb/Obsidian_MCP.git
   cd Obsidian_OpenAPI
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the interactive setup wizard**:
   ```bash
   python scripts/setup.py
   ```

4. **Start the server**:
   ```bash
   python -m app.main
   ```

The server will start on port `27150` (configurable) and automatically generate a secure API key on first run.

## API Endpoints

### System Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check & Obsidian connectivity |
| GET | `/docs` | No | Swagger UI documentation |
| GET | `/openapi.json` | No | OpenAPI specification |
| POST | `/auth/regenerate-key` | Yes | Regenerate API key |
| GET | `/history` | Yes | Get operation history |
| DELETE | `/history` | Yes | Clear operation history |

### Vault Operations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/vault/{path}` | Yes | Get file content (markdown/json/document-map) |
| POST | `/vault/{path}` | Yes | Create or replace file |
| PATCH | `/vault/{path}` | Yes | Partial update (heading/block/frontmatter) |
| PATCH | `/vault/{path}/append` | Yes | Append to file |
| DELETE | `/vault/{path}` | Yes | Delete file |

### Directory Operations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/vault` | Yes | List vault contents |

### Search Operations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/search` | Yes | Simple text search |
| POST | `/search/advanced` | Yes | Dataview DQL / JsonLogic search |

## Usage Examples

### Get File Content
```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:27150/vault/my-note.md
```

### Create a File
```bash
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"content": "# My New Note\n\nHello World!"}' \
  http://localhost:27150/vault/my-new-note.md
```

### Search
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:27150/search?query=hello&limit=10"
```

### Advanced Search (Dataview DQL)
```bash
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "dataview",
    "query": "TABLE file.mtime FROM #project WHERE status = 'active'",
    "limit": 50
  }' \
  http://localhost:27150/search/advanced
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OBSIDIAN_OPENAPI_PORT` | Server port | `27150` |
| `OBSIDIAN_OPENAPI_HOST` | Server host binding | `0.0.0.0` |
| `OBSIDIAN_API_URL` | Obsidian REST API URL | `http://127.0.0.1:27123` |
| `OBSIDIAN_API_KEY` | Obsidian API Key | (required) |
| `SERVER_API_KEY` | Server API Key | (auto-generated) |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_HISTORY_ENTRIES` | Write history size | `10` |
| `REQUEST_TIMEOUT` | Request timeout (seconds) | `30` |
| `ENABLE_KEY_REGENERATION` | Allow key regeneration | `false` |

### Interactive Setup

Run the beautiful interactive wizard:
```bash
python scripts/setup.py
```

### Non-Interactive CLI

For Docker, CI/CD, or automated deployments:
```bash
python scripts/cli.py \
  --obsidian-key your-obsidian-key \
  --port 27150 \
  --host 0.0.0.0
```

## Open WebUI Integration

1. **Start the server**:
   ```bash
   python -m app.main
   ```

2. **In Open WebUI**, go to:
   - **Admin Settings** → **Tools** → **OpenAPI Tool Servers**

3. **Add a new tool server**:
   - **Name**: Obsidian
   - **URL**: `http://localhost:27150`
   - **API Key**: Your generated key (shown in logs or `.env` file)

4. Open WebUI will automatically fetch the OpenAPI spec and make all tools available!

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Create your `.env` file**:
   ```bash
   python scripts/setup.py
   ```

2. **Start with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

### Using Docker Run

```bash
docker run -d \
  --name obsidian-openapi-server \
  -p 27150:27150 \
  -e OBSIDIAN_API_URL=http://host.docker.internal:27123 \
  -e OBSIDIAN_API_KEY=your-obsidian-key \
  -e SERVER_API_KEY=your-server-key \
  obsidian-openapi-server:latest
```

### Building the Image

```bash
docker build -t obsidian-openapi-server:latest .
```

## Write Operation History

Enable automatic tracking of write operations for potential rollback:

1. Set `MAX_HISTORY_ENTRIES` in your `.env` file (default: 10)
2. View history: `GET /history`
3. Clear history: `DELETE /history`

Each write operation (create, append, patch, delete) stores the previous content, enabling future rollback functionality.

## Development

### Local Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run with auto-reload
python -m app.main

# Or use the CLI with reload
python scripts/cli.py --reload --debug
```

### Project Structure

```
obsidian-openapi-server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Configuration management
│   ├── auth.py              # API key authentication
│   ├── models.py            # Pydantic models
│   ├── routers/
│   │   ├── vault.py         # Vault file operations
│   │   ├── directory.py     # Directory operations
│   │   └── search.py        # Search operations
│   └── services/
│       ├── obsidian.py      # Obsidian API client
│       └── history.py       # Operation history manager
├── scripts/
│   ├── setup.py             # Interactive setup wizard
│   └── cli.py               # Non-interactive CLI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Troubleshooting

### Server won't start

1. **Check Obsidian is running** with Local REST API plugin enabled
2. **Verify API key** is correct in `.env` file
3. **Check port availability**: `lsof -i :27150` (macOS/Linux) or `netstat -ano | findstr 27150` (Windows)

### Connection refused to Obsidian

- **Windows/macOS**: If running Obsidian on the host and server in Docker, use `host.docker.internal` instead of `127.0.0.1`
- **Linux**: Use the host's IP address or `--network host` in Docker

### API key issues

- Check the `.env` file for `SERVER_API_KEY`
- If lost, delete the `.env` file and run `python scripts/setup.py` again
- Or regenerate via API if `ENABLE_KEY_REGENERATION=true`

### CORS errors in browser

Update `CORS_ORIGINS` in `.env` to include your origin:
```env
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## Security Considerations

- **API Key**: Keep your `SERVER_API_KEY` secure. It provides full access to your vault.
- **Network**: Use HTTPS in production (via reverse proxy like nginx)
- **Obsidian API**: The server passes through your Obsidian API key - keep it secure
- **Key Regeneration**: Disable `ENABLE_KEY_REGENERATION` in production unless needed
- **CORS**: Restrict `CORS_ORIGINS` to known domains in production

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! This is an open project following the OpenAPI Tool Server standard.

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [HTTPX](https://www.python-httpx.org/) - Async HTTP client
- [Inquirer](https://github.com/magmax/python-inquirer) - Interactive CLI
- [Open WebUI](https://github.com/open-webui/openapi-servers) - OpenAPI Server standard