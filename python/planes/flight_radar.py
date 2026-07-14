from __future__ import annotations
import logging

logging.getLogger("FlightRadarAPI.request").setLevel(logging.ERROR)
import math
from typing import Any

from FlightRadarAPI import FlightRadar24API
from FlightRadarAPI.request import RetryPolicy
import time

EARTH_RADIUS_KM = 6371.0088
FEET_PER_METER = 3.28084


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Расстояние между двумя координатами по поверхности Земли."""

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def find_nearby_aircraft_fr24(
    max_altitude_m: float,
    bounds: tuple[float, float, float, float],
    *,
    include_ground: bool = False,
    debug: bool = False,
) -> list[dict[str, Any]]:
    """
    Получает самолёты через неофициальный FlightRadarAPI.

    Сначала FR24 возвращает самолёты из прямоугольной области,
    затем функция точно фильтрует их по круговому радиусу.
    """


    if max_altitude_m < 0:
        raise ValueError("max_altitude_m не может быть отрицательной")

    retry = RetryPolicy(
        max_attempts=3,
        base_delay=1,
        max_delay=5,
        jitter=0.5,
    )

    fr_api = FlightRadar24API(
        timeout=30,
        retry=retry,
    )

    # # В библиотеке радиус передаётся в метрах.

    # bounds = (55.025451, 82.737111, 54.972320, 82.992117)

    # bounds = f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}"
    
    # bounds = fr_api.get_bounds_by_point(
    #     bounds[0],
    #     bounds[1],
    #     20 * 1000,
    # )
    bounds = f"{bounds[0]},{bounds[2]},{bounds[1]},{bounds[3]},"
    flights = fr_api.get_flights(bounds=bounds)

    max_altitude_ft = max_altitude_m * FEET_PER_METER

    if debug:
        print("Границы запроса:", bounds)
        print("FR24 вернул самолётов в прямоугольнике:", len(flights))
        print()

        print("Все самолёты до фильтрации:")

        for flight in flights:
            print({
                "number": flight.number,
                "callsign": flight.callsign,
                "registration": flight.registration,
                "aircraft": flight.aircraft_code,
                "latitude": flight.latitude,
                "longitude": flight.longitude,
                "altitude_ft": flight.altitude,
                "on_ground": flight.on_ground,
            })

        print()

    result: list[dict[str, Any]] = []

    for flight in flights:
        aircraft_lat = flight.latitude
        aircraft_lon = flight.longitude
        altitude_ft = flight.altitude
        on_ground = bool(flight.on_ground)

        if not isinstance(aircraft_lat, (int, float)):
            continue

        if not isinstance(aircraft_lon, (int, float)):
            continue

        if on_ground:
            if not include_ground:
                continue

            altitude_ft = 0

        if not isinstance(altitude_ft, (int, float)):
            continue

        if altitude_ft > max_altitude_ft:
            continue

        if flight.aircraft_code == 'GRND':
            continue
        result.append({
            "id": flight.id,
            "number": flight.number,
            "callsign": flight.callsign,
            "registration": flight.registration,
            "aircraft_code": flight.aircraft_code,
            "airline_icao": flight.airline_icao,
            "origin_iata": flight.origin_airport_iata,
            "destination_iata": flight.destination_airport_iata,
            "latitude": aircraft_lat,
            "longitude": aircraft_lon,
            "altitude_ft": round(float(altitude_ft)),
            "altitude_m": round(float(altitude_ft) / FEET_PER_METER),
            "ground_speed_knots": flight.ground_speed,
            "ground_speed_km_h": (
                round(float(flight.ground_speed) * 1.852)
                if isinstance(flight.ground_speed, (int, float))
                else None
            ),
            "heading": flight.heading,
            "vertical_speed_fpm": flight.vertical_speed,
            "on_ground": on_ground,
        })

    return result


def find_specific_flight(
    aircraft: list[dict[str, Any]],
    *identifiers: str,
) -> dict[str, Any] | None:
    """
    Ищет рейс по номеру, позывному или регистрации.

    Например:
        S75005 — коммерческий номер рейса;
        SBI5005 — ICAO-позывной.
    """

    normalized = {
        identifier.strip().upper()
        for identifier in identifiers
    }

    for item in aircraft:
        values = {
            str(item.get("number") or "").strip().upper(),
            str(item.get("callsign") or "").strip().upper(),
            str(item.get("registration") or "").strip().upper(),
        }

        if normalized & values:
            return item

    return None


if __name__ == "__main__":
    finded_aircraft = {}
    while True:
        
        time.sleep(1)
        aircraft = find_nearby_aircraft_fr24(
            latitude=54.89874,
            longitude=82.89874,
            radius_km=10,
            max_altitude_m=22000,
            include_ground=True,
            debug=False,
        )
        


        if len(aircraft) > 0:
            for item in aircraft:
                if item['id'] not in finded_aircraft:
                    finded_aircraft[item['id']] = item
                    finded_aircraft[item['id']]['last_seen'] = time.time()

        for item in finded_aircraft.values():
            print(
                f"{item['number'] or '-'} / "
                f"{item['callsign'] or '-'}: "
                f"{item['distance_km']} км, "
                f"{item['altitude_m']} м "
                f"({item['altitude_ft']} ft), "
                f"{item['ground_speed_km_h']} км/ч, "
                f"{item['origin_iata'] or '?'} → "
                f"{item['destination_iata'] or '?'}", end="\r"
            )
        if len(finded_aircraft) == 0:
            print("Самолётов не найдено", end="\r")

        for item in finded_aircraft.values():
            if time.time() - item['last_seen'] > 300:
                del finded_aircraft[item['id']]
                continue

            if item['on_ground'] == True:
                del finded_aircraft[item['id']]
