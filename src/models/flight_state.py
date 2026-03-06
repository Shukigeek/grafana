from enum import Enum , auto


class FlightState(Enum):
    IDLE        = auto()
    TAKEOFF     = auto()
    MISSION     = auto()
    LOITER      = auto()
    LANDING     = auto()
    LOST        = auto()
    LANDED      = auto()