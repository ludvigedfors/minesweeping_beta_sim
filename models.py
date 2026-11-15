from dataclasses import dataclass
import json
from geopy.distance import geodesic

@dataclass
class Mine:
    '''Mine - characteristics'''
    id: str
    name: str
    magnetic_sensitivity: float
    acoustic_sensitivity: float
    pressure_sensitivity: float
    severity: str
    radius_m: float
    '''Initialization of mine-state'''
    lat: float
    lon: float
    depth_m: float  # Depth of the mine in meters, also functions as a default value for 100% detection of signals
    activated: bool = False  # Whether the mine has been triggered or not

    @property
    def explosion_radius(self) -> float:
        """Returns the explosion radius based on the mine's severity."""
        if self.severity == "high":
            return 80.0  # High severity mines have a larger explosion radius
        elif self.severity == "medium":
            return 50.0  # Medium severity mines have a moderate explosion radius
        else:
            return 30.0  # Low severity mines have a smaller explosion radius

    def distance_to(self, lat: float, lon: float) -> float:
        """Calculates the distance from the mine to a given latitude and longitude."""
        return geodesic((self.lat, self.lon), (lat, lon)).meters

    

@dataclass
class Ship:
    '''Boat - characteristics'''
    base_magnetic_signature: float
    base_acoustic_signature: float
    base_pressure_signature: float
    max_speed_knots: float
    '''Initialization of boat-state'''
    lat: float
    lon: float
    speed_knots: float
    heading_deg: float = 0.0  # Direction in degrees 0 = north, 90 = east, 180 = south, 270 = west
    degaussing_on: bool = False  # Whether degaussing is enabled or not, add button
    silent_mode: bool = False # Whether silent mode is enabled or not
    """Add health to boat?, which can be reduced by mine explosions. When health reaches 0, the boat is destroyed 
    and simulation ends. Health can be restored by repairs, may need the boat to be stationary for a certain amount of time."""    


    @property
    def magnetic_signature(self) -> float:
        # Returns the ship's magnetic signature based on whether degaussing is enabled or not.
        return 0.25*self.base_magnetic_signature if self.degaussing_on else self.base_magnetic_signature

    # @property
    # def acoustic_signature(self) -> float:
    #     # Returns the ship's acoustic signature based on whether silent mode is enabled or not.
    #     return 0.25*self.base_acoustic_signature if self.silent_mode else self.base_acoustic_signature

    # @property
    # def pressure_signature(self) -> float:
    #     # Returns the ship's pressure signature based on whether silent mode is enabled or not.
    #     return 0.25*self.base_pressure_signature if self.silent_mode else self.base_pressure_signature

    @property
    def acoustic_signature(self) -> float:
        # Engine baseline noise (15 in silent mode, 45 in normal operation) + water noise from speed
        base_noise = 0.25*self.base_acoustic_signature if self.silent_mode else self.base_acoustic_signature
        return base_noise + (self.speed_knots/self.max_speed_knots) * 30.0  # Sound level increases with speed

    @property
    def pressure_signature(self) -> float:
        # Baseline pressure from the hull displacement (20) + dynamic pressure
        return self.base_pressure_signature + (self.speed_knots/self.max_speed_knots)**2 * 25.0  # Pressure increases with speed

def load_mines_from_json(file_path: str) -> list[Mine]:
    with open(file_path, 'r') as file:
        raw_data = json.load(file)

    list_of_mines = []
    for mine_data in raw_data:
        mine = Mine(
            id=mine_data["id"],
            name=mine_data["name"],
            lat=mine_data["lat"],
            lon=mine_data["lon"],
            depth_m=mine_data["depth_m"],
            radius_m=mine_data["radius_m"],
            magnetic_sensitivity=mine_data["magnetic_sensitivity"],
            acoustic_sensitivity=mine_data["acoustic_sensitivity"],
            pressure_sensitivity=mine_data["pressure_sensitivity"],
            severity=mine_data["severity"]
        )
        list_of_mines.append(mine)

    return list_of_mines