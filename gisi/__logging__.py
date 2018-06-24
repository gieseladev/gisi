import sys

CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,

    "formatters": {
        "detailed": {
            "format": "{asctime} - <{name}> {message}",
            "style": "{"
        },
        "color": {
            "()": "colorlog.ColoredFormatter",
            "format": "{log_color}{levelname:8}{reset} {bg_blue}{name}{reset} {message}",
            "style": "{",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white"
            }
        }
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "color"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/gisi.log",
            "mode": "w",
            "formatter": "detailed"
        }
    },

    "loggers": {
        "gisi": {
            "level": "DEBUG",
            "propagate": False,
            "handlers": ["console", "file"]
        }
    },

    "root": {
        "level": "WARN",
        "handlers": ["console", "file"]
    }
}

sys.modules[__name__] = CONFIG
