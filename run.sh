#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run FastAPI with Uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
