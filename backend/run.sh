#!/bin/bash

echo "Starting FastAPI backend server..."
echo ""

uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload

