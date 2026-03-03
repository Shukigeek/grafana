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
"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" http://localhost:3000/d/adb4rpm/sardin?orgId=1&from=now-15m&to=now&timezone=browser&refresh=auto & http://localhost:3000/d/adb4rpm/sardin?orgId=1&from=now-15m&to=now&timezone=browser&refresh=auto >/dev/null 2>&1 &


# --- Read drone count from pram.json ---
if [ ! -f pram.json ]; then
  echo "pram.json not found!"
  exit 1
fi

DRONE_COUNT=$(grep -oP '"number_of_drones"\s*:\s*\K[0-9]+' pram.json)

if [ -z "$DRONE_COUNT" ]; then
  echo "Could not read number_of_drones from pram.json"
  exit 1
fi

echo "Starting $DRONE_COUNT drone containers..."

# --- Run drone containers ---
for (( i=1; i<=DRONE_COUNT; i++ ))
do
  CONTAINER_NAME="drone$i"

  if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "Removing existing container: $CONTAINER_NAME"
    docker rm -f $CONTAINER_NAME
  fi

  echo "Starting $CONTAINER_NAME with ID=$i"

  docker run -d \
    --name $CONTAINER_NAME \
    --network $NETWORK_NAME \
    -e DRONE_ID=$i \
    drone

done

echo "All drones started successfully 🚁"