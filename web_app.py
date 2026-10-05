#!/usr/bin/env python
"""Entrypoint launcher script for AutoCompliant-ML FastAPI Stepper Wizard Dashboard."""

import argparse
import sys
import uvicorn


def main():
    parser = argparse.ArgumentParser(
        description="AutoCompliant-ML Interactive Stepper Wizard Dashboard Launcher"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host address to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (default: 8000)"
    )
    parser.add_argument(
        "--reload", action="store_true", default=False, help="Enable auto-reload on code change"
    )
    args = parser.parse_args()

    print("\n" + "=" * 68)
    print(" ⚙️  AutoCompliant-ML Guided Stepper Wizard Dashboard")
    print(f" 🌐 Dashboard URL: http://localhost:{args.port}")
    print(f" 📚 Swagger Docs:  http://localhost:{args.port}/docs")
    print("=" * 68 + "\n")

    uvicorn.run(
        "autocompliant.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
