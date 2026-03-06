import random
import logging
from src.models.gps_fix_type import GPSFixType
from src.models.simulation_config import SimulationConfig


class GPSSubsystem:
    def __init__(self, drone_id: str, config: SimulationConfig):
        self.log     = logging.getLogger(f"DroneSimulator.{drone_id}.GPS")
        self.config  = config

        self.fix      = GPSFixType.THREE_D_FIX
        self.satellites = random.randint(10, 14)
        self.lost     = False

    def update(self, tick_events: list) -> None:
        """Called every tick. Appends event tags to tick_events."""
        self._fluctuate_satellites()

        if not self.lost:
            self._update_fix_quality()
            if random.random() < self.config.GPS_LOSS_PROB:
                self._lose(tick_events)
            else:
                self.log.debug(f"GPS OK  fix={self.fix.name}  sats={self.satellites}")
        else:
            if random.random() < self.config.GPS_RECOVER_PROB:
                self._recover(tick_events)
            else:
                self.log.warning(f"GPS LOST  sats={self.satellites}")

    def trigger_loss(self, tick_events: list, position, state_name: str) -> None:
        """Force a GPS loss (called by EventsSubsystem or externally)."""
        self._lose(tick_events, position=position, state_name=state_name)

    def recover(self, tick_events: list) -> None:
        self._recover(tick_events)

    def _fluctuate_satellites(self) -> None:
        self.satellites = max(0, min(16, self.satellites + random.randint(-1, 1)))

    def _update_fix_quality(self) -> None:
        if self.satellites >= 8:
            self.fix = GPSFixType.THREE_D_FIX
        elif self.satellites >= 4:
            self.fix = GPSFixType.TWO_D_FIX
        else:
            self.fix = GPSFixType.NO_GPS_LOCK

    def _lose(self, tick_events: list, position=None, state_name: str = "") -> None:
        self.lost = True
        self.fix  = GPSFixType.NO_GPS_LOCK
        extra = f"  pos={position}  state={state_name}" if position else ""
        self.log.error(f"🛰  GPS SIGNAL LOST  sats={self.satellites}{extra}")
        tick_events.append("GPS_LOST")

    def _recover(self, tick_events: list) -> None:
        self.lost       = False
        self.satellites = random.randint(8, 14)
        self.fix        = GPSFixType.THREE_D_FIX
        self.log.info(f"🛰  GPS recovered  sats={self.satellites}  fix={self.fix.name}")
        tick_events.append("GPS_RECOVERED")