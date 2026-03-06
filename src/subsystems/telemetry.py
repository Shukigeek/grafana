import logging
from datetime import datetime, timezone
from typing import List
from src.models.gps_point import GPSPoint
from src.models.telemetry import Telemetry


class TelemetrySubsystem:
    def __init__(self, drone_id: str):
        self.log      = logging.getLogger(f"DroneSimulator.{drone_id}.Telemetry")
        self.drone_id = drone_id
        self.history: List[Telemetry] = []

    def build_and_send(
        self,
        *,
        state,
        nav,
        gps,
        link,
        mission,
        tick_events: list,
    ) -> Telemetry:
        t = Telemetry(
            timestamp            = datetime.now(timezone.utc).isoformat(),
            drone_id             = self.drone_id,
            state                = state.name,
            position             = GPSPoint(nav.position.lat, nav.position.lon, nav.position.alt),
            heading              = nav.heading,
            speed_mps            = nav.speed_mps,
            altitude_agl         = nav.altitude_agl,
            battery_pct          = 0.0,
            gps_fix              = gps.fix.value,
            satellites           = gps.satellites,
            link_latency_ms      = link.latency_ms,
            uplink_kbps          = link.uplink_kbps,
            downlink_kbps        = link.downlink_kbps,
            current_waypoint_idx = mission.index,
            mission_progress_pct = mission.progress_pct(),
            distance_to_wp_m     = nav.distance_to(mission.current()) if mission.current() else 0.0,
            distance_to_home_m   = nav.distance_to_home(),
            events               = list(tick_events),
        )
        self.history.append(t)
        self._log(t, mission.total())
        return t

    def event_counts(self) -> dict:
        counts: dict = {}
        for t in self.history:
            for ev in t.events:
                counts[ev] = counts.get(ev, 0) + 1
        return counts

    def _log(self, t: Telemetry, total_wps: int) -> None:
        events_part = f" | EVENTS={t.events}" if t.events else ""
        msg = (
            f"TEL"
            f" | state={t.state:<10}"
            f" | pos={t.position}"
            f" | hdg={t.heading:>6.1f}°"
            f" | spd={t.speed_mps:>5.1f}m/s"
            f" | AGL={t.altitude_agl:>6.1f}m"
            f" | bat={t.battery_pct:>5.1f}%"
            f" | gps={t.gps_fix}({t.satellites}sv)"
            f" | latency={t.link_latency_ms:>6.1f}ms"
            f" | UL={t.uplink_kbps:>7.1f}kbps"
            f" | DL={t.downlink_kbps:>8.1f}kbps"
            f" | wp={t.current_waypoint_idx}/{total_wps} ({t.mission_progress_pct:.1f}%)"
            f" | d2wp={t.distance_to_wp_m:>8.1f}m"
            f" | d2home={t.distance_to_home_m:>8.1f}m"
            f"{events_part}"
        )
        self.log.info(msg)