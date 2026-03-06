from enum import Enum

class GPSFixType(Enum):
    NO_GPS_LOCK  = 0   # אין נעילה
    TWO_D_FIX    = 1   # 2D fix – רק latitude/longitude
    THREE_D_FIX  = 2   # 3D fix – כולל altitude
    RTK_FIX      = 3   # RTK – מיקום מדויק מאוד בסנטימטרים
