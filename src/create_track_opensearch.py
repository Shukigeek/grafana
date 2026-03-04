from utils.logger import logger
from src.read_json import read_json
import random
import time
from opensearchpy import OpenSearch

class CreateTrackOpensearch:
    def __init__(self, path, os_host, drone_id):
        self.os = OpenSearch(
            hosts=[os_host],
            http_compress=True,
            use_ssl=False,
            verify_certs=False
        )
        self.id = drone_id
        self.city_coordinates = []
        try:
            self.city_coordinates = read_json(path)
            logger.info(f"Loaded {len(self.city_coordinates)} cities from {path}")
        except Exception as e:
            logger.error(f"Failed to read JSON from {path}: {e}")

    def wait_for_connection(self, timeout=60):
        logger.info("Waiting for OpenSearch connection...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if self.os.ping():
                    logger.info("Connected to OpenSearch!")
                    return True
            except Exception:
                pass

            logger.info("OpenSearch not ready, retrying...")
            time.sleep(2)

        raise TimeoutError("OpenSearch did not become ready in time")

    def get_random_city(self):
        if not self.city_coordinates:
            return {"city": "Unknown", "lat": 0.0, "lon": 0.0}
        return random.choice(self.city_coordinates)

    def get_number_of_points(self):
        return random.randint(30, 100)

    def get_flight_track(self):
        number_of_points = self.get_number_of_points()
        city = self.get_random_city()
        lat = city.get("lat", 0.0)
        lon = city.get("lon", 0.0)

        track = [[lat, lon]]
        for _ in range(number_of_points):
            lat += random.uniform(-0.0005, 0.0005)
            lon += random.uniform(-0.0005, 0.0005)
            track.append([lat, lon])
        return track

    def publish_to_opensearch(self, index="drones"):
        self.wait_for_connection()
        track = self.get_flight_track()
        if not track:
            logger.warning("No track to publish")
            return

        for coord in track:
            lat, lon = coord[0], coord[1]
            doc = {
                "drone_id": str(self.id),
                "location": {"lat": lat, "lon": lon},
                "timestamp": int(time.time() * 1000)
            }
            try:
                self.os.index(index=index, body=doc)
            except Exception as e:
                logger.error(f"Failed to send coordinate {coord} to Elasticsearch: {e}")