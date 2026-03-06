import random
import logging
from src.models.simulation_config import SimulationConfig





class EventsSubsystem:
    def __init__(self, drone_id: str, config: SimulationConfig):
        self.log    = logging.getLogger(f"DroneSimulator.{drone_id}.Events")
        self.config = config

    def update(self, tick_events: list, position, sim_time: float) -> None:
        """Roll for a random event this tick."""
        if random.random() > self.config.RANDOM_EVENT_PROB:
            return
        tag, msg = random.choice(self.config.RANDOM_EVENTS)
        self.log.warning(f"{msg}  pos={position}  sim_time={sim_time:.1f}s")
        tick_events.append(tag)

    def trigger_drone_lost(self, tick_events: list, position, gps_lost: bool, link_state) -> None:
        self.log.error(
            f"🆘 DRONE LOST  pos={position}  "
            f"gps_lost={gps_lost}  link={link_state.name}"
        )
        tick_events.append("DRONE_LOST")