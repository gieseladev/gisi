import codecs
import io
import logging
import os
import random
from os import path

import aiohttp
import matplotlib.cm as colour_map
import numpy
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from bs4 import BeautifulSoup, Comment
from discord import File, User
from discord.ext.commands import ColourConverter, group
from wordcloud import ImageColorGenerator, WordCloud

from gisi.constants import Colours, FileLocations
from gisi.utils import FlagConverter, UrlConverter, add_embed

log = logging.getLogger(__name__)


class Draw:
    """You can draw but so can Gisi!"""

    def __init__(self, bot):
        self.bot = bot

    @group(invoke_without_command=True)
    async def draw(self, ctx):
        """Drawings make the world more beautiful?"""
        pass

    @staticmethod
    def get_size(text: str, font: ImageFont):
        lines = text.splitlines()
        width = 0
        height = 0
        for line in lines:
            line_w, line_h = font.getsize(line)
            height += line_h
            width = max(line_w, width)
        return width, height

    @staticmethod
    def get_font(name=None, *, default=None, pick_random=True):
        if name and name.lower():
            name = name.lower.replace(" ", "_")
            font_path = f"{FileLocations.FONTS}/{name}.otf"
            if path.isfile(font_path):
                return font_path

        if default:
            return default
        elif pick_random:
            font = random.choice(os.listdir(FileLocations.FONTS))
            font_path = f"{FileLocations.FONTS}/{font}"
            return font_path
        return False

    async def get_image(self, url):
        try:
            async with self.bot.aiosession.get(url) as resp:
                image_data = io.BytesIO(await resp.read())
            img = Image.open(image_data)
        except (OSError, aiohttp.ClientConnectorError, TypeError, ValueError):
            return None
        else:
            return img

    @draw.command()
    async def text(self, ctx, text, *flags):
        """Render text to an image

        Flags:
          -f <name>      | specify the font to use
          -c <colour>    | colour for the text
             <image url> | use text as mask for image
          -b <image url> | set a background image
        """
        text = codecs.unicode_escape_decode(text)[0]
        flags = FlagConverter.from_spec(flags)

        font = Draw.get_font(flags.get("f", None))

        if "c" in flags:
            colour = await self.get_image(flags.get("c", None))
            if not colour:
                colour = await flags.convert_dis("c", ctx, ColourConverter, default=None)
                if colour:
                    colour = colour.to_rgb()
                else:
                    raw_c = flags.get("c")
                    await add_embed(ctx.message, description=f"Couldn't parse colour \"{raw_c}\"", colour=Colours.ERROR)
                    return
        else:
            colour = "white"

        font = ImageFont.truetype(font=font, size=40)
        text_width, text_height = Draw.get_size(text, font)
        margin = 10

        im = await self.get_image(flags.get("b", None))
        if im:
            new_width = text_width + margin
            new_height = int(new_width * im.height / im.width)
            if new_height < text_height + margin:
                new_height = text_height + margin
                new_width = int(new_height * im.width / im.height)

            im = im.resize((new_width, new_height)).convert("RGBA")
            enhancer = ImageEnhance.Brightness(im)
            im = enhancer.enhance(.6)
            im = im.filter(ImageFilter.GaussianBlur(3))
        else:
            im = Image.new("RGBA", (text_width + margin, text_height + margin), color=None)

        mask = Image.new("L", im.size, color=None)
        draw = ImageDraw.Draw(mask)
        draw.text(((im.width - text_width) // 2, (im.height - text_height) // 2), text, fill=255, font=font,
                  align="center")

        if isinstance(colour, Image.Image):
            _width = im.width
            _height = int(_width * colour.width / colour.height)
            if _height < im.height:
                _height = im.height
                _width = int(_height * colour.width / colour.height)

            w_diff = abs(im.width - _width) // 2
            h_diff = abs(im.height - _height) // 2
            colour = colour.resize((_width, _height)).crop((w_diff, h_diff, im.width + w_diff, im.height + h_diff))

        im.paste(colour, mask=mask)

        img_file = io.BytesIO()
        im.save(img_file, "PNG")
        img_file.seek(0)
        file = File(img_file, "text.png")
        await ctx.send(file=file)
        await ctx.message.delete()

    async def create_wordcloud(self, ctx, text, flags, *, file_title="wordcloud.png"):
        WC_WIDTH = 600
        WC_HEIGHT = 400

        font = Draw.get_font(flags.get("f", default=None))
        try:
            colourmap = colour_map.get_cmap(flags.get("c", None))
        except ValueError:
            colourmap = random.choice(colour_map.datad)

        mask = await self.get_image(flags.get("m", None))
        if mask:
            WC_WIDTH, WC_HEIGHT = mask.size
            mask = numpy.array(mask)

        colour_func = await self.get_image(flags.get("ci", None))
        if colour_func:
            _width = WC_WIDTH
            _height = int(WC_WIDTH * colour_func.height / colour_func.width)
            if _height < WC_HEIGHT:
                _height = WC_HEIGHT
                _width = int(WC_HEIGHT * colour_func.width / colour_func.height)
            colour_func = colour_func.resize((_width, _height)).crop((0, 0, WC_WIDTH, WC_HEIGHT))
            colour_func = ImageColorGenerator(numpy.array(colour_func))

        wc = WordCloud(width=WC_WIDTH, height=WC_HEIGHT, mode="RGBA", background_color=None,
                       font_path=font,
                       color_func=colour_func,
                       colormap=colourmap,
                       mask=mask)

        await add_embed(ctx.message, description="creating word cloud!", colour=Colours.INFO)
        wc.generate(text)

        img = wc.to_image()
        img_file = io.BytesIO()
        img.save(img_file, "PNG")
        img_file.seek(0)
        file = File(img_file, file_title)

        await add_embed(ctx.message, description="uploading word cloud!", colour=Colours.INFO)
        await ctx.send(file=file)
        await add_embed(ctx.message, description="done!", colour=Colours.SUCCESS)
        return True

    @draw.group(invoke_without_command=True)
    async def wordcloud(self, ctx, text, *flags):
        """Draw some beautiful word clouds.

        Flags:
          -f <name>       | specify font
          -m <image url>  | image mask
          -c <colour map> | specify colour map to use
          -ci <image url> | specify colour image
        """
        flags = FlagConverter.from_spec(flags)
        await self.create_wordcloud(ctx, text, flags)

    @wordcloud.command()
    async def chat(self, ctx, *flags):
        """Draw word cloud from chat

        Flags:
          -u <user>    | specify chat
          -lm <number> | set max number of messages
          [Flags from default wordcloud]
        """
        flags = FlagConverter.from_spec(flags)
        target = await flags.convert_dis("u", ctx, User, default=ctx.channel)
        limit = flags.convert("lm", int, default=500)

        await add_embed(ctx.message, description=f"Reading your messages ԅ(≖‿≖ԅ)", colour=Colours.INFO)
        text = ""
        async for message in target.history(limit=limit):
            text += message.content + "\n"

        await self.create_wordcloud(ctx, text, flags)

    @wordcloud.command()
    async def url(self, ctx, url: UrlConverter, *flags):
        """Draw a word cloud from an online source

        Flags:
          [Flags from default wordcloud]
        """
        await add_embed(ctx.message, description=f"Reading website ԅ(≖‿≖ԅ)", colour=Colours.INFO)
        async with self.bot.aiosession.get(url) as resp:
            content_type = resp.content_type
            if not content_type.startswith("text"):
                await add_embed(description="Can't extract any words from \"{url}\"", colour=Colours.ERROR)
                return
            text = await resp.text()

        if content_type == "text/html":
            bs = BeautifulSoup(text, "html.parser")

            def tag_visible(element):
                if element.parent.name in ["style", "script", "head", "title", "meta", "[document]"]:
                    return False
                if isinstance(element, Comment):
                    return False
                return True

            texts = filter(tag_visible, bs.find_all(text=True))
            text = " ".join(t.strip() for t in texts)

        await self.create_wordcloud(ctx, text, flags)


def setup(bot):
    bot.add_cog(Draw(bot))
