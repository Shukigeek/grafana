import logging
from typing import List, Optional, Tuple
from src.models.gps_point import GPSPoint


class MissionSubsystem:
    def __init__(self, drone_id: str, waypoints: List[Tuple[float, float, float]]):
        self.log      = logging.getLogger(f"DroneSimulator.{drone_id}.Mission")
        self.waypoints: List[GPSPoint] = []
        self.index    = 0

        self._load(waypoints)

    def current(self) -> Optional[GPSPoint]:
        if self.index < len(self.waypoints):
            return self.waypoints[self.index]
        return None

    def advance(self) -> None:
        prev = self.index
        self.index += 1
        self.log.info(
            f"Waypoint advanced  {prev} → {self.index}  "
            f"(total={len(self.waypoints)})"
        )

    def is_complete(self) -> bool:
        return self.index >= len(self.waypoints)

    def progress_pct(self) -> float:
        if len(self.waypoints) <= 1:
            return 100.0
        return min(100.0, self.index / (len(self.waypoints) - 1) * 100.0)

    def total(self) -> int:
        return len(self.waypoints)

    def _load(self, waypoints: List[Tuple[float, float, float]]) -> None:
        if not waypoints:
            raise ValueError("Waypoint list must not be empty")
        self.waypoints = [GPSPoint(lat, lon, alt) for lat, lon, alt in waypoints]
        self.log.info(f"📋 Mission loaded  total_waypoints={len(self.waypoints)}")
        for i, wp in enumerate(self.waypoints):
            self.log.info(f"    WP[{i:02d}] {wp}")