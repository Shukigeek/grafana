from dataclasses import dataclass

@dataclass
class SimulationConfig:
    # 🌍 פיזיקה ותנועה
    EARTH_RADIUS_M: float          = 6_371_000.0     # רדיוס כדור הארץ במטרים
    TAKEOFF_SPEED_MPS: float       = 2.5             # מהירות המראה אנכית
    CRUISE_SPEED_MPS: float        = 12.0            # מהירות טיסה אופקית
    LANDING_SPEED_MPS: float       = 1.5             # מהירות ירידה
    WAYPOINT_REACH_RADIUS_M: float = 5.0             # נחשב שהרחפן הגיע ל-waypoint אם בתוך רדיוס זה
    LOITER_DURATION_S: float       = 8.0             # זמן שהרחפן מחכה ב-loiter

    # 🔋 סוללה
    BATTERY_DRAIN_PER_SEC: float   = 0.025           # אחוז סוללה שנגמר לכל שנייה סימולציה

    # ⏱ זמן סימולציה
    SIM_TICK_S: float              = 0.5             # wall-clock seconds per subsystems tick
    SIM_TIME_SCALE: float          = 4.0             # כמה שניות סימולציה לכל tick אמיתי

    # 📡 אירועי GPS
    GPS_LOSS_PROB: float           = 0.004           # הסתברות אובדן GPS בכל tick
    GPS_RECOVER_PROB: float        = 0.15            # הסתברות שחזרת GPS בכל tick לאחר אובדן

    # 📶 אירועי קישור (Link)
    LINK_LOSS_PROB: float          = 0.003           # הסתברות אובדן קישור
    LINK_DEGRADE_PROB: float       = 0.01            # הסתברות ירידה באיכות הקישור
    LINK_RECOVER_PROB: float       = 0.20            # הסתברות שחזרת הקישור לאחר אובדן

    # 🎲 אירועים אקראיים
    RANDOM_EVENT_PROB: float       = 0.005           # הסתברות לאירוע אקראי כל tick

    # 🎲 אירועים אקראיים
    RANDOM_EVENTS = [
        ("WIND_GUST", "💨 Wind gust detected – attitude hold engaged"),
        ("OBSTACLE_AVOID", "🚧 Obstacle avoidance triggered"),
        ("GEOFENCE_WARN", "🔴 Approaching geofence boundary"),
        ("MOTOR_TEMP_HIGH", "🌡  Motor temperature elevated"),
        ("IMU_VIBRATION", "📳 High IMU vibration detected"),
        ("RTK_ACQUIRED", "🛰  RTK fix acquired – precision navigation active"),
    ]