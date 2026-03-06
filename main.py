from utils.logger import setup_logger, get_logger
from src.read_json import read_json
from src.drone_simulator import DroneSimulator
import logging
import os

setup_logger(level=logging.DEBUG, console_level=logging.INFO,enable_console=True, enable_file=False)

logger = get_logger("DroneSimulator")


def main(drone_id,data):
    waypoints = [(wp["lat"], wp["lon"], wp["alt"]) for wp in data]
    drone_simulator = DroneSimulator(drone_id=drone_id,waypoints=waypoints)
    drone_simulator.run()

if __name__ == "__main__":
    drone_id = os.getenv("DRONE_ID", "0")
    data = read_json('utils/mission_dahiyeh.json')
    main(drone_id,data)