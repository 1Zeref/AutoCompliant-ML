#!/usr/bin/env python
"""Launcher script for AutoCompliant-ML Web Dashboard."""

import uvicorn

if __name__ == "__main__":
    print("Starting AutoCompliant-ML Interactive Dashboard on http://localhost:8000 ...")
    uvicorn.run("autocompliant.web.app:app", host="0.0.0.0", port=8000, reload=False)
