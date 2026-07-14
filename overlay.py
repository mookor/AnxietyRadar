"""
AnxietyRadar — индикатор поверх всех окон.

Зелёный круг  — в зоне есть самолёты (громкий звук, скорее всего, от них).
Красный круг  — самолётов нет.
Серый круг    — API недоступен.

Настройки: .env (см. .env.example)

Запуск:
    python overlay.py

Перетаскивание: зажать ЛКМ и тянуть.
Закрытие: ПКМ по кругу.
"""

from __future__ import annotations

import argparse
import tkinter as tk

import requests

from config import get_settings

CIRCLE_SIZE = 36
PADDING = 4

COLOR_PLANES = "#22c55e"
COLOR_EMPTY = "#ef4444"
COLOR_OFFLINE = "#9ca3af"


class OverlayIndicator:
    def __init__(self, api_url: str, poll_interval_ms: int) -> None:
        self.api_url = api_url
        self.poll_interval_ms = poll_interval_ms
        self.plane_count = 0
        self.online = False

        self.root = tk.Tk()
        self.root.title("AnxietyRadar")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")
        self.root.configure(bg="white")

        size = CIRCLE_SIZE + PADDING * 2
        self.root.geometry(f"{size}x{size}+4350+25")

        self.canvas = tk.Canvas(
            self.root,
            width=size,
            height=size,
            bg="white",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.circle = self.canvas.create_oval(
            PADDING,
            PADDING,
            PADDING + CIRCLE_SIZE,
            PADDING + CIRCLE_SIZE,
            fill=COLOR_OFFLINE,
            outline="#333333",
            width=1,
        )

        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-3>", lambda _e: self.root.destroy())

        self._drag_offset_x = 0
        self._drag_offset_y = 0

        self.root.after(self.poll_interval_ms, self._poll_api)
        self.root.mainloop()

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_offset_x = event.x
        self._drag_offset_y = event.y

    def _on_drag(self, event: tk.Event) -> None:
        x = self.root.winfo_x() + event.x - self._drag_offset_x
        y = self.root.winfo_y() + event.y - self._drag_offset_y
        self.root.geometry(f"+{x}+{y}")

    def _poll_api(self) -> None:
        try:
            response = requests.get(self.api_url, timeout=2)
            response.raise_for_status()
            self.plane_count = response.json().get("count", 0)
            self.online = True
        except requests.RequestException:
            self.online = False

        self._update_circle()
        self.root.after(self.poll_interval_ms, self._poll_api)

    def _update_circle(self) -> None:
        if not self.online:
            color = COLOR_OFFLINE
            title = "AnxietyRadar: API недоступен"
        elif self.plane_count > 0:
            color = COLOR_PLANES
            title = f"AnxietyRadar: {self.plane_count} самолёт(ов) рядом"
        else:
            color = COLOR_EMPTY
            title = "AnxietyRadar: самолётов нет"

        self.canvas.itemconfig(self.circle, fill=color)
        self.root.title(title)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="AnxietyRadar overlay indicator")
    parser.add_argument(
        "--url",
        default=settings.planes_count_url,
        help="URL эндпоинта /planes/count",
    )
    args = parser.parse_args()
    OverlayIndicator(args.url, settings.overlay_poll_interval_ms)


if __name__ == "__main__":
    main()
