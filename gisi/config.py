import json
import logging
import os
from ast import literal_eval
from typing import Any, Dict

from .constants import FileLocations

log = logging.getLogger(__name__)

MUST_SET = object()


class Defaults:
    TOKEN = MUST_SET
    COMMAND_PREFIX = ">"
    MONGO_URI = MUST_SET
    MONGO_DATABASE = "Gisi"

    WEBHOOK_URL = None

    DEFAULT_FONT = "arial"

    SEND_STATS_INTERVAL = 60 * 60


def set_defaults(defaults: dict):
    for key, value in defaults.items():
        setattr(Defaults, key, value)
    log.debug(f"added {len(defaults)} setting(s) to default config")


class Config:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def __str__(self) -> str:
        return "<Config>"

    def __getattr__(self, item: str) -> Any:
        return self.get(item)

    def __getitem__(self, item: str) -> Any:
        return self.get(item)

    def __setitem__(self, key: str, value: Any):
        return self.set(key, value)

    @classmethod
    def load(cls):
        try:
            with open(FileLocations.CONFIG, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        return cls(data)

    def save(self):
        with open(FileLocations.CONFIG, "w+") as f:
            json.dump(self.config, f)
        log.info("saved config")

    def get(self, key: str) -> Any:
        try:
            return self.config[key]
        except KeyError:
            try:
                return literal_eval(os.environ[key])
            except (KeyError, SyntaxError):
                default = getattr(Defaults, key)
                if default == MUST_SET:
                    log.error(f"Key \"{key}\" missing in config!")
                    raise KeyError(f"Key \"{key}\" must be set but isn't!") from None
                return default

    def set(self, key: str, value: Any):
        if not hasattr(Defaults, key):
            raise KeyError(f"Key not in Defaults! ({key})")
        self.config[key] = value
        self.save()
