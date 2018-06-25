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
                return getattr(Defaults, key)

    def set(self, key: str, value: Any):
        if not hasattr(Defaults, key):
            raise KeyError(f"Key not in Defaults! ({key})")
        self.config[key] = value
        self.save()


def extract_env(config: Config):
    env = os.environ
    for key, default_value in vars(Defaults).items():
        value = env.get(key)
        if value:
            value = literal_eval(value)
            config.config[key] = value
        elif default_value == MUST_SET:
            if key not in config.config:
                raise KeyError(f"Key {key} missing in environment variables!")
