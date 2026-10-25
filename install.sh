#!/bin/bash
read -p "Enter desired web port (default 8080): " PORT
PORT=${PORT:-8080}
echo "WEB_PORT=$PORT" > .env
mkdir -p data
docker compose up -d --build
echo "Installation complete. The dashboard is running on port $PORT."