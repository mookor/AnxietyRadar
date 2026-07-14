# AnxietyRadar

Помогает связать громкие звуки на улице с пролетающими самолётами. Сервис опрашивает FlightRadar24 в заданной зоне и показывает, есть ли рядом рейсы — через HTTP API и overlay-индикатор на экране.

## Зачем это нужно

Если громкий звук пугает, а в зоне есть самолёт — скорее всего, это он. Если самолётов нет — звук вызван чем-то другим. AnxietyRadar убирает необходимость вручную открывать FlightRadar.

## Структура проекта

```
AnxietyRadar/
├── config.py              # загрузка настроек из .env
├── .env.example           # шаблон конфигурации
├── overlay.py             # индикатор-кружок поверх всех окон
├── test_api.py            # простой скрипт для проверки API
├── requirements.txt
└── python/planes/
    ├── find_planes.py     # поиск самолётов + запуск API
    ├── api.py             # FastAPI эндпоинты
    └── flight_radar.py    # клиент FlightRadar24
```

## Установка

```powershell
cd b:\projects\AnxietyRadar
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Отредактируйте `.env` под свою зону и сеть.

## Конфигурация (.env)

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `API_BIND_HOST` | Интерфейс сервера (`0.0.0.0` = доступен в LAN) | `0.0.0.0` |
| `API_PORT` | Порт HTTP API | `8000` |
| `API_CLIENT_HOST` | Хост для клиентов (overlay, тесты) | `localhost` |
| `BOUNDS_LAT1`, `BOUNDS_LON1` | Верхний левый угол зоны поиска | Новосибирск |
| `BOUNDS_LAT2`, `BOUNDS_LON2` | Нижний правый угол зоны поиска | Новосибирск |
| `MAX_ALTITUDE_M` | Макс. высота самолёта (м) | `20000` |
| `INCLUDE_GROUND` | Учитывать самолёты на земле | `true` |
| `FINDER_POLL_INTERVAL_S` | Интервал опроса FR24 (сек) | `1` |
| `PLANE_STALE_SECONDS` | Удалять самолёт, если не видели N сек | `60` |
| `MIN_ALTITUDE_M` | Игнорировать самолёты ниже N метров | `10` |
| `OVERLAY_POLL_INTERVAL_MS` | Интервал опроса overlay (мс) | `1500` |

Для доступа с другого устройства в сети (телефон, WEMOS) укажите LAN IP компьютера в `API_CLIENT_HOST`, например `192.168.0.141`. Узнать IP: `ipconfig` → IPv4-адрес Wi-Fi/Ethernet.

## Запуск

### 1. Сервер (API + поиск самолётов)

```powershell
.\venv\Scripts\python.exe python\planes\find_planes.py
```

В консоли появится зона поиска. API доступен на `http://localhost:8000`.

### 2. Overlay-индикатор

В отдельном терминале:

```powershell
.\venv\Scripts\python.exe overlay.py
```

| Цвет | Значение |
|------|----------|
| Зелёный | в зоне есть самолёты |
| Красный | самолётов нет |
| Серый | API недоступен |

- **Перетаскивание** — ЛКМ
- **Закрыть** — ПКМ по кругу

### 3. Проверка API

```powershell
.\venv\Scripts\python.exe test_api.py
```

Или в браузере:
- `http://localhost:8000/planes` — все самолёты
- `http://localhost:8000/planes/count` — `{"count": N}`
- `http://localhost:8000/health` — `{"ok": true}`
- `http://localhost:8000/docs` — Swagger UI

## API

| Метод | Путь | Ответ |
|-------|------|-------|
| GET | `/planes` | Словарь самолётов (ключ — callsign) |
| GET | `/planes/count` | `{"count": 0}` |
| GET | `/health` | `{"ok": true}` |

Пример записи о самолёте:

```json
{
  "SBI1234": {
    "callsign": "SBI1234",
    "altitude_m": 3200,
    "latitude": 55.01,
    "longitude": 82.75,
    "last_seen": 1720950000.0
  }
}
```

## Как это работает

1. `flight_radar.py` запрашивает FlightRadar24 по прямоугольной зоне (`bounds`).
2. `PlanesFinder` в фоне обновляет список каждую секунду, помечает `last_seen`, удаляет устаревшие и слишком низкие рейсы.
3. `api.py` отдаёт актуальные данные по HTTP.
4. `overlay.py` опрашивает `/planes/count` и меняет цвет кружка.

## Сеть и брандмауэр

Сервер слушает `API_BIND_HOST:API_PORT` (по умолчанию `0.0.0.0:8000`). Если с телефона или другого устройства API не открывается — разрешите порт 8000 в брандмауэре Windows.

## Зависимости

- [FlightRadarAPI](https://github.com/JeanExtreme002/FlightRadarAPI) — неофициальный клиент FR24
- FastAPI + uvicorn — HTTP API
- requests — HTTP-клиент
- python-dotenv — конфигурация
- tkinter — overlay (встроен в Python на Windows)

## Ограничения

- FlightRadar24 — сторонний сервис, данные могут запаздывать на несколько секунд.
- Зона задаётся прямоугольником координат, не кругом.
- Отсутствие самолёта в API не гарантирует, что громкий звук безопасен — это лишь один из источников информации.
