from dataclasses import dataclass


@dataclass
class GPSPoint:
    lat: float      # degrees
    lon: float      # degrees
    alt: float      # metres ASL

    def __str__(self):
        return f"({self.lat:.6f}°, {self.lon:.6f}°, {self.alt:.1f}m)"
