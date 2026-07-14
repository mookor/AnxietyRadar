# AnxietyRadar

Помогает связать громкие звуки на улице с пролетающими самолётами. Сервис опрашивает FlightRadar24 в заданной зоне и показывает, есть ли рядом рейсы — через HTTP API и overlay-индикатор на экране.

## Зачем это нужно

Если громкий звук пугает, а в зоне есть самолёт — скорее всего, это он. Если самолётов нет — звук вызван чем-то другим. AnxietyRadar убирает необходимость вручную открывать FlightRadar.

## Структура проекта

```
AnxietyRadar/
├── config.py              # загрузка настроек из .env
├── .env.example           # шаблон конфигурации (сервер)
├── .env.client.example    # шаблон .env для клиента (overlay на другом ПК)
├── deploy/
│   ├── anxietyradar-planes.service.in  # шаблон unit для systemd
│   └── install-service.sh              # установка сервиса + UFW
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
| `API_PORT` | Порт HTTP API | `8001` |
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

В консоли появится зона поиска. API доступен на `http://localhost:8001` (на VPS по умолчанию `8001`, т.к. `8000` часто занят).

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
- `http://localhost:8001/planes` — все самолёты
- `http://localhost:8001/planes/count` — `{"count": N}`
- `http://localhost:8001/health` — `{"ok": true}`
- `http://localhost:8001/docs` — Swagger UI

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

Сервер слушает `API_BIND_HOST:API_PORT` (по умолчанию `0.0.0.0:8001` на VPS).

### Windows (локальный сервер)

Если с телефона или другого устройства API не открывается — разрешите порт 8000 в брандмауэре Windows.

### Linux-сервер (systemd + UFW)

На удалённом VPS сервис можно держать постоянно через systemd и открыть API только для вашего IP.

> **Важно:** если порт `8000` уже занят другим сервисом, используйте `8001` в `.env`.
> Проверяйте, что отвечает именно AnxietyRadar: `/health` должен вернуть `{"ok":true}`.

**1. Подготовка на сервере**

```bash
cd ~/AnxietyRadar
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
# отредактируйте .env: зона поиска, API_BIND_HOST=0.0.0.0
```

**2. Установка systemd-сервиса и firewall**

```bash
sudo ./deploy/install-service.sh YOUR_CLIENT_IP
```

`YOUR_CLIENT_IP` — ваш внешний IP (узнать: `curl -4 ifconfig.me`). Скрипт:
- генерирует unit из `deploy/anxietyradar-planes.service.in` с путями текущего репозитория
- включает автозапуск и перезапуск при падении (`Restart=always`)
- добавляет правило UFW: TCP `API_PORT` из `.env` (по умолчанию `8001`) только с указанного IP

Ручная установка (без скрипта):

```bash
sudo ./deploy/install-service.sh
sudo ufw allow from YOUR_CLIENT_IP to any port 8001 proto tcp comment 'AnxietyRadar client'
```

**3. Управление сервисом**

```bash
sudo systemctl status anxietyradar-planes   # статус
sudo systemctl restart anxietyradar-planes  # перезапуск
sudo journalctl -u anxietyradar-planes -f   # логи в реальном времени
```

**4. Проверка с сервера**

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/planes/count
```

### Клиент на основном ПК (overlay / tkinter)

На компьютере, откуда запускаете `overlay.py`, нужен свой `.env` — сервер только отдаёт API, зона поиска настраивается на VPS.

```powershell
copy .env.client.example .env
```

Минимально важные поля:

| Переменная | Значение | Зачем |
|------------|----------|-------|
| `API_CLIENT_HOST` | публичный IP или домен сервера | куда ходит overlay |
| `API_PORT` | `8001` | порт API на сервере |
| `OVERLAY_POLL_INTERVAL_MS` | `1500` | частота опроса кружка |

Пример `.env` на клиенте:

```env
API_CLIENT_HOST=your-server.example.com
API_PORT=8001
API_BIND_HOST=127.0.0.1
OVERLAY_POLL_INTERVAL_MS=1500
```

Запуск overlay на Windows:

```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
python overlay.py
```

### Сборка .exe и автозапуск

Один раз собрать исполняемый файл:

```powershell
.\scripts\build_overlay.ps1
```

Результат: `dist\AnxietyRadarOverlay.exe`

Положите `.env` **в папку `dist\`** рядом с exe (скопируйте из `.env.example` или с ПК-клиента). Exe читает конфиг из своей папки, не из репозитория.

Проверка:

```powershell
cd dist
.\AnxietyRadarOverlay.exe
```

Добавить в автозапуск Windows:

```powershell
.\scripts\install_autostart.ps1
```

Скрипт создаёт ярлык в папке автозагрузки (`Win+R` → `shell:startup`). Убрать из автозапуска — удалить ярлык `AnxietyRadarOverlay.lnk` оттуда же.

Пересборка после изменений в `overlay.py`:

```powershell
.\scripts\build_overlay.ps1
```

Проверка доступности API с клиента:

```powershell
curl http://your-server.example.com:8001/health
python test_api.py
```

Если кружок серый — API недоступен: проверьте IP в `.env`, что сервис на VPS запущен (`systemctl status anxietyradar-planes`) и что ваш текущий внешний IP совпадает с разрешённым в UFW.

## Безопасность и публикация в Git

**Никогда не коммитьте:**

| Файл | Почему |
|------|--------|
| `.env` | реальные IP, зона поиска, порты |
| `venv/`, `.venv/` | локальное окружение |
| `*.log`, `__pycache__/` | артефакты запуска |

В репозитории только шаблоны: `.env.example`, `.env.client.example`. После клонирования:

```bash
cp .env.example .env          # на сервере
cp .env.client.example .env   # на клиенте (overlay)
```

Перед `git push` проверьте:

```bash
git status
git diff --staged
```

Убедитесь, что в diff нет `.env`, реальных IP и персональных путей. Systemd unit генерируется на сервере скриптом `install-service.sh` — в git только шаблон `.service.in`.

Если случайно закоммитили секрет — смените IP в UFW и пересоздайте `.env`; для удаления из истории git используйте `git filter-repo` или BFG (простой `git rm` не убирает из старых коммитов).

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
