#!/usr/bin/env python3
"""
Convenience startup script for Obsidian OpenAPI Server.

This script provides a simple way to start the server without
remembering the exact module path.

Usage:
    python start.py              # Start with .env config
    python start.py --setup      # Run setup wizard first
    python start.py --help       # Show all options
"""

import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        return True
    except ImportError:
        return False


def install_dependencies():
    """Install dependencies from requirements.txt."""
    print("Installing dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=False,
    )
    return result.returncode == 0


def run_setup():
    """Run the interactive setup wizard."""
    print("Running setup wizard...")
    subprocess.run([sys.executable, "scripts/setup.py"])


def start_server():
    """Start the server."""
    import uvicorn
    
    print("=" * 60)
    print("  Starting Obsidian OpenAPI Server")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=27150,
        reload=False,
    )


def main():
    """Main entry point."""
    # Check for --setup flag
    if "--setup" in sys.argv:
        run_setup()
        return
    
    # Check for --help flag
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print()
        print("Additional options are passed to uvicorn:")
        print("  --reload          Enable auto-reload")
        print("  --port PORT       Use different port")
        print("  --host HOST       Use different host")
        print()
        return
    
    # Check dependencies
    if not check_dependencies():
        print("Dependencies not installed.")
        response = input("Install now? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes"):
            if not install_dependencies():
                print("Failed to install dependencies.")
                sys.exit(1)
        else:
            print("Cannot start without dependencies.")
            sys.exit(1)
    
    # Check if .env exists
    if not Path(".env").exists():
        print("No configuration file found (.env)")
        response = input("Run setup wizard? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes"):
            run_setup()
            # Ask if they want to start now
            response = input("\nStart server now? [Y/n]: ").strip().lower()
            if response not in ("", "y", "yes"):
                return
        else:
            print("Creating minimal configuration...")
            print("Please edit .env file and add your Obsidian API key.")
            Path(".env").write_text(
                "OBSIDIAN_API_KEY=your-obsidian-api-key-here\n"
                "OBSIDIAN_API_URL=http://127.0.0.1:27123\n"
            )
            sys.exit(1)
    
    # Start the server
    try:
        start_server()
    except KeyboardInterrupt:
        print()
        print("\nServer stopped.")


if __name__ == "__main__":
    main()