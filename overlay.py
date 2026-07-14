"""
AnxietyRadar — индикатор поверх всех окон.

Зелёный круг  — в зоне есть самолёты (громкий звук, скорее всего, от них).
Красный круг  — самолётов нет.
Серый круг    — API недоступен.

Настройки: .env (см. .env.example)

Перетаскивание: зажать ЛКМ и тянуть.
Закрытие: ПКМ по кругу.

Лог ошибок (рядом с exe): overlay.log
"""

from __future__ import annotations

import argparse
import logging
import sys
import tkinter as tk
import traceback

import requests

from config import get_app_dir, get_settings

CIRCLE_SIZE = 36
PADDING = 4

COLOR_PLANES = "#22c55e"
COLOR_EMPTY = "#ef4444"
COLOR_OFFLINE = "#9ca3af"

LOG_FILE = get_app_dir() / "overlay.log"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def log_unhandled_exception(exc_type, exc_value, exc_tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logging.critical(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_tb),
    )


class OverlayIndicator:
    def __init__(
        self,
        count_url: str,
        planes_url: str,
        poll_interval_ms: int,
    ) -> None:
        self.count_url = count_url
        self.planes_url = planes_url
        self.poll_interval_ms = poll_interval_ms
        self.plane_count = 0
        self.online = False
        self.status_detail = "Запуск..."

        self.root = tk.Tk()
        self.root.title("AnxietyRadar")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")
        self.root.configure(bg="white")

        size = CIRCLE_SIZE + PADDING * 2
        self.root.geometry(f"{size}x{size}+50+50")

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

        logging.info("Overlay started. count=%s planes=%s", self.count_url, self.planes_url)
        self.root.after(0, self._poll_api)
        self.root.mainloop()

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_offset_x = event.x
        self._drag_offset_y = event.y

    def _on_drag(self, event: tk.Event) -> None:
        try:
            x = self.root.winfo_x() + event.x - self._drag_offset_x
            y = self.root.winfo_y() + event.y - self._drag_offset_y
            self.root.geometry(f"+{x}+{y}")
        except tk.TclError:
            logging.exception("Drag failed")

    def _parse_count(self, data: object) -> int | None:
        if not isinstance(data, dict):
            return None
        if "count" in data:
            return int(data["count"])
        return len(data)

    def _fetch_plane_count(self) -> None:
        try:
            response = requests.get(self.count_url, timeout=5)
            if response.status_code == 200:
                count = self._parse_count(response.json())
                if count is not None:
                    self.plane_count = count
                    self.online = True
                    self.status_detail = "OK"
                    return
                self.status_detail = "Неверный ответ /planes/count"
            else:
                self.status_detail = f"/planes/count → HTTP {response.status_code}"

            response = requests.get(self.planes_url, timeout=5)
            response.raise_for_status()
            count = self._parse_count(response.json())
            if count is not None:
                self.plane_count = count
                self.online = True
                self.status_detail = "OK (/planes)"
                return

            self.online = False
            self.status_detail = "Неверный ответ /planes"
        except requests.RequestException as error:
            self.online = False
            self.status_detail = str(error)[:60]
            logging.warning("API request failed: %s", error)
        except (ValueError, TypeError) as error:
            self.online = False
            self.status_detail = "Ошибка разбора ответа"
            logging.warning("Bad API response: %s", error)

    def _poll_api(self) -> None:
        try:
            self._fetch_plane_count()
            self._update_circle()
        except Exception:
            logging.exception("Poll loop error")
            self.online = False
            self.status_detail = "Внутренняя ошибка"
            try:
                self._update_circle()
            except Exception:
                logging.exception("UI update failed")
        finally:
            try:
                self.root.after(self.poll_interval_ms, self._poll_api)
            except tk.TclError:
                logging.info("Overlay window closed")

    def _update_circle(self) -> None:
        if not self.online:
            color = COLOR_OFFLINE
            title = f"AnxietyRadar: API недоступен ({self.status_detail})"
        elif self.plane_count > 0:
            color = COLOR_PLANES
            title = f"AnxietyRadar: {self.plane_count} самолёт(ов) рядом"
        else:
            color = COLOR_EMPTY
            title = "AnxietyRadar: самолётов нет"

        self.canvas.itemconfig(self.circle, fill=color)
        self.root.title(title)


def main() -> None:
    setup_logging()
    sys.excepthook = log_unhandled_exception

    try:
        settings = get_settings()
        parser = argparse.ArgumentParser(description="AnxietyRadar overlay indicator")
        parser.add_argument(
            "--url",
            default=settings.planes_count_url,
            help="URL эндпоинта /planes/count",
        )
        args = parser.parse_args()
        logging.info("Using count URL: %s", args.url)
        OverlayIndicator(args.url, settings.planes_url, settings.overlay_poll_interval_ms)
    except Exception:
        logging.critical("Startup failed:\n%s", traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
