import os

import requests

from app.database.models import Health
from app.settings import Settings
from app.utils import timer_count


class GITHUB:
    proxy: str

    def __init__(self, settings: Settings):
        self.proxy = settings.PROXY

