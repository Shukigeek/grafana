import math
import time
import random
import logging
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from src.models.flight_state import FlightState
from src.models.gps_fix_type import GPSFixType
from src.models.gps_point import GPSPoint
from src.models.link_state import LinkState
from src.models.simulation_config import SimulationConfig
from src.models.telemetry import Telemetry



# ---------------------------------------------------------------------------
# DroneSimulator
# ---------------------------------------------------------------------------

class DroneSimulator:
    """
    Full drone flight simulator.

    Parameters
    ----------
    drone_id  : str         – unique identifier for this drone
    waypoints : list[tuple] – list of (lat, lon, alt) tuples
    """

    def __init__(self, drone_id: str, waypoints: List[Tuple[float, float, float]]):
        self.log = logging.getLogger(f"DroneSimulator.{drone_id}")
        self.log.info(f"Initialising drone  ID={drone_id}")

        self.config = SimulationConfig()
        self.drone_id   = drone_id
        self.state      = FlightState.IDLE
        self._running   = False

        # Mission
        self.mission: List[GPSPoint] = []
        self.wp_index   = 0
        self.load_mission(waypoints)

        # Position – start at home (first waypoint, on the ground)
        home = self.mission[0]
        self.position   = GPSPoint(home.lat, home.lon, home.alt)
        self.home       = GPSPoint(home.lat, home.lon, home.alt)
        self.target_alt = 0.0

        # Kinematics
        self.heading        = 0.0
        self.speed_mps      = 0.0
        self.altitude_agl   = 0.0

        # Power
        self.battery_pct    = 100.0

        # GPS
        self.gps_fix        = GPSFixType.THREE_D_FIX
        self.satellites     = random.randint(10, 14)
        self.gps_lost       = False

        # RF link
        self.link_state     = LinkState.NOMINAL
        self.link_latency   = 30.0      # ms
        self.uplink_kbps    = 500.0
        self.downlink_kbps  = 2000.0

        # Timing
        self.sim_time       = 0.0       # simulated seconds
        self.takeoff_time   = 0.0
        self.loiter_start   = 0.0

        # Telemetry buffer
        self._telemetry_log: List[Telemetry] = []

        # Active event descriptions this tick
        self._tick_events: List[str] = []

        self.log.info(
            f"Home position: {self.home}  "
            f"| Waypoints: {len(self.mission)}  "
            f"| Battery: {self.battery_pct:.1f}%"
        )
        self.log.info("=" * 60)

    # -----------------------------------------------------------------------
    # MAIN LOOP
    # -----------------------------------------------------------------------

    def run(self):
        """Blocking entry-point – runs the full mission to completion."""
        self.log.info("Starting subsystems run")
        self._running = True
        self.state = FlightState.TAKEOFF

        try:
            while self._running:
                self.update()
                time.sleep(self.config.SIM_TICK_S)
        except KeyboardInterrupt:
            self.log.warning("⚠  Simulation interrupted by user")
        finally:
            self._running = False
            self.log.info("■  Simulation stopped")
            self._print_summary()

    def update(self):
        """Single subsystems tick – advances sim time and dispatches to state handler."""
        dt = self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S
        self.sim_time += dt
        self._tick_events = []

        self.log.debug(
            f"── tick  sim_time={self.sim_time:.1f}s  state={self.state.name}  "
            f"battery={self.battery_pct:.1f}%"
        )

        # Drain battery
        drain = self.config.BATTERY_DRAIN_PER_SEC * dt
        self.battery_pct = max(0.0, self.battery_pct - drain)
        if self.battery_pct < 20.0:
            self.log.warning(f"🔋 LOW BATTERY  {self.battery_pct:.1f}%")
        if self.battery_pct == 0.0:
            self.log.critical("💀 BATTERY DEPLETED – forcing landing")
            self.state = FlightState.LANDING

        # Sub-system simulations
        self.simulate_gps_signal()
        self.simulate_link_state()
        self.generate_random_event()

        # State dispatcher
        dispatch = {
            FlightState.TAKEOFF  : self.simulate_takeoff,
            FlightState.MISSION  : self.simulate_mission,
            FlightState.LOITER   : self.simulate_loiter,
            FlightState.LANDING  : self.simulate_landing,
            FlightState.LOST     : self.simulate_lost_mode,
            FlightState.LANDED   : self._handle_landed,
            FlightState.IDLE     : lambda: None,
        }
        dispatch[self.state]()

        # Send telemetry every tick
        self.send_telemetry()

    # -----------------------------------------------------------------------
    # FLIGHT STATES
    # -----------------------------------------------------------------------

    def simulate_takeoff(self):
        log_t = logging.getLogger(f"DroneSimulator.{self.drone_id}.Takeoff")
        cruise_alt = self.mission[1].alt if len(self.mission) > 1 else 50.0
        self.target_alt = cruise_alt

        climb_step = self.config.TAKEOFF_SPEED_MPS * self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S
        self.altitude_agl += climb_step
        self.speed_mps = self.config.TAKEOFF_SPEED_MPS

        log_t.debug(
            f"Climbing  AGL={self.altitude_agl:.1f}m / target={self.target_alt:.1f}m  "
            f"v_climb={self.config.TAKEOFF_SPEED_MPS:.1f}m/s"
        )

        if self.altitude_agl >= cruise_alt:
            self.altitude_agl = cruise_alt
            self.takeoff_time = self.sim_time
            log_t.info(
                f"✅ Takeoff complete  AGL={self.altitude_agl:.1f}m  "
                f"time_to_alt={self.sim_time:.1f}s"
            )
            self.state = FlightState.MISSION

    def simulate_mission(self):
        log_m = logging.getLogger(f"DroneSimulator.{self.drone_id}.Mission")

        if self.wp_index >= len(self.mission):
            log_m.info("🏁 All waypoints reached – transitioning to LANDING")
            self.state = FlightState.LANDING
            return

        wp = self.current_waypoint()
        dist = self.calculate_distance_to_waypoint()

        log_m.debug(
            f"Flying to WP[{self.wp_index}/{len(self.mission)-1}]  "
            f"target={wp}  dist={dist:.1f}m  "
            f"progress={self.mission_progress():.1f}%"
        )

        self.move_towards_waypoint()

        if self.reached_waypoint():
            log_m.info(
                f"📍 Reached WP[{self.wp_index}]  pos={self.position}  "
                f"mission_progress={self.mission_progress():.1f}%"
            )
            self.advance_waypoint()

            if self.wp_index < len(self.mission):
                log_m.info(
                    f"➡  Next WP[{self.wp_index}] = {self.current_waypoint()}  "
                    f"heading={self.heading:.1f}°"
                )
                # Short loiter at each waypoint
                log_m.info("⏸  Entering LOITER at waypoint")
                self.loiter_start = self.sim_time
                self.state = FlightState.LOITER

    def simulate_loiter(self):
        log_l = logging.getLogger(f"DroneSimulator.{self.drone_id}.Loiter")
        elapsed = self.sim_time - self.loiter_start
        self.speed_mps = 0.0

        log_l.debug(f"Loitering  elapsed={elapsed:.1f}s / {self.config.LOITER_DURATION_S:.0f}s")

        if elapsed >= self.config.LOITER_DURATION_S:
            log_l.info(
                f"✅ Loiter complete after {elapsed:.1f}s – resuming MISSION"
            )
            if self.wp_index >= len(self.mission):
                self.state = FlightState.LANDING
            else:
                self.state = FlightState.MISSION

    def simulate_landing(self):
        log_l = logging.getLogger(f"DroneSimulator.{self.drone_id}.Landing")
        descend_step = self.config.LANDING_SPEED_MPS * self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S
        self.altitude_agl = max(0.0, self.altitude_agl - descend_step)
        self.speed_mps = self.config.LANDING_SPEED_MPS if self.altitude_agl > 0 else 0.0

        log_l.debug(
            f"Descending  AGL={self.altitude_agl:.1f}m  "
            f"v_descent={self.config.LANDING_SPEED_MPS:.1f}m/s"
        )

        if self.altitude_agl == 0.0:
            log_l.info(
                f"🛬 Landed successfully  pos={self.position}  "
                f"total_sim_time={self.sim_time:.1f}s  "
                f"battery_remaining={self.battery_pct:.1f}%"
            )
            self.state = FlightState.LANDED
            self._running = False

    def simulate_lost_mode(self):
        log_lo = logging.getLogger(f"DroneSimulator.{self.drone_id}.LostMode")
        log_lo.warning(
            f"🆘 LOST MODE ACTIVE  pos={self.position}  "
            f"heading={self.heading:.1f}°  gps_lost={self.gps_lost}  "
            f"link={self.link_state.name}"
        )
        # Attempt to recover GPS / link each tick
        if self.gps_lost:
            self.recover_gps()
        if self.link_state == LinkState.LOST:
            if random.random() < self.config.LINK_RECOVER_PROB:
                self.link_state = LinkState.NOMINAL
                log_lo.info("📡 Link recovered in LOST MODE – resuming MISSION")

        if not self.gps_lost and self.link_state != LinkState.LOST:
            log_lo.info("✅ Recovery successful – returning to MISSION")
            self.state = FlightState.MISSION

    def _handle_landed(self):
        self._running = False

    # -----------------------------------------------------------------------
    # NAVIGATION
    # -----------------------------------------------------------------------

    def move_towards_waypoint(self):
        """Advance position one tick's worth of travel toward current waypoint."""
        log_nav = logging.getLogger(f"DroneSimulator.{self.drone_id}.Nav")
        wp = self.current_waypoint()
        dist = self.calculate_distance_to_waypoint()

        step = min(self.config.CRUISE_SPEED_MPS * self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S, dist)
        if dist < 1e-6:
            return

        # Linear interpolation in lat/lon space (fine for short distances)
        fraction = step / dist
        self.position.lat += (wp.lat - self.position.lat) * fraction
        self.position.lon += (wp.lon - self.position.lon) * fraction
        self.position.alt  = wp.alt  # fly to target altitude

        self.speed_mps  = self.config.CRUISE_SPEED_MPS
        self.heading    = self.calculate_heading()

        log_nav.debug(
            f"Moved {step:.1f}m toward WP[{self.wp_index}]  "
            f"remaining={dist - step:.1f}m  "
            f"heading={self.heading:.1f}°  pos={self.position}"
        )

    def calculate_distance_to_waypoint(self) -> float:
        """Haversine distance (m) from current position to current waypoint."""
        if self.wp_index >= len(self.mission):
            return 0.0
        return self._haversine(self.position, self.current_waypoint())

    def calculate_distance_from_home(self) -> float:
        """Haversine distance (m) from current position to home."""
        return self._haversine(self.position, self.home)

    def reached_waypoint(self) -> bool:
        dist = self.calculate_distance_to_waypoint()
        reached = dist <= self.config.WAYPOINT_REACH_RADIUS_M
        if reached:
            self.log.debug(f"Waypoint reach check: dist={dist:.2f}m ≤ {self.config.WAYPOINT_REACH_RADIUS_M}m → REACHED")
        return reached

    def advance_waypoint(self):
        log_nav = logging.getLogger(f"DroneSimulator.{self.drone_id}.Nav")
        prev = self.wp_index
        self.wp_index += 1
        log_nav.info(
            f"Advanced waypoint index  {prev} → {self.wp_index}  "
            f"(total={len(self.mission)})"
        )

    # -----------------------------------------------------------------------
    # TELEMETRY
    # -----------------------------------------------------------------------

    def build_telemetry(self) -> Telemetry:
        return Telemetry(
            timestamp            = datetime.now(timezone.utc).isoformat(),
            drone_id             = self.drone_id,
            state                = self.state.name,
            position             = GPSPoint(self.position.lat, self.position.lon, self.position.alt),
            heading              = self.heading,
            speed_mps            = self.speed_mps,
            altitude_agl         = self.altitude_agl,
            battery_pct          = self.battery_pct,
            gps_fix              = self.gps_fix.value,
            satellites           = self.satellites,
            link_latency_ms      = self.simulate_latency(),
            uplink_kbps          = self.simulate_uplink_bitrate(),
            downlink_kbps        = self.simulate_downlink_bitrate(),
            current_waypoint_idx = self.wp_index,
            mission_progress_pct = self.mission_progress(),
            distance_to_wp_m     = self.calculate_distance_to_waypoint(),
            distance_to_home_m   = self.calculate_distance_from_home(),
            events               = list(self._tick_events),
        )

    def send_telemetry(self):
        log_tel = logging.getLogger(f"DroneSimulator.{self.drone_id}.Telemetry")
        t = self.build_telemetry()
        self._telemetry_log.append(t)

        log_tel.info(
            f"TEL | state={t.state:<10} | pos={t.position} | "
            f"hdg={t.heading:>6.1f}° | spd={t.speed_mps:>5.1f}m/s | "
            f"AGL={t.altitude_agl:>6.1f}m | bat={t.battery_pct:>5.1f}% | "
            f"gps={t.gps_fix}({t.satellites}sv) | "
            f"latency={t.link_latency_ms:>6.1f}ms | "
            f"UL={t.uplink_kbps:>7.1f}kbps DL={t.downlink_kbps:>8.1f}kbps | "
            f"wp={t.current_waypoint_idx}/{self.total_waypoints()} "
            f"({t.mission_progress_pct:.1f}%) | "
            f"d2wp={t.distance_to_wp_m:>8.1f}m | "
            f"d2home={t.distance_to_home_m:>8.1f}m"
            + (f" | EVENTS={t.events}" if t.events else "")
        )

    # -----------------------------------------------------------------------
    # LINK SIMULATION
    # -----------------------------------------------------------------------

    def simulate_latency(self) -> float:
        """Return jittered latency based on current link state (ms)."""
        log_rf = logging.getLogger(f"DroneSimulator.{self.drone_id}.RF")
        base = {
            LinkState.NOMINAL : 30.0,
            LinkState.DEGRADED: 180.0,
            LinkState.LOST    : 9999.0,
        }[self.link_state]
        jitter = random.gauss(0, base * 0.1)
        result = max(1.0, base + jitter)
        log_rf.debug(f"Latency  base={base:.0f}ms  jitter={jitter:+.1f}ms  result={result:.1f}ms")
        return result

    def simulate_uplink_bitrate(self) -> float:
        """Uplink kbps ground→drone."""
        log_rf = logging.getLogger(f"DroneSimulator.{self.drone_id}.RF")
        base = {
            LinkState.NOMINAL : 500.0,
            LinkState.DEGRADED: 80.0,
            LinkState.LOST    : 0.0,
        }[self.link_state]
        result = max(0.0, base + random.gauss(0, base * 0.05))
        log_rf.debug(f"Uplink  {result:.1f} kbps")
        return result

    def simulate_downlink_bitrate(self) -> float:
        """Downlink kbps drone→ground (video + telemetry)."""
        log_rf = logging.getLogger(f"DroneSimulator.{self.drone_id}.RF")
        base = {
            LinkState.NOMINAL : 2000.0,
            LinkState.DEGRADED: 300.0,
            LinkState.LOST    : 0.0,
        }[self.link_state]
        result = max(0.0, base + random.gauss(0, base * 0.05))
        log_rf.debug(f"Downlink  {result:.1f} kbps")
        return result

    def simulate_link_state(self):
        """Stochastic RF link state machine."""
        log_rf = logging.getLogger(f"DroneSimulator.{self.drone_id}.RF")
        prev = self.link_state

        if self.link_state == LinkState.NOMINAL:
            if random.random() < self.config.LINK_LOSS_PROB:
                self.trigger_link_loss()
            elif random.random() < self.config.LINK_DEGRADE_PROB:
                self.link_state = LinkState.DEGRADED
                log_rf.warning("📶 Link degraded  NOMINAL → DEGRADED")
                self._tick_events.append("LINK_DEGRADED")

        elif self.link_state == LinkState.DEGRADED:
            if random.random() < self.config.LINK_RECOVER_PROB:
                self.link_state = LinkState.NOMINAL
                log_rf.info("📶 Link recovered  DEGRADED → NOMINAL")
                self._tick_events.append("LINK_RECOVERED")
            elif random.random() < self.config.LINK_LOSS_PROB:
                self.trigger_link_loss()

        elif self.link_state == LinkState.LOST:
            if random.random() < self.config.LINK_RECOVER_PROB:
                self.link_state = LinkState.NOMINAL
                log_rf.info("📶 Link restored  LOST → NOMINAL")
                self._tick_events.append("LINK_RESTORED")

        if self.link_state != prev:
            log_rf.info(
                f"Link state transition: {prev.name} → {self.link_state.name}  "
                f"pos={self.position}"
            )

    # -----------------------------------------------------------------------
    # GPS SIMULATION
    # -----------------------------------------------------------------------

    def simulate_gps_signal(self):
        """Stochastic GPS signal quality."""
        log_gps = logging.getLogger(f"DroneSimulator.{self.drone_id}.GPS")

        # Satellite count fluctuation
        self.satellites = max(0, self.satellites + random.randint(-1, 1))
        self.satellites = min(self.satellites, 16)

        if not self.gps_lost:
            # Update fix quality based on satellite count
            if self.satellites >= 8:
                self.gps_fix = GPSFixType.THREE_D_FIX
            elif self.satellites >= 4:
                self.gps_fix = GPSFixType.TWO_D_FIX
            else:
                self.gps_fix = GPSFixType.NO_GPS_LOCK

            if random.random() < self.config.GPS_LOSS_PROB:
                self.trigger_gps_loss()
            else:
                log_gps.debug(
                    f"GPS OK  fix={self.gps_fix.name}  sats={self.satellites}"
                )
        else:
            if random.random() < self.config.GPS_RECOVER_PROB:
                self.recover_gps()
            else:
                log_gps.warning(
                    f"GPS LOST  sats={self.satellites}  "
                    f"sim_time={self.sim_time:.1f}s"
                )

    def trigger_gps_loss(self):
        log_gps = logging.getLogger(f"DroneSimulator.{self.drone_id}.GPS")
        self.gps_lost = True
        self.gps_fix  = GPSFixType.NO_FIX
        log_gps.error(
            f"🛰  GPS SIGNAL LOST  pos={self.position}  "
            f"sats={self.satellites}  state={self.state.name}"
        )
        self._tick_events.append("GPS_LOST")
        if self.state not in (FlightState.LANDING, FlightState.LANDED):
            self.trigger_drone_lost()

    def recover_gps(self):
        log_gps = logging.getLogger(f"DroneSimulator.{self.drone_id}.GPS")
        self.gps_lost   = False
        self.satellites = random.randint(8, 14)
        self.gps_fix    = GPSFixType.THREE_D_FIX
        log_gps.info(
            f"🛰  GPS recovered  sats={self.satellites}  fix={self.gps_fix.name}"
        )
        self._tick_events.append("GPS_RECOVERED")

    # -----------------------------------------------------------------------
    # EVENTS
    # -----------------------------------------------------------------------

    def generate_random_event(self):
        """Occasionally inject miscellaneous in-flight events."""
        log_ev = logging.getLogger(f"DroneSimulator.{self.drone_id}.Events")
        if random.random() > self.config.RANDOM_EVENT_PROB:
            return

        events = [
            ("WIND_GUST",       "💨 Wind gust detected – attitude hold engaged"),
            ("OBSTACLE_AVOID",  "🚧 Obstacle avoidance triggered"),
            ("GEOFENCE_WARN",   "🔴 Approaching geofence boundary"),
            ("MOTOR_TEMP_HIGH", "🌡  Motor temperature elevated"),
            ("IMU_VIBRATION",   "📳 High IMU vibration detected"),
            ("RTK_ACQUIRED",    "🛰  RTK fix acquired – precision navigation active"),
        ]
        tag, msg = random.choice(events)
        log_ev.warning(f"{msg}  pos={self.position}  sim_time={self.sim_time:.1f}s")
        self._tick_events.append(tag)

    def trigger_drone_lost(self):
        log_ev = logging.getLogger(f"DroneSimulator.{self.drone_id}.Events")
        if self.state not in (FlightState.LOST,):
            log_ev.error(
                f"🆘 DRONE LOST  pos={self.position}  "
                f"gps_lost={self.gps_lost}  link={self.link_state.name}"
            )
            self._tick_events.append("DRONE_LOST")
            self.state = FlightState.LOST

    def trigger_link_loss(self):
        log_rf = logging.getLogger(f"DroneSimulator.{self.drone_id}.RF")
        self.link_state = LinkState.LOST
        log_rf.error(
            f"📡 LINK LOST  pos={self.position}  sim_time={self.sim_time:.1f}s"
        )
        self._tick_events.append("LINK_LOST")

    # -----------------------------------------------------------------------
    # FLIGHT METRICS
    # -----------------------------------------------------------------------

    def calculate_time_in_air(self) -> float:
        """Simulated seconds since takeoff completed."""
        return max(0.0, self.sim_time - self.takeoff_time)

    def calculate_speed_over_ground(self) -> float:
        return self.speed_mps

    def calculate_heading(self) -> float:
        """True heading (degrees) from current position to current waypoint."""
        if self.wp_index >= len(self.mission):
            return self.heading
        wp = self.current_waypoint()
        dlat = wp.lat - self.position.lat
        dlon = wp.lon - self.position.lon
        angle = math.degrees(math.atan2(dlon, dlat)) % 360
        return angle

    # -----------------------------------------------------------------------
    # WAYPOINT / MISSION
    # -----------------------------------------------------------------------

    def load_mission(self, waypoints: List[Tuple[float, float, float]]):
        log_wp = logging.getLogger(f"DroneSimulator.{self.drone_id}.Mission")
        if not waypoints:
            raise ValueError("Waypoint list must not be empty")
        self.mission = [GPSPoint(lat, lon, alt) for lat, lon, alt in waypoints]
        log_wp.info(f"📋 Mission loaded  total_waypoints={len(self.mission)}")
        for i, wp in enumerate(self.mission):
            log_wp.info(f"    WP[{i:02d}] {wp}")

    def current_waypoint(self) -> Optional[GPSPoint]:
        if self.wp_index < len(self.mission):
            return self.mission[self.wp_index]
        return None

    def total_waypoints(self) -> int:
        return len(self.mission)

    def mission_progress(self) -> float:
        """0–100 % based on waypoints visited."""
        if len(self.mission) <= 1:
            return 100.0
        return min(100.0, self.wp_index / (len(self.mission) - 1) * 100.0)

    # -----------------------------------------------------------------------
    # UTILITIES
    # -----------------------------------------------------------------------

    def _haversine(self,a: GPSPoint, b: GPSPoint) -> float:
        """Great-circle distance in metres between two GPS points."""
        lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
        lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        return 2 * self.config.EARTH_RADIUS_M * math.asin(math.sqrt(h))

    def _print_summary(self):
        """Print end-of-flight statistics."""
        self.log.info("")
        self.log.info("=" * 60)
        self.log.info("FLIGHT SUMMARY")
        self.log.info("=" * 60)
        self.log.info(f"  Drone ID          : {self.drone_id}")
        self.log.info(f"  Final state       : {self.state.name}")
        self.log.info(f"  Total sim time    : {self.sim_time:.1f}s")
        self.log.info(f"  Time in air       : {self.calculate_time_in_air():.1f}s")
        self.log.info(f"  Battery remaining : {self.battery_pct:.1f}%")
        self.log.info(f"  Waypoints reached : {self.wp_index}/{len(self.mission)}")
        self.log.info(f"  Mission progress  : {self.mission_progress():.1f}%")
        self.log.info(f"  Telemetry packets : {len(self._telemetry_log)}")
        self.log.info(f"  Final position    : {self.position}")
        self.log.info(f"  Distance to home  : {self.calculate_distance_from_home():.1f}m")

        event_counts: dict = {}
        for t in self._telemetry_log:
            for ev in t.events:
                event_counts[ev] = event_counts.get(ev, 0) + 1
        if event_counts:
            self.log.info("  Events recorded   :")
            for ev, cnt in sorted(event_counts.items()):
                self.log.info(f"    {ev:<25} × {cnt}")
        self.log.info("=" * 60)


# ---------------------------------------------------------------------------
# Demo – run as script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Tel Aviv area waypoints: (lat, lon, alt_m)
    MISSION_WAYPOINTS = [
        (32.0853,  34.7818,   0.0),    # Home – Tel Aviv centre
        (32.0853,  34.7818,  50.0),    # First target altitude
        (32.0900,  34.7850,  50.0),    # WP 2
        (32.0950,  34.7900,  60.0),    # WP 3
        (32.1000,  34.7950,  60.0),    # WP 4
        (32.1050,  34.8000,  55.0),    # WP 5
        (32.1000,  34.8050,  55.0),    # WP 6
        (32.0950,  34.8020,  50.0),    # WP 7
        (32.0853,  34.7818,  50.0),    # Return to home altitude
        (32.0853,  34.7818,   0.0),    # Land
    ]

    sim = DroneSimulator(drone_id="DRONE-001", waypoints=MISSION_WAYPOINTS)
    sim.run()