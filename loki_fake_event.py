import requests
import time
import json
import random

url = "http://localhost:3100/loki/api/v1/push"


lat = 31.7683
lon = 35.2137

points_count = 120  # יותר מ-100 נקודות

while True:
    for _ in range(points_count):
        # תזוזה קטנה רנדומלית (תנועה חלקה)
        lat += random.uniform(-0.0005, 0.0005)
        lon += random.uniform(-0.0005, 0.0005)

        now_ns = int(time.time() * 1e9)

        log_line = json.dumps({
            "lat": round(lat, 6),
            "lon": round(lon, 6)
        })

        payload = {
            "streams": [
                {
                    "stream": {"sensor": "GPS"},
                    "values": [[str(now_ns), log_line]]
                }
            ]
        }

        requests.post(url, json=payload)
        print(log_line)

        time.sleep(1)