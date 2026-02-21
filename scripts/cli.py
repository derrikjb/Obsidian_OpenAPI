#!/usr/bin/env python3
"""
CLI entry point for non-interactive mode.

Usage:
    python scripts/cli.py [OPTIONS]
    
Examples:
    # Start with default settings
    python scripts/cli.py
    
    # Specify Obsidian connection
    python scripts/cli.py --obsidian-url http://localhost:27123 --obsidian-key xxx
    
    # Use different port
    python scripts/cli.py --port 8080
    
    # Debug mode
    python scripts/cli.py --debug
"""

import os
import sys
from pathlib import Path

import click


@click.command()
@click.option(
    "--port",
    "-p",
    type=int,
    default=27150,
    help="Server port (default: 27150)",
)
@click.option(
    "--host",
    "-h",
    default="0.0.0.0",
    help="Server host binding (default: 0.0.0.0)",
)
@click.option(
    "--obsidian-url",
    "-u",
    default="http://127.0.0.1:27123",
    help="Obsidian REST API URL",
)
@click.option(
    "--obsidian-key",
    "-k",
    required=True,
    help="Obsidian API Key",
)
@click.option(
    "--server-key",
    "-s",
    help="Server API Key (auto-generated if not provided)",
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug mode",
)
@click.option(
    "--reload",
    "-r",
    is_flag=True,
    help="Enable auto-reload (for development)",
)
@click.option(
    "--cors",
    "-c",
    default="*",
    help="CORS origins (comma-separated, default: *)",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level",
)
@click.option(
    "--max-history",
    "-m",
    type=int,
    default=10,
    help="Max history entries for rollback (0 to disable)",
)
@click.option(
    "--non-interactive",
    "-n",
    is_flag=True,
    help="Non-interactive mode (no prompts)",
)
def main(
    port: int,
    host: str,
    obsidian_url: str,
    obsidian_key: str,
    server_key: str,
    debug: bool,
    reload: bool,
    cors: str,
    log_level: str,
    max_history: int,
    non_interactive: bool,
):
    """
    Start the Obsidian OpenAPI Server.
    
    This is the non-interactive CLI mode suitable for:
    - Docker deployments
    - CI/CD pipelines
    - Systemd services
    - Automated scripts
    """
    # Set environment variables
    os.environ["OBSIDIAN_OPENAPI_PORT"] = str(port)
    os.environ["OBSIDIAN_OPENAPI_HOST"] = host
    os.environ["OBSIDIAN_API_URL"] = obsidian_url
    os.environ["OBSIDIAN_API_KEY"] = obsidian_key
    os.environ["CORS_ORIGINS"] = cors
    os.environ["DEBUG"] = str(debug).lower()
    os.environ["LOG_LEVEL"] = log_level
    os.environ["MAX_HISTORY_ENTRIES"] = str(max_history)
    
    if server_key:
        os.environ["SERVER_API_KEY"] = server_key
    
    # Check if we're in the right directory
    if not Path("app/main.py").exists():
        click.echo(
            "Error: app/main.py not found. Please run from the project root.",
            err=True,
        )
        sys.exit(1)
    
    # Print startup info
    click.echo("=" * 60)
    click.echo("  Obsidian OpenAPI Server - Starting")
    click.echo("=" * 60)
    click.echo()
    click.echo(f"Port:          {port}")
    click.echo(f"Host:          {host}")
    click.echo(f"Obsidian URL:  {obsidian_url}")
    click.echo(f"Debug:         {debug}")
    click.echo(f"Reload:        {reload}")
    click.echo()
    
    # Import and start the server
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level.lower(),
    )


if __name__ == "__main__":
    main()