import json
import logging

from .constants import FileLocations

log = logging.getLogger(__name__)


class Defaults:
    token = None
    command_prefix = ">"
    mongodb_uri = None

    webhook_url = None


def SetDefaults(defaults: dict):
    for key, value in defaults.items():
        setattr(Defaults, key, value)
    log.debug(f"added {len(defaults)} setting(s) to default config")


class Config:
    def __init__(self, config):
        self.config = config

    def __str__(self):
        return "<Config>"

    def __getattr__(self, item):
        return self.get(item)

    def __getitem__(self, item):
        return self.get(item)

    def __setitem__(self, key, value):
        return self.set(key, value)

    @classmethod
    def load(cls):
        with open(FileLocations.CONFIG, "r") as f:
            data = json.load(f)
        return cls(data)

    def save(self):
        with open(FileLocations.CONFIG, "w+") as f:
            json.dump(self.config, f)
        log.info("saved config")

    def get(self, key):
        return self.config.get(key, getattr(Defaults, key))

    def set(self, key, value):
        if not hasattr(Defaults, key):
            raise KeyError(f"Key not in Defaults! ({key})")
        self.config[key] = value
        self.save()
