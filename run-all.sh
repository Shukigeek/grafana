#!/bin/bash

# --- Names ---
NETWORK_NAME=monitoring
LOKI_CONTAINER=loki
GRAFANA_CONTAINER=grafana
LOKI_VOLUME=loki-data
GRAFANA_VOLUME=grafana-data

# --- Create network if it doesn't exist ---
if ! docker network ls | grep -q "$NETWORK_NAME"; then
  echo "Creating network $NETWORK_NAME..."
  docker network create $NETWORK_NAME
else
  echo "Network $NETWORK_NAME already exists."
fi

# --- Remove existing containers if they exist ---
for CONTAINER in $LOKI_CONTAINER $GRAFANA_CONTAINER; do
  if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER$"; then
    echo "Removing existing container: $CONTAINER"
    docker rm -f $CONTAINER
  fi
done

# --- Create volumes if they don't exist ---
for VOLUME in $LOKI_VOLUME $GRAFANA_VOLUME; do
  if ! docker volume ls | grep -q "$VOLUME"; then
    echo "Creating volume: $VOLUME"
    docker volume create $VOLUME
  fi
done

# --- Run Loki ---
echo "Starting Loki..."
docker run -d \
  --name $LOKI_CONTAINER \
  --network $NETWORK_NAME \
  -p 3100:3100 \
  -v $LOKI_VOLUME:/loki \
  grafana/loki:2.9.0

# --- Run Grafana ---
echo "Starting Grafana..."
docker run -d \
  --name $GRAFANA_CONTAINER \
  --network $NETWORK_NAME \
  -p 3000:3000 \
  -v $GRAFANA_VOLUME:/var/lib/grafana \
  -v $(pwd)/dashboards:/etc/grafana/provisioning/dashboards \
  -v $(pwd)/provisioning:/etc/grafana/provisioning \
  grafana/grafana:latest

echo "All set! Grafana is running at: http://localhost:3000"

echo "Waiting for Grafana to respond..."

until curl -s http://localhost:3000 > /dev/null; do
  sleep 1
done

echo "Opening in Google Chrome..."
"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" http://localhost:3000 & http://localhost:3000 >/dev/null 2>&1 &