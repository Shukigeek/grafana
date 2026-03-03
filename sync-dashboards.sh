TOKEN="$GRAFANA_TOKEN"
DASHBOARDS=(adb4rpm)

for DASH_UID in "${DASHBOARDS[@]}"; do
  curl -s -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" \
       "http://localhost:3000/api/dashboards/uid/$DASH_UID" \
       > "dashboards/$DASH_UID.json"
done