#!/usr/bin/env python3
"""
Interactive setup wizard for Obsidian OpenAPI Server.

This script guides you through configuring the server with a beautiful
interactive CLI using Inquirer.
"""

import os
import secrets
import sys
from pathlib import Path

try:
    import inquirer
    from colorama import Fore, Style, init
except ImportError:
    print("Error: Required packages not installed.")
    print("Run: pip install inquirer colorama")
    sys.exit(1)

# Initialize colorama for cross-platform colored output
init(autoreset=True)


def print_header():
    """Print the setup wizard header."""
    print()
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + "     Obsidian OpenAPI Server - Setup Wizard")
    print(Fore.CYAN + "=" * 60)
    print()
    print("Welcome! This wizard will help you configure your server.")
    print()


def print_success(message):
    """Print a success message."""
    print(Fore.GREEN + "✓ " + message)


def print_warning(message):
    """Print a warning message."""
    print(Fore.YELLOW + "⚠ " + message)


def print_info(message):
    """Print an info message."""
    print(Fore.BLUE + "ℹ " + message)


def generate_api_key():
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def check_existing_env():
    """Check if .env file already exists."""
    env_path = Path(".env")
    if env_path.exists():
        return True
    return False


def load_existing_config():
    """Load existing configuration from .env file."""
    config = {}
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key] = value
    return config


def save_config(config):
    """Save configuration to .env file."""
    env_path = Path(".env")
    
    lines = [
        "# ========================================",
        "# Obsidian OpenAPI Server Configuration",
        "# ========================================",
        "",
        "# Server Configuration",
        f"OBSIDIAN_OPENAPI_PORT={config.get('port', 27150)}",
        f"OBSIDIAN_OPENAPI_HOST={config.get('host', '0.0.0.0')}",
        "",
        "# Obsidian REST API Configuration",
        f"OBSIDIAN_API_URL={config.get('obsidian_url', 'http://127.0.0.1:27123')}",
        f"OBSIDIAN_API_KEY={config.get('obsidian_key', '')}",
        "",
        "# Server API Authentication",
        f"SERVER_API_KEY={config.get('server_key', '')}",
        "",
        "# CORS Configuration",
        f"CORS_ORIGINS={config.get('cors', '*')}",
        "",
        "# Debug Mode",
        f"DEBUG={str(config.get('debug', False)).lower()}",
        "",
        "# Logging Level",
        f"LOG_LEVEL={config.get('log_level', 'INFO')}",
        "",
        "# History Configuration",
        f"MAX_HISTORY_ENTRIES={config.get('max_history', 10)}",
        "",
        "# Request Timeout",
        f"REQUEST_TIMEOUT={config.get('timeout', 30)}",
        "",
        "# Security",
        f"ENABLE_KEY_REGENERATION={str(config.get('key_regen', False)).lower()}",
        "",
    ]
    
    with open(env_path, "w") as f:
        f.write("\n".join(lines))
    
    return env_path


def main():
    """Main setup wizard."""
    print_header()
    
    # Check for existing config
    existing_config = {}
    if check_existing_env():
        questions = [
            inquirer.Confirm(
                "use_existing",
                message="An existing .env file was found. Use it as a base?",
                default=True,
            ),
        ]
        answers = inquirer.prompt(questions)
        if answers and answers["use_existing"]:
            existing_config = load_existing_config()
            print_info("Loaded existing configuration")
    
    print("\n" + Fore.CYAN + "--- Server Configuration ---" + Style.RESET_ALL + "\n")
    
    # Server port
    default_port = existing_config.get("OBSIDIAN_OPENAPI_PORT", "27150")
    questions = [
        inquirer.Text(
            "port",
            message="Server port",
            default=default_port,
            validate=lambda _, x: x.isdigit() and 1 <= int(x) <= 65535,
        ),
    ]
    answers = inquirer.prompt(questions)
    port = int(answers["port"]) if answers else 27150
    
    # Server host
    default_host = existing_config.get("OBSIDIAN_OPENAPI_HOST", "0.0.0.0")
    questions = [
        inquirer.List(
            "host",
            message="Server host binding",
            choices=[
                ("All interfaces (0.0.0.0) - Accessible from network", "0.0.0.0"),
                ("Localhost only (127.0.0.1) - Local access only", "127.0.0.1"),
            ],
            default=default_host,
        ),
    ]
    answers = inquirer.prompt(questions)
    host = answers["host"] if answers else "0.0.0.0"
    
    print("\n" + Fore.CYAN + "--- Obsidian Connection ---" + Style.RESET_ALL + "\n")
    
    # Obsidian URL
    default_url = existing_config.get("OBSIDIAN_API_URL", "http://127.0.0.1:27123")
    questions = [
        inquirer.Text(
            "obsidian_url",
            message="Obsidian REST API URL",
            default=default_url,
        ),
    ]
    answers = inquirer.prompt(questions)
    obsidian_url = answers["obsidian_url"] if answers else default_url
    
    # Obsidian API Key
    default_key = existing_config.get("OBSIDIAN_API_KEY", "")
    obsidian_key_prompt = "Obsidian API Key"
    if default_key:
        obsidian_key_prompt += f" ({len(default_key)} chars already set)"
    
    questions = [
        inquirer.Text(
            "obsidian_key",
            message=obsidian_key_prompt,
            default="" if not default_key else default_key[:10] + "...",
        ),
    ]
    answers = inquirer.prompt(questions)
    obsidian_key = answers["obsidian_key"] if answers else default_key
    if obsidian_key.endswith("...") and default_key:
        obsidian_key = default_key
    
    print("\n" + Fore.CYAN + "--- Server Security ---" + Style.RESET_ALL + "\n")
    
    # Server API Key
    default_server_key = existing_config.get("SERVER_API_KEY", "")
    if default_server_key:
        server_key_prompt = f"Server API Key ({len(default_server_key)} chars already set)"
    else:
        server_key_prompt = "Server API Key (leave blank to auto-generate)"
    
    questions = [
        inquirer.Text(
            "server_key",
            message=server_key_prompt,
            default="" if not default_server_key else default_server_key[:10] + "...",
        ),
    ]
    answers = inquirer.prompt(questions)
    server_key = answers["server_key"] if answers else default_server_key
    if server_key.endswith("...") and default_server_key:
        server_key = default_server_key
    
    if not server_key:
        server_key = generate_api_key()
        print_success(f"Auto-generated secure API key")
    
    print("\n" + Fore.CYAN + "--- Advanced Options ---" + Style.RESET_ALL + "\n")
    
    # Debug mode
    default_debug = existing_config.get("DEBUG", "false").lower() == "true"
    questions = [
        inquirer.Confirm(
            "debug",
            message="Enable debug mode?",
            default=default_debug,
        ),
    ]
    answers = inquirer.prompt(questions)
    debug = answers["debug"] if answers else False
    
    # History
    default_history = int(existing_config.get("MAX_HISTORY_ENTRIES", "10"))
    questions = [
        inquirer.List(
            "max_history",
            message="Max history entries (for rollback)",
            choices=[
                ("Disabled (0)", 0),
                ("5 entries", 5),
                ("10 entries (recommended)", 10),
                ("25 entries", 25),
                ("50 entries", 50),
            ],
            default=default_history,
        ),
    ]
    answers = inquirer.prompt(questions)
    max_history = answers["max_history"] if answers else 10
    
    # Key regeneration
    default_regen = existing_config.get("ENABLE_KEY_REGENERATION", "false").lower() == "true"
    questions = [
        inquirer.Confirm(
            "key_regen",
            message="Allow API key regeneration via API?",
            default=default_regen,
        ),
    ]
    answers = inquirer.prompt(questions)
    key_regen = answers["key_regen"] if answers else False
    
    # Build configuration
    config = {
        "port": port,
        "host": host,
        "obsidian_url": obsidian_url,
        "obsidian_key": obsidian_key,
        "server_key": server_key,
        "debug": debug,
        "max_history": max_history,
        "key_regen": key_regen,
        "cors": "*",
        "log_level": "DEBUG" if debug else "INFO",
        "timeout": 30,
    }
    
    print("\n" + Fore.CYAN + "--- Summary ---" + Style.RESET_ALL + "\n")
    
    # Show summary
    print(f"Server Port:     {port}")
    print(f"Server Host:     {host}")
    print(f"Obsidian URL:    {obsidian_url}")
    print(f"Obsidian Key:    {'*' * 10}... ({len(obsidian_key)} chars)")
    print(f"Server API Key:  {'*' * 10}... ({len(server_key)} chars)")
    print(f"Debug Mode:      {'Yes' if debug else 'No'}")
    print(f"History Entries: {max_history}")
    print(f"Key Regen:       {'Enabled' if key_regen else 'Disabled'}")
    
    print()
    
    # Confirm
    questions = [
        inquirer.Confirm(
            "confirm",
            message="Save this configuration?",
            default=True,
        ),
    ]
    answers = inquirer.prompt(questions)
    
    if answers and answers["confirm"]:
        env_path = save_config(config)
        print()
        print_success(f"Configuration saved to {env_path}")
        print()
        print(Fore.GREEN + "=" * 60)
        print(Fore.GREEN + "  Setup complete! You can now start the server:")
        print()
        print(Fore.WHITE + "    python -m app.main")
        print()
        print(Fore.GREEN + "  Or with auto-reload for development:")
        print()
        print(Fore.WHITE + "    python -m app.main --reload")
        print()
        print(Fore.GREEN + "  Your API Key (save this securely):")
        print()
        print(Fore.YELLOW + f"    {server_key}")
        print()
        print(Fore.GREEN + "=" * 60)
        print()
    else:
        print()
        print_warning("Setup cancelled. No changes were made.")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Setup interrupted. No changes were made.")
        print()
        sys.exit(0)