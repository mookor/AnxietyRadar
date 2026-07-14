import time

import requests

from config import get_settings

settings = get_settings()

while True:
    response = requests.get(settings.planes_url, timeout=2)
    print(response.json())
    time.sleep(1)
