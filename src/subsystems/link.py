import random
import logging
from src.models.link_state import LinkState
from src.models.simulation_config import SimulationConfig


class LinkSubsystem:
    def __init__(self, drone_id: str, config: SimulationConfig):
        self.log    = logging.getLogger(f"DroneSimulator.{drone_id}.RF")
        self.config = config

        self.state         = LinkState.NOMINAL
        self.latency_ms    = 30.0
        self.uplink_kbps   = 500.0
        self.downlink_kbps = 2000.0

    def update(self, tick_events: list) -> None:
        """Advance link state machine one tick."""
        prev = self.state

        if self.state == LinkState.NOMINAL:
            if random.random() < self.config.LINK_LOSS_PROB:
                self._lose(tick_events)
            elif random.random() < self.config.LINK_DEGRADE_PROB:
                self.state = LinkState.DEGRADED
                self.log.warning("📶 Link degraded  NOMINAL → DEGRADED")
                tick_events.append("LINK_DEGRADED")

        elif self.state == LinkState.DEGRADED:
            if random.random() < self.config.LINK_RECOVER_PROB:
                self.state = LinkState.NOMINAL
                self.log.info("📶 Link recovered  DEGRADED → NOMINAL")
                tick_events.append("LINK_RECOVERED")
            elif random.random() < self.config.LINK_LOSS_PROB:
                self._lose(tick_events)

        elif self.state == LinkState.LOST:
            if random.random() < self.config.LINK_RECOVER_PROB:
                self.state = LinkState.NOMINAL
                self.log.info("📶 Link restored  LOST → NOMINAL")
                tick_events.append("LINK_RESTORED")

        if self.state != prev:
            self.log.info(f"Link transition: {prev.name} → {self.state.name}")

        self.latency_ms    = self._calc_latency()
        self.uplink_kbps   = self._calc_uplink()
        self.downlink_kbps = self._calc_downlink()

    def force_loss(self, tick_events: list, position=None) -> None:
        self._lose(tick_events, position=position)

    def try_recover(self) -> bool:
        """Returns True if recovery succeeded (used by LostMode)."""
        if random.random() < self.config.LINK_RECOVER_PROB:
            self.state = LinkState.NOMINAL
            self.log.info("📡 Link recovered in LOST MODE")
            return True
        return False

    def _lose(self, tick_events: list, position=None) -> None:
        self.state = LinkState.LOST
        extra = f"  pos={position}" if position else ""
        self.log.error(f"📡 LINK LOST{extra}")
        tick_events.append("LINK_LOST")

    def _calc_latency(self) -> float:
        base = {LinkState.NOMINAL: 30.0, LinkState.DEGRADED: 180.0, LinkState.LOST: 9999.0}[self.state]
        result = max(1.0, base + random.gauss(0, base * 0.1))
        self.log.debug(f"Latency  {result:.1f}ms")
        return result

    def _calc_uplink(self) -> float:
        base = {LinkState.NOMINAL: 500.0, LinkState.DEGRADED: 80.0, LinkState.LOST: 0.0}[self.state]
        result = max(0.0, base + random.gauss(0, base * 0.05)) if base else 0.0
        self.log.debug(f"Uplink  {result:.1f} kbps")
        return result

    def _calc_downlink(self) -> float:
        base = {LinkState.NOMINAL: 2000.0, LinkState.DEGRADED: 300.0, LinkState.LOST: 0.0}[self.state]
        result = max(0.0, base + random.gauss(0, base * 0.05)) if base else 0.0
        self.log.debug(f"Downlink  {result:.1f} kbps")
        return result