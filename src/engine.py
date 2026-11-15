from geopy.distance import geodesic
from models import Mine, Ship
import numpy as np

def check_for_mines(ship: Ship, mines: list[Mine]) -> list[tuple[Mine, float]]:
    """
    Returns a list of (Mine, distance_m, alarm_reason) for all triggered mines.
    """
    triggered_mines = []
    ship_pos = (ship.lat, ship.lon)

    for mine in mines:
        surface_distance = geodesic(ship_pos, (mine.lat, mine.lon)).meters
        total_distance = np.sqrt(surface_distance**2 + mine.depth_m**2)

        # What proportion (0.0 to 1.0) of the ship's signature reaches the mine at this distance?
        distance_factor = mine.depth_m / total_distance
        """detection radius is very dependent on depth in this case
        i dont know a better way for it at the moment but will look into it
        maybe have acoustic threshold activate other thresholds
        """

        felt_acoustic = ship.acoustic_signature * distance_factor
        felt_pressure = ship.pressure_signature * distance_factor**2
        felt_magnetic = ship.magnetic_signature * distance_factor**3
        
        # Check which sensor or sensors in the mine triggered!
        reasons = []
        if felt_magnetic >= 100-mine.magnetic_sensitivity:
            reasons.append("Magnetic sensor")
        if felt_acoustic >= 100-mine.acoustic_sensitivity:
            reasons.append("Acoustic sensor")
        if felt_pressure >= 100-mine.pressure_sensitivity:
            reasons.append("Pressure sensor")

        if any([felt_magnetic >= 100-mine.magnetic_sensitivity,
                felt_acoustic >= 100-mine.acoustic_sensitivity,
                felt_pressure >= 100-mine.pressure_sensitivity]):
            mine.activated = True  # Mark the mine as triggered
            triggered_mines.append((mine, round(total_distance, 1), ", ".join(reasons)))

    return triggered_mines


def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculates the direction (bearing) from point 1 (lat1, lon1) to point 2 (lat2, lon2).
    Returns the direction in degrees (0-360), where 0 = north, 90 = east, 180 = south, 270 = west.
    """
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lon_rad = np.radians(lon2 - lon1)

    x = np.sin(delta_lon_rad) * np.cos(lat2_rad)
    y = np.cos(lat1_rad) * np.sin(lat2_rad) - (np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(delta_lon_rad))

    initial_bearing_rad = np.arctan2(x, y)
    initial_bearing_deg = np.degrees(initial_bearing_rad)

    # Normalize to 0-360 degrees
    compass_bearing = (initial_bearing_deg + 360) % 360

    return compass_bearing

def offset_point(lat: float, lon: float, dist_m: float, angle_deg: float) -> list[float]:
    """Calculates a new GPS point at a given distance (meters) and angle (degrees) from (lat, lon)."""
    rad = np.radians(angle_deg)
    d_lat = (dist_m * np.cos(rad)) / 111320.0
    d_lon = (dist_m * np.sin(rad)) / (111320.0 * np.cos(np.radians(lat)))
    return [lat + d_lat, lon + d_lon]

def get_ship_pentagon(lat: float, lon: float, heading_deg: float) -> list[list[float]]:
    """Creates 5 vertices for a boat-shaped pentagon (rectangle with a pointed bow)."""
    bow = offset_point(lat, lon, 45, heading_deg)                  # 1. Bow tip (straight ahead)
    shoulder_sb = offset_point(lat, lon, 25, heading_deg + 35)     # 2. Starboard bow (front-right corner)
    stern_sb = offset_point(lat, lon, 35, heading_deg + 150)       # 3. Starboard stern (rear-right corner)
    stern_bb = offset_point(lat, lon, 35, heading_deg - 150)       # 4. Port stern (rear-left corner)
    shoulder_bb = offset_point(lat, lon, 25, heading_deg - 35)     # 5. Port bow (front-left corner)
    return [bow, shoulder_sb, stern_sb, stern_bb, shoulder_bb]

def get_mine_x(lat: float, lon: float, size_m: float = 20) -> list[list[float]]:
    """Creates 4 vertices for a mine-shaped X (two crossing lines)."""
    half_size = size_m / 2
    line1_start = offset_point(lat, lon, half_size, 45)   # Top-right
    line1_end = offset_point(lat, lon, half_size, 225)    # Bottom-left
    line2_start = offset_point(lat, lon, half_size, 135)  # Top-left
    line2_end = offset_point(lat, lon, half_size, 315)    # Bottom-right
    return [line1_start, line1_end], [line2_start, line2_end]

def get_heading_line(lat: float, lon: float, heading_deg: float, length_m: float = 400) -> list[list[float]]:
    """Creates the start and end points for the heading line extending from the bow."""
    bow = offset_point(lat, lon, 45, heading_deg)                  # Starts precisely at the bow tip
    line_end = offset_point(lat, lon, 45 + length_m, heading_deg)  # Ends 400 meters farther ahead
    return [bow, line_end]

def get_mine_sensor_data(ship: Ship, mine: Mine) -> dict:
    """Returns the mine's current sensor data and distance to the ship in real-time.
    currently double coded which is tupid but it works for now, will refactor later"""
    
    ship_pos = (ship.lat, ship.lon)
    surface_distance = geodesic(ship_pos, (mine.lat, mine.lon)).meters
    total_distance = np.sqrt(surface_distance**2 + mine.depth_m**2)

    # What proportion (0.0 to 1.0) of the ship's signature reaches the mine at this distance?
    distance_factor = mine.depth_m / total_distance

    felt_acoustic = ship.acoustic_signature * distance_factor
    felt_pressure = ship.pressure_signature * distance_factor**2
    felt_magnetic = ship.magnetic_signature * distance_factor**3

    return {
        "distance_m": round(total_distance, 1),
        "magnetic": round(felt_magnetic, 1),
        "magnetic_limit": round(100.0 - mine.magnetic_sensitivity, 1),
        "acoustic": round(felt_acoustic, 1),
        "acoustic_limit": round(100.0 - mine.acoustic_sensitivity, 1),
        "pressure": round(felt_pressure, 1),
        "pressure_limit": round(100.0 - mine.pressure_sensitivity, 1),
    }
