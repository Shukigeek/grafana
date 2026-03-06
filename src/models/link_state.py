from enum import Enum , auto


class LinkState(Enum):
    NOMINAL     = auto()
    DEGRADED    = auto()
    LOST        = auto()