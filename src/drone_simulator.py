import time
import logging
from typing import List, Tuple

from src.models.flight_state import FlightState
from src.models.link_state import LinkState
from src.models.simulation_config import SimulationConfig
from src.subsystems.gps import GPSSubsystem
from src.subsystems.link import LinkSubsystem
from src.subsystems.mission import MissionSubsystem
from src.subsystems.navigation import NavigationSubsystem
from src.subsystems.events import EventsSubsystem
from src.subsystems.telemetry import TelemetrySubsystem


class DroneSimulator:
    """
    Drone flight simulator – orchestrates all subsystems.

    Parameters
    ----------
    drone_id  : unique identifier string
    waypoints : list of (lat, lon, alt_m) tuples
    """

    def __init__(self, drone_id: str, waypoints: List[Tuple[float, float, float]]):
        self.log      = logging.getLogger(f"DroneSimulator.{drone_id}")
        self.drone_id = drone_id
        self.config   = SimulationConfig()

        self.state    = FlightState.IDLE
        self._running = False

        # Timing
        self.sim_time     = 0.0
        self.takeoff_time = 0.0
        self.loiter_start = 0.0

        # Power
        self.battery_pct = 100.0

        # ── subsystems ──────────────────────────────────────────────────────
        self.mission  = MissionSubsystem(drone_id, waypoints)
        self.nav      = NavigationSubsystem(drone_id, self.mission.waypoints[0], self.config)
        self.gps      = GPSSubsystem(drone_id, self.config)
        self.link     = LinkSubsystem(drone_id, self.config)
        self.events   = EventsSubsystem(drone_id, self.config)
        self.telemetry = TelemetrySubsystem(drone_id)

        self.log.info(
            f"Drone initialised  home={self.nav.home}  "
            f"waypoints={self.mission.total()}  battery={self.battery_pct:.0f}%"
        )

    def run(self) -> None:
        self.log.info("▶  Simulation started")
        self._running = True
        self.state    = FlightState.TAKEOFF

        try:
            while self._running:
                self.update()
                time.sleep(self.config.SIM_TICK_S)
        except KeyboardInterrupt:
            self.log.warning("⚠  Interrupted by user")
        finally:
            self._running = False
            self.log.info("■  Simulation stopped")
            self._print_summary()

    def update(self) -> None:
        dt = self.config.SIM_TIME_SCALE * self.config.SIM_TICK_S
        self.sim_time += dt
        tick_events: list = []

        self.log.debug(
            f"tick  t={self.sim_time:.1f}s  state={self.state.name}  "
            f"bat={self.battery_pct:.1f}%"
        )

        # ── battery ─────────────────────────────────────────────────────────
        self.battery_pct = max(0.0, self.battery_pct - self.config.BATTERY_DRAIN_PER_SEC * dt)
        if self.battery_pct < 20.0:
            self.log.warning(f"🔋 LOW BATTERY  {self.battery_pct:.1f}%")
        if self.battery_pct == 0.0:
            self.log.critical("💀 BATTERY DEPLETED – forcing landing")
            self.state = FlightState.LANDING

        # ── subsystem updates ───────────────────────────────────────────────
        self.gps.update(tick_events)
        self.link.update(tick_events)
        self.events.update(tick_events, self.nav.position, self.sim_time)

        # Trigger LOST state if GPS dropped mid-flight
        if "GPS_LOST" in tick_events and self.state not in (
            FlightState.LANDING, FlightState.LANDED, FlightState.LOST
        ):
            self.events.trigger_drone_lost(
                tick_events, self.nav.position, self.gps.lost, self.link.state
            )
            self.state = FlightState.LOST

        # ── flight state machine ─────────────────────────────────────────────
        {
            FlightState.TAKEOFF : self._do_takeoff,
            FlightState.MISSION : self._do_mission,
            FlightState.LOITER  : self._do_loiter,
            FlightState.LANDING : self._do_landing,
            FlightState.LOST    : self._do_lost,
            FlightState.LANDED  : lambda: None,
            FlightState.IDLE    : lambda: None,
        }[self.state]()

        # ── telemetry ────────────────────────────────────────────────────────
        t = self.telemetry.build_and_send(
            state=self.state, nav=self.nav, gps=self.gps,
            link=self.link, mission=self.mission, tick_events=tick_events,
        )
        t.battery_pct = self.battery_pct   # patch battery after build

    # -----------------------------------------------------------------------
    # FLIGHT STATES
    # -----------------------------------------------------------------------

    def _do_takeoff(self) -> None:
        target = self.mission.waypoints[1].alt if self.mission.total() > 1 else 50.0
        reached = self.nav.climb(target)
        if reached:
            self.takeoff_time = self.sim_time
            self.log.info(
                f"✅ Takeoff complete  AGL={self.nav.altitude_agl:.1f}m  "
                f"t={self.sim_time:.1f}s"
            )
            self.state = FlightState.MISSION

    def _do_mission(self) -> None:
        if self.mission.is_complete():
            self.log.info("🏁 All waypoints reached – landing")
            self.state = FlightState.LANDING
            return

        wp = self.mission.current()
        self.log.debug(
            f"→ WP[{self.mission.index}/{self.mission.total()-1}]  "
            f"dist={self.nav.distance_to(wp):.1f}m  "
            f"progress={self.mission.progress_pct():.1f}%"
        )
        self.nav.move_towards(wp, self.mission.index)

        if self.nav.reached(wp):
            self.log.info(
                f"📍 WP[{self.mission.index}] reached  "
                f"progress={self.mission.progress_pct():.1f}%"
            )
            self.mission.advance()
            if not self.mission.is_complete():
                self.log.info(
                    f"➡  Next WP[{self.mission.index}] = {self.mission.current()}  "
                    f"hdg={self.nav.heading:.1f}°"
                )
                self.loiter_start = self.sim_time
                self.state = FlightState.LOITER

    def _do_loiter(self) -> None:
        self.nav.speed_mps = 0.0
        elapsed = self.sim_time - self.loiter_start
        self.log.debug(f"Loitering  {elapsed:.1f}s / {self.config.LOITER_DURATION_S:.0f}s")
        if elapsed >= self.config.LOITER_DURATION_S:
            self.log.info(f"✅ Loiter complete after {elapsed:.1f}s")
            self.state = FlightState.LANDING if self.mission.is_complete() else FlightState.MISSION

    def _do_landing(self) -> None:
        landed = self.nav.descend()
        if landed:
            self.log.info(
                f"🛬 Landed  pos={self.nav.position}  "
                f"t={self.sim_time:.1f}s  bat={self.battery_pct:.1f}%"
            )
            self.state    = FlightState.LANDED
            self._running = False

    def _do_lost(self) -> None:
        self.log.warning(
            f"🆘 LOST MODE  pos={self.nav.position}  "
            f"gps={self.gps.lost}  link={self.link.state.name}"
        )
        if self.gps.lost:
            self.gps.recover([])
        if self.link.state == LinkState.LOST:
            self.link.try_recover()
        if not self.gps.lost and self.link.state != LinkState.LOST:
            self.log.info("✅ Recovery complete – resuming MISSION")
            self.state = FlightState.MISSION

    # -----------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------

    def _print_summary(self) -> None:
        self.log.info("=" * 60)
        self.log.info("FLIGHT SUMMARY")
        self.log.info("=" * 60)
        self.log.info(f"  Drone ID          : {self.drone_id}")
        self.log.info(f"  Final state       : {self.state.name}")
        self.log.info(f"  Total sim time    : {self.sim_time:.1f}s")
        self.log.info(f"  Time in air       : {max(0.0, self.sim_time - self.takeoff_time):.1f}s")
        self.log.info(f"  Battery remaining : {self.battery_pct:.1f}%")
        self.log.info(f"  Waypoints reached : {self.mission.index}/{self.mission.total()}")
        self.log.info(f"  Mission progress  : {self.mission.progress_pct():.1f}%")
        self.log.info(f"  Telemetry packets : {len(self.telemetry.history)}")
        self.log.info(f"  Final position    : {self.nav.position}")
        self.log.info(f"  Distance to home  : {self.nav.distance_to_home():.1f}m")

        counts = self.telemetry.event_counts()
        if counts:
            self.log.info("  Events recorded   :")
            for ev, cnt in sorted(counts.items()):
                self.log.info(f"    {ev:<25} × {cnt}")
        self.log.info("=" * 60)