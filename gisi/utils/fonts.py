import io
import logging
import os
import random
from collections import namedtuple
from os import path

import aiohttp
from PIL import ImageFont

from gisi.constants import FileLocations

_default = object()
log = logging.getLogger(__name__)

Font = namedtuple("Font", ("name", "location"))


def im_font_from_io_font(font_io: io.BytesIO):
    font_io.seek(0)
    try:
        font = ImageFont.FreeTypeFont(font_io)
    except IOError:
        raise TypeError("Couldn't open font")
    font_io.seek(0)
    return font


async def download_font(session, url, *, name=None):
    font_io = io.BytesIO()
    try:
        async with session.get(url) as resp:
            resp.raise_for_status()
            font_io.write(await resp.read())
            if not name:
                filename = ""
                if resp.content_disposition:
                    filename = resp.content_disposition.filename
                if not filename:
                    filename = resp.url.name
                s = filename.rpartition(".")
                name = s[0] or s[2]
    except (aiohttp.ClientResponseError, aiohttp.ClientConnectorError):
        raise ValueError(f"Couldn't extract font from {url}")
    else:
        im_font_from_io_font(font_io)
        return name, font_io


class FontManager:
    def __init__(self, bot):
        self.bot = bot
        self.fonts = FontManager.load_fonts()
        self.default = self.fonts[bot.config.default_font]
        log.info(f"loaded {len(self.fonts)} fonts, default: \"{self.default.name}\"")

    def __repr__(self):
        return f"FontManager"

    def __iter__(self):
        return iter(self.fonts.values())

    @staticmethod
    def load_font(location, *, name=None):
        if not path.isfile(location):
            raise ValueError(f"location must point to a file!")
        if not name:
            name = path.basename(location).rpartition(".")[0].replace("_", " ").title()
        font = Font(name, location)
        return font

    @staticmethod
    def load_fonts(directory=FileLocations.FONTS):
        files = os.listdir(directory)
        fonts = {}
        for file in files:
            location = f"{directory}/{file}"
            f_name = file.rpartition(".")[0].lower()
            name = f_name.replace("_", " ").title()
            font = FontManager.load_font(location, name=name)
            fonts[f_name] = font
        return fonts

    def get(self, name, default=_default):
        name = name.lower().replace(" ", "_")
        try:
            return self.fonts[name]
        except KeyError:
            if default is not _default:
                return default
            else:
                raise

    def random(self):
        return random.choice(list(self.fonts.values()))

    def remove(self, name):
        print(name)
        font = self.get(name)
        if font == self.default:
            raise ValueError("mustn't remove default font!")
        os.remove(font.location)
        del font

    def add(self, name, font_io):
        try:
            ImageFont.FreeTypeFont(font_io)
        except OSError:
            raise ValueError("Provided font doesn't seem to be a font!")
        f_name = name.lower().replace(" ", "_")
        if f_name in self.fonts:
            raise ValueError(f"A font with this name already exists ({f_name})")
        location = f"{FileLocations.FONTS}/{f_name}.otf"
        font_io.seek(0)
        with open(location, "w+b") as f:
            f.write(font_io.read())
        font = Font(name, location)
        self.fonts[f_name] = font
