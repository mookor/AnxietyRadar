from flight_radar import find_nearby_aircraft_fr24
from threading import Lock, Thread
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import get_settings

class PlanesFinder:
    def __init__(
        self,
        bounds: tuple[float, float, float, float],
        max_altitude_m: int = 2000,
        include_ground: bool = True,
        debug: bool = False,
        *,
        plane_stale_seconds: int = 60,
        min_altitude_m: int = 10,
        poll_interval_s: float = 1,
    ):
        """
        bounds format x1 y1 x2 y2
        """
        self.bounds = bounds
        self.max_altitude_m = max_altitude_m
        self.finded_planes = {}
        self._lock = Lock()
        self.include_ground = include_ground
        self.debug = debug
        self.plane_stale_seconds = plane_stale_seconds
        self.min_altitude_m = min_altitude_m
        self.poll_interval_s = poll_interval_s

    def start_find_planes_loop(self):
        thread = Thread(target=self._run_find_planes_loop, daemon=True)
        thread.start()

    def _find_planes(self):
        aircraft = find_nearby_aircraft_fr24(
            max_altitude_m=self.max_altitude_m,
            bounds=self.bounds,
            include_ground=self.include_ground,
            debug=self.debug,
        )
        return aircraft

    def _run_find_planes_loop(self):
        while True:
            aircraft = self._find_planes()

            now = time.time()
            with self._lock:
                for plane in aircraft:
                    callsign = plane['callsign']

                    self.finded_planes[callsign] = plane
                    self.finded_planes[callsign]['last_seen'] = now

                stale = [
                    callsign
                    for callsign, data in self.finded_planes.items()
                    if now - data['last_seen'] > self.plane_stale_seconds
                    or data['altitude_m'] < self.min_altitude_m
                ]
                for callsign in stale:
                    del self.finded_planes[callsign]
            time.sleep(self.poll_interval_s)

    def get_finded_planes(self) -> dict:
        with self._lock:
            return {callsign: dict(plane) for callsign, plane in self.finded_planes.items()}

if __name__ == "__main__":
    import uvicorn

    from api import app, init_planes_finder

    settings = get_settings()
    bounds = settings.bounds
    print('Поиск в квадрате: ', bounds[0], bounds[1], ":", bounds[2], bounds[3])
    planes_finder = PlanesFinder(
        bounds,
        settings.max_altitude_m,
        include_ground=settings.include_ground,
        plane_stale_seconds=settings.plane_stale_seconds,
        min_altitude_m=settings.min_altitude_m,
        poll_interval_s=settings.finder_poll_interval_s,
    )
    init_planes_finder(planes_finder)
    planes_finder.start_find_planes_loop()

    uvicorn.run(app, host=settings.api_bind_host, port=settings.api_port)