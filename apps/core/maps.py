"""
Maps & Distance Facade (Architecture §4.4 & §4.5).
Uses Haversine / OpenStreetMap compatible calculations for MVP without requiring an API key,
and abstracts distance, delivery-radius validation, and ETA estimation so Google Maps can be
swapped in later without changing callers in apps/orders or apps/delivery.
"""
import math
from dataclasses import dataclass
from decimal import Decimal

from .models import RestaurantSettings
from .utils import haversine_distance_km


@dataclass(frozen=True)
class RouteEstimate:
    distance_km: Decimal
    within_delivery_radius: bool
    estimated_travel_minutes: int
    origin_lat: Decimal
    origin_lng: Decimal
    destination_lat: Decimal
    destination_lng: Decimal


class MapsFacade:
    """
    Central facade for location distance, delivery eligibility, and travel ETA.
    """

    DEFAULT_AVG_SPEED_KMH = 25.0  # Urban motorcycle dispatch average speed

    @classmethod
    def get_restaurant_origin(cls) -> tuple[Decimal, Decimal]:
        config = RestaurantSettings.get_solo()
        return config.origin_latitude, config.origin_longitude

    @classmethod
    def calculate_distance_from_restaurant(
        cls,
        dest_lat: Decimal | float,
        dest_lng: Decimal | float,
    ) -> Decimal:
        origin_lat, origin_lng = cls.get_restaurant_origin()
        return haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)

    @classmethod
    def estimate_travel_minutes(
        cls,
        distance_km: Decimal | float,
        avg_speed_kmh: float = DEFAULT_AVG_SPEED_KMH,
    ) -> int:
        dist = float(distance_km)
        if dist <= 0:
            return 5
        minutes = math.ceil((dist / avg_speed_kmh) * 60.0) + 5
        return max(5, minutes)

    @classmethod
    def evaluate_destination(
        cls,
        dest_lat: Decimal | float,
        dest_lng: Decimal | float,
    ) -> RouteEstimate:
        config = RestaurantSettings.get_solo()
        origin_lat = config.origin_latitude
        origin_lng = config.origin_longitude
        d_lat = Decimal(str(dest_lat))
        d_lng = Decimal(str(dest_lng))

        distance_km = haversine_distance_km(origin_lat, origin_lng, d_lat, d_lng)
        within_radius = distance_km <= config.max_delivery_radius_km
        travel_minutes = cls.estimate_travel_minutes(distance_km)

        return RouteEstimate(
            distance_km=distance_km,
            within_delivery_radius=within_radius,
            estimated_travel_minutes=travel_minutes,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            destination_lat=d_lat,
            destination_lng=d_lng,
        )
