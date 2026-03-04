from utils.logger import logger
from src.read_json import read_json
import random
import time
import requests
import json


class CreateTrack:
    def __init__(self, path, url,id):
        self.url = url
        self.id = id
        self.city_coordinates = []
        try:
            self.city_coordinates = read_json(path)
            logger.info(f"Loaded {len(self.city_coordinates)} cities from {path}")
        except Exception as e:
            logger.error(f"Failed to read JSON from {path}: {e}")

    def get_random_city(self):
        try:
            if not self.city_coordinates:
                raise ValueError("City coordinates list is empty")
            city = random.choice(self.city_coordinates)
            logger.debug(f"Random city selected: {city}")
            return city
        except Exception as e:
            logger.error(f"Failed to get random city: {e}")
            return {"city": "Unknown", "lat": 0.0, "lon": 0.0}

    def get_number_of_points(self):
        try:
            number_of_points = random.randint(50, 150)
            logger.debug(f"Number of points: {number_of_points}")
            return number_of_points
        except Exception as e:
            logger.error(f"Failed to generate number of points: {e}")
            return 30

    def get_flight_track(self):
        try:
            number_of_points = self.get_number_of_points()
            city = self.get_random_city()
            lat = city.get("lat", 0.0)
            lon = city.get("lon", 0.0)

            track = [[lat, lon]]
            for _ in range(number_of_points):
                lat += random.uniform(-0.0005, 0.0005)
                lon += random.uniform(-0.0005, 0.0005)
                track.append([lat, lon])
            logger.info(f"Generated flight track with {len(track)} points from city {city.get('city')}")
            return track
        except Exception as e:
            logger.error(f"Failed to generate flight track: {e}")
            return []

    def publish_to_loki(self):
        try:
            track = self.get_flight_track()
            if not track:
                logger.warning("No track to publish")
                return

            for coord in track:
                try:
                    lat, lon = coord[0], coord[1]
                    now_ns = int(time.time() * 1e9)

                    log_line = json.dumps({
                        "lat": round(lat, 6),
                        "lon": round(lon, 6)
                    })

                    payload = {
                        "streams": [
                            {
                                "stream": {
                                    "sensor": "GPS",
                                    "drone_id": str(self.id)
                                },
                                "values": [
                                    [str(now_ns), log_line]
                                ]
                            }
                        ]
                    }
                    time.sleep(random.randint(1, 5))
                    response = requests.post(self.url, json=payload)
                    if response.status_code not in (200, 204):
                        logger.warning(f"Loki POST returned {response.status_code}: {response.text}")

                except Exception as e:
                    logger.error(f"Failed to send coordinate {coord}: {e}")

        except Exception as e:
            logger.error(f"Failed to publish track to Loki: {e}")