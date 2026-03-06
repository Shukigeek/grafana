from dataclasses import dataclass , field
from typing import List

from src.models.gps_point import GPSPoint

@dataclass
class Telemetry:
    timestamp: str
    drone_id: str
    state: str
    position: GPSPoint
    heading: float          # degrees 0-360
    speed_mps: float        # m/s
    altitude_agl: float     # m above ground level
    battery_pct: float
    gps_fix: int            # 0=no fix, 1=2D, 2=3D, 3=RTK
    satellites: int
    link_latency_ms: float
    uplink_kbps: float
    downlink_kbps: float
    current_waypoint_idx: int
    mission_progress_pct: float
    distance_to_wp_m: float
    distance_to_home_m: float
    events: List[str] = field(default_factory=list)

