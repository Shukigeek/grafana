#!/bin/bash
set -e

# Load .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

TOKEN="$GRAFANA_TOKEN"
DASHBOARDS=(adb4rpm)
mkdir -p dashboards

for DASH_UID in "${DASHBOARDS[@]}"; do
  echo "Syncing dashboard $DASH_UID..."

  # Download raw JSON
  curl -s -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" \
       "http://localhost:3000/api/dashboards/uid/$DASH_UID" \
       | jq '.' > "dashboards/$DASH_UID.json"

  echo "Saved dashboards/$DASH_UID.json"
done