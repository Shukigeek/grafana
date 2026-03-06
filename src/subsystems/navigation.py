"""
subsystems/navigation.py – Position, heading, distance calculations
"""

import math
import logging
from src.models.gps_point import GPSPoint
from src.models.simulation_config import SimulationConfig


class NavigationSubsystem:
    def __init__(self, drone_id: str, home: GPSPoint, config: SimulationConfig):
        self.log     = logging.getLogger(f"DroneSimulator.{drone_id}.Nav")
        self.config  = config

        self.position     = GPSPoint(home.lat, home.lon, home.alt)
        self.home         = GPSPoint(home.lat, home.lon, home.alt)
        self.heading      = 0.0
        self.speed_mps    = 0.0
        self.altitude_agl = 0.0

    def move_towards(self, wp: GPSPoint, wp_index: int) -> None:
        dist = self.distance_to(wp)
        step = min(
            self.config.CRUISE_SPEED_MPS * self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S,
            dist,
        )
        if dist < 1e-6:
            return

        fraction = step / dist
        self.position.lat += (wp.lat - self.position.lat) * fraction
        self.position.lon += (wp.lon - self.position.lon) * fraction
        self.position.alt  = wp.alt
        self.speed_mps     = self.config.CRUISE_SPEED_MPS
        self.heading       = self._bearing_to(wp)

        self.log.debug(
            f"Moved {step:.1f}m → WP[{wp_index}]  "
            f"remaining={dist - step:.1f}m  "
            f"hdg={self.heading:.1f}°  pos={self.position}"
        )

    def climb(self, target_alt: float) -> bool:
        """Climb one tick. Returns True when target altitude is reached."""
        step = self.config.TAKEOFF_SPEED_MPS * self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S
        self.altitude_agl = min(self.altitude_agl + step, target_alt)
        self.speed_mps    = self.config.TAKEOFF_SPEED_MPS
        self.log.debug(f"Climbing  AGL={self.altitude_agl:.1f}m / target={target_alt:.1f}m")
        return self.altitude_agl >= target_alt

    def descend(self) -> bool:
        """Descend one tick. Returns True when landed (AGL == 0)."""
        step = self.config.LANDING_SPEED_MPS * self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S
        self.altitude_agl = max(0.0, self.altitude_agl - step)
        self.speed_mps    = self.config.LANDING_SPEED_MPS if self.altitude_agl > 0 else 0.0
        self.log.debug(f"Descending  AGL={self.altitude_agl:.1f}m")
        return self.altitude_agl == 0.0

    def distance_to(self, wp: GPSPoint) -> float:
        return self._haversine(self.position, wp)

    def distance_to_home(self) -> float:
        return self._haversine(self.position, self.home)

    def reached(self, wp: GPSPoint) -> bool:
        dist = self.distance_to(wp)
        if dist <= self.config.WAYPOINT_REACH_RADIUS_M:
            self.log.debug(f"Waypoint reached  dist={dist:.2f}m")
            return True
        return False

    def _bearing_to(self, wp: GPSPoint) -> float:
        dlat = wp.lat - self.position.lat
        dlon = wp.lon - self.position.lon
        return math.degrees(math.atan2(dlon, dlat)) % 360

    def _haversine(self, a: GPSPoint, b: GPSPoint) -> float:
        lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
        lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * self.config.EARTH_RADIUS_M * math.asin(math.sqrt(h))