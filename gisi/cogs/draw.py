import io
import logging
import os
import random
from os import path

import aiohttp
from PIL import Image, ImageColor, ImageDraw, ImageFont
from bs4 import BeautifulSoup, Comment
from discord import File, User
from discord.ext.commands import group
from wordcloud import WordCloud

from gisi.constants import Colours, FileLocations
from gisi.utils import UrlConverter, add_embed

log = logging.getLogger(__name__)

WORDCLOUD_COLOUR_SCHEMES = ["hot", "summer", "BrBG", "PuBuGn"]


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

    @draw.command()
    async def text(self, ctx, text, colour="white", font=None, background: UrlConverter = None):
        """Render text to an image

        Create stunning *cough* graphical texts...
        """
        if font and font.lower() not in ("none", "default"):
            font_path = f"{FileLocations.FONTS}/{font.lower()}.ttf"
            if not path.isfile(font_path):
                await add_embed(ctx.message, colour=Colours.ERROR,
                                description=f"Font \"{font}\" doesn't exist!")
                return
        else:
            font = random.choice(os.listdir(FileLocations.FONTS))
            font_path = f"{FileLocations.FONTS}/{font}"

        if background:
            try:
                async with self.bot.aiosession.get(background) as resp:
                    image_data = io.BytesIO(await resp.read())
                background_img = Image.open(image_data)
            except (OSError, aiohttp.ClientConnectorError):
                await add_embed(ctx.message, colour=Colours.ERROR,
                                description=f"can't use image {background}")
                return

        else:
            background_img = None

        inverse = colour.lower() in ("inverse", "image", "background")

        if not inverse:
            try:
                colour = ImageColor.getrgb(colour)
            except ValueError:
                await add_embed(ctx.message, colour=Colours.ERROR,
                                description=f"can't parse \"{colour}\" to a colour")
                return

        font = ImageFont.truetype(font=font_path, size=40)
        text_width, text_height = Draw.get_size(text, font)
        margin = 10

        if background_img:
            bg = background_img
            new_width = text_width + margin
            new_height = int(new_width * bg.height / bg.width)
            if new_height < text_height + margin:
                new_height = text_height + margin
                new_width = int(new_height * bg.width / bg.height)

            bg = bg.resize((new_width, new_height)).convert("RGBA")
            if inverse:
                im = Image.new("L", (new_width, new_height), color=0)
                final_im = Image.new("RGBA", (new_width, new_height), color=None)
                colour = 255
            else:
                im = bg
        else:
            im = Image.new("RGBA", (text_width + margin, text_height + margin), color=None)

        draw = ImageDraw.Draw(im)
        draw.text(((im.width - text_width) // 2, (im.height - text_height) // 2), text, fill=colour, font=font,
                  align="center")

        if inverse:
            final_im.paste(bg, mask=im)
            left = (final_im.width - text_width) // 2 - margin // 2
            top = (final_im.height - text_height) // 2 - margin // 2
            im = final_im.crop((left, top, final_im.width - left, final_im.height - top))

        img_file = io.BytesIO()
        im.save(img_file, "PNG")
        img_file.seek(0)
        file = File(img_file, "text.png")
        await ctx.send(file=file)
        await ctx.message.delete()

    def create_wordcloud(self, text, *, file_title="wordcloud.png"):
        wc = WordCloud(width=1600, height=1200, font_path=f"{FileLocations.FONTS}/arial.ttf", mode="RGBA",
                       background_color=None,
                       colormap=random.choice(WORDCLOUD_COLOUR_SCHEMES))
        wc.generate(text)
        img = wc.to_image()
        img_file = io.BytesIO()
        img.save(img_file, "PNG")
        img_file.seek(0)
        file = File(img_file, file_title)
        return file

    @draw.group(invoke_without_command=True)
    async def wordcloud(self, ctx, *, text):
        """Draw some beautiful word clouds."""
        content = ctx.message.content
        await ctx.message.edit(content=f"{content} | creating image")
        file = self.create_wordcloud(text)
        await ctx.send(file=file)
        await ctx.message.edit(content=f"{content} | done!")

    @wordcloud.command()
    async def chat(self, ctx, target: User = None):
        """Draw word cloud from chat"""
        content = ctx.message.content
        text = []
        target = target or ctx.channel
        await ctx.message.edit(content=f"{content} | Reading your messages ԅ(≖‿≖ԅ)")
        async for message in target.history(limit=500):
            text.append(message.content)

        await ctx.message.edit(content=f"{content} | creating image")
        file = self.create_wordcloud(" ".join(text))
        await ctx.send(file=file)
        await ctx.message.edit(content=f"{content} | done!")

    @wordcloud.command()
    async def url(self, ctx, url: UrlConverter):
        """Draw a word cloud from an online source"""
        content = ctx.message.content
        await ctx.message.edit(content=f"{content} | Reading website ԅ(≖‿≖ԅ)")
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
            print(text)

        await ctx.message.edit(content=f"{content} | creating image")
        file = self.create_wordcloud(text)
        await ctx.send(file=file)
        await ctx.message.edit(content=f"{content} | done!")


def setup(bot):
    bot.add_cog(Draw(bot))
