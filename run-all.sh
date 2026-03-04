#!/bin/bash

# --- Names ---
NETWORK_NAME=monitoring
LOKI_CONTAINER=loki
GRAFANA_CONTAINER=grafana
OPENSEARCH_CONTAINER=opensearch
PROMTAIL=promtail
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
for CONTAINER in $LOKI_CONTAINER $GRAFANA_CONTAINER $OPENSEARCH_CONTAINER $PROMTAIL; do
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


# --- Run Promtail ---
docker run -d \
  --name promtail \
  --network monitoring \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/promtail-config.yaml:/etc/promtail/config.yaml \
  grafana/promtail:latest -config.file=/etc/promtail/config.yaml

# --- Run Grafana ---
echo "Starting Grafana..."
docker run -d \
  --name $GRAFANA_CONTAINER \
  --network $NETWORK_NAME \
  -p 3000:3000 \
  -v $GRAFANA_VOLUME:/var/lib/grafana \
  -v $(pwd)/dashboards:/etc/grafana/dashboards \
  -v $(pwd)/provisioning:/etc/grafana/provisioning \
  grafana/grafana:latest

## -- Run Opensearch --
#echo "Starting Opensearch..."
#docker run -d --name $OPENSEARCH_CONTAINER -p 9200:9200 -p 9600:9600 \
#  --network $NETWORK_NAME \
#  -e "discovery.type=single-node" \
#  -e "DISABLE_SECURITY_PLUGIN=true" \
#  --user 1000:1000 \
#  opensearchproject/opensearch:2.10.0

echo "All set! Grafana is running at: http://localhost:3000"

echo "Waiting for Grafana to respond..."

until curl -s http://localhost:3000 > /dev/null; do
  sleep 1
done

echo "Opening in Google Chrome..."
"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" http://localhost:3000/d/adb4rpm/sardin?orgId=1&from=now-15m&to=now&timezone=browser&refresh=auto & http://localhost:3000/d/adb4rpm/sardin?orgId=1&from=now-15m&to=now&timezone=browser&refresh=auto >/dev/null 2>&1 &


# --- Read drone count from pram.json ---
if [ ! -f utils/pram.json ]; then
  echo "pram.json not found!"
  exit 1
fi

DRONE_COUNT=$(grep -oP '"number_of_drones"\s*:\s*\K[0-9]+' utils/pram.json)

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
    -v $(pwd)/logs_files/logs:/app/logs \
    drone

done

echo "All drones started successfully 🚁"