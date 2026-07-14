from __future__ import annotations

from fastapi import FastAPI

from find_planes import PlanesFinder

app = FastAPI(title="AnxietyRadar Planes API")
planes_finder: PlanesFinder | None = None


def init_planes_finder(finder: PlanesFinder) -> None:
    global planes_finder
    planes_finder = finder


@app.get("/planes")
def get_planes() -> dict:
    if planes_finder is None:
        return {}
    return planes_finder.get_finded_planes()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/planes/count")
def get_planes_count() -> dict:
    if planes_finder is None:
        return {"count": 0}
    return {"count": len(planes_finder.get_finded_planes())}
