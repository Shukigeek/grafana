import random
import time
import json
from utils.logger import logger
from src.read_json import read_json


class SimulatedFlight:
    def __init__(self, drone_id, cities_json_path,pram_json_path):
        self.drone_id = drone_id
        self.track = []
        self.city_coordinates = []
        try:
            self.city_coordinates = read_json(cities_json_path)
            self.pram = read_json(pram_json_path)
            logger.info(f"Loaded {len(self.city_coordinates)} cities from {cities_json_path}")
        except Exception as e:
            logger.error(f"Failed to read JSON from {cities_json_path}: {e}")

        self.city = self.get_random_city()
        self.max_points = self.get_number_of_points()

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
            return 50

    def simulate_takeoff(self):
        logger.info(f"Drone {self.drone_id} taking off from {self.city['city']}")
        altitude = 0
        for _ in range(5):
            altitude += random.uniform(5, 15)
            lat = self.city["lat"] + random.uniform(-0.0002, 0.0002)
            lon = self.city["lon"] + random.uniform(-0.0002, 0.0002)
            self.track.append({"lat": lat, "lon": lon, "alt": round(altitude, 1)})
            logger.debug(f"Takeoff point: lat={lat:.6f}, lon={lon:.6f}, alt={altitude:.1f}")
            time.sleep(0.1)

    def flying_over_forbidden_city(self, lat, lon, city_name, delta):
        try:
            city = next((c for c in self.city_coordinates if c["city"] == city_name), None)
            if not city:
                logger.warning(f"City {city_name} not found in coordinates")
                return False

            city_lat = city["lat"]
            city_lon = city["lon"]

            if (city_lat - delta) <= lat <= (city_lat + delta) and (city_lon - delta) <= lon <= (city_lon + delta):
                logger.debug(f"Drone {self.drone_id} is over forbidden city {city_name}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error checking forbidden city: {e}")
            return False

    def simulate_flight(self):
        logger.info(f"Drone {self.drone_id} en route")
        for i in range(self.max_points):
            last_point = self.track[-1]
            lat = last_point["lat"] + random.uniform(-0.0005, 0.0005)
            lon = last_point["lon"] + random.uniform(-0.0005, 0.0005)
            alt = last_point["alt"] + random.uniform(-1, 1)
            self.track.append({"lat": lat, "lon": lon, "alt": round(alt, 1)})
            logger.debug(f"Flight point {i}: lat={lat:.6f}, lon={lon:.6f}, alt={alt:.1f}")

            city_name = self.pram.get("forbidden_city", "Unknown")
            delta = self.pram.get("delta", 0.002)

            if self.flying_over_forbidden_city(lat, lon, city_name,delta):
                logger.warning(f"Drone {self.drone_id} initiating emergency landing over Jerusalem!")
                self.simulate_emergency_landing(lat, lon)
                break

            time.sleep(0.05)

    def simulate_emergency_landing(self, lat, lon):
        altitude = self.track[-1]["alt"]
        while altitude > 0:
            altitude -= random.uniform(2, 5)
            if altitude < 0:
                altitude = 0
            self.track.append({"lat": lat, "lon": lon, "alt": round(altitude, 1)})
            logger.error(f"Emergency landing: lat={lat:.6f}, lon={lon:.6f}, alt={altitude:.1f}")
            time.sleep(0.05)
        logger.info(f"Drone {self.drone_id} safely landed in emergency mode")

    def simulate_landing(self):
        if self.track[-1]["alt"] > 0:
            logger.info(f"Drone {self.drone_id} performing normal landing")
            altitude = self.track[-1]["alt"]
            lat = self.track[-1]["lat"]
            lon = self.track[-1]["lon"]
            while altitude > 0:
                altitude -= random.uniform(2, 5)
                if altitude < 0:
                    altitude = 0
                self.track.append({"lat": lat, "lon": lon, "alt": round(altitude, 1)})
                logger.debug(f"Landing point: lat={lat:.6f}, lon={lon:.6f}, alt={altitude:.1f}")
                time.sleep(0.05)
            logger.info(f"Drone {self.drone_id} safely landed")

    def run_simulation(self):
        try:
            self.simulate_takeoff()
            self.simulate_flight()
            self.simulate_landing()
            logger.info(f"Drone {self.drone_id} flight simulation completed, total points: {len(self.track)}")
        except Exception as e:
            logger.error(f"Simulation failed for drone {self.drone_id}: {e}")

    def save_track_to_file(self, filename):
        try:
            with open(filename, "a", encoding="utf-8") as f:
                for point in self.track:
                    f.write(json.dumps({"drone_id": self.drone_id, **point}) + "\n")
            logger.info(f"Flight track saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save track to {filename}: {e}")