import codecs
import io
import logging
import random

import aiohttp
import matplotlib.cm as colour_map
import numpy
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from bs4 import BeautifulSoup, Comment
from discord import File, User
from discord.ext.commands import ColourConverter, group
from wordcloud import ImageColorGenerator, WordCloud

from gisi import Gisi
from gisi.constants import Colours
from gisi.utils import FlagConverter, UrlConverter, add_embed, chunks, download_font, text_utils

log = logging.getLogger(__name__)
_default = object()

SAMPLE_SENTENCES = (
    "Two driven jocks help fax my big quiz",
    "The five boxing wizards jump quickly",
    "Sphinx of black quartz, judge my vow",
    "Pack my box with five dozen liquor jugs",
    "\"Gisi\" isn't a pangram but it looks cool"
)


class Draw:
    """You can draw but so can Gisi!"""

    def __init__(self, bot: Gisi):
        self.bot = bot
        self.font_manager = bot.fonts

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

    async def get_image(self, url):
        try:
            async with self.bot.aiosession.get(url) as resp:
                image_data = io.BytesIO(await resp.read())
            img = Image.open(image_data)
        except (OSError, aiohttp.ClientConnectorError, TypeError, ValueError):
            return None
        else:
            return img

    @group(invoke_without_command=True)
    async def fonts(self, ctx):
        """Haven't you ever wanted to mess with fonts?"""
        fonts = [font.name for font in self.font_manager]
        description = text_utils.code("\n".join(fonts), "css")
        await add_embed(ctx.message, title="Available Fonts", description=description, colour=Colours.INFO)

    @fonts.command("add", usage="[url] [flags...]")
    async def add_font(self, ctx, *flags):
        """Add a font to Gisi's repertoire
        Instead of providing the url of a font you may attach it to your message.

        Flags:
          -n | name for the new font
        """
        flags = FlagConverter.from_spec(flags)
        font_io = io.BytesIO()
        font_name = flags.get("n", None)

        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            url = attachment.url
        else:
            url = await flags.convert_dis(0, ctx, UrlConverter, default=None)
        if not url:
            await add_embed(ctx.message, description="Please either attach or provide the url to a truetype font",
                            colour=Colours.ERROR)
            return
        try:
            font_name, font_io = await download_font(self.bot.aiosession, url, name=font_name)
        except ValueError:
            await add_embed(ctx.message, description=f"Couldn't read font from url!", colour=Colours.ERROR)
            return
        except TypeError:
            await add_embed(ctx.message, description="This doesn't seem to be a valid font file...",
                            colour=Colours.ERROR)
            return

        if not font_name:
            await add_embed(ctx.message, description="Couldn't figure out the font's name", colour=Colours.ERROR)
            return

        try:
            self.font_manager.add(font_name, font_io)
        except ValueError:
            await add_embed(ctx.message, description=f"There's already a font with the name \"{font_name.title()}\"",
                            colour=Colours.ERROR)
            return

        await add_embed(ctx.message, description=f"Added new font \"{text_utils.bold(font_name.title())}\"",
                        colour=Colours.SUCCESS)

    @fonts.command("remove")
    async def remove_font(self, ctx, font):
        """Remove a font"""

        try:
            self.font_manager.remove(font)
        except KeyError:
            await add_embed(ctx.message, description="This font doesn't even exist...", colour=Colours.ERROR)
        except ValueError:
            await add_embed(ctx.message, description="You mustn't delete the default font!", colour=Colours.ERROR)
        else:
            await add_embed(ctx.message, description=f"Deleted font \"{font.title()}\"", colour=Colours.SUCCESS)

    @fonts.command("show")
    async def font_show(self, ctx, *fonts):
        """Render the fonts so you can see how they look.

        If no fonts provided, it shows all of them
        """
        MARGIN = 10
        LINE_SPACING = 5
        TITLE_SPACING = 2

        if fonts:
            font_set = set()
            for name in fonts:
                font = self.font_manager.get(name, default=None)
                if not font:
                    await add_embed(ctx.message, description=f"There's no font \"{name}\"", colour=Colours.ERROR)
                    return
                font_set.add(font)
            fonts = sorted(font_set)
        else:
            fonts = sorted(self.font_manager.fonts.values(), key=lambda f: f.name)

        images = []
        for font_chunk in chunks(fonts, 10):
            samples = []
            width = 0
            height = 0
            for name, loc in font_chunk:
                title_font = ImageFont.truetype(font=loc, size=24)
                text_font = ImageFont.truetype(font=loc, size=16)
                sample = random.choice(SAMPLE_SENTENCES)

                n_width, n_height = Draw.get_size(name, title_font)
                n_height += TITLE_SPACING
                samples.append((name, (114, 137, 218), title_font, n_height))

                t_width, t_height = Draw.get_size(sample, text_font)
                t_height += LINE_SPACING
                samples.append((sample, "white", text_font, t_height))

                width = max(width, n_width, t_width)
                height += n_height + t_height

            width += MARGIN
            height += MARGIN - LINE_SPACING
            im = Image.new("RGBA", (width, height), color=None)
            draw = ImageDraw.Draw(im)
            y = MARGIN // 2
            for text, fill, font, _height in samples:
                draw.text((MARGIN // 2, y), text, fill=fill, font=font)
                y += _height
            images.append(im)

        for im in images:
            img_file = io.BytesIO()
            im.save(img_file, "PNG")
            img_file.seek(0)
            file = File(img_file, "font.png")
            await ctx.send(file=file)

    @group(invoke_without_command=True)
    async def draw(self, ctx):
        """Drawings make the world more beautiful?"""
        pass

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

        font = (self.font_manager.get(flags.get("f", ""), False) or self.font_manager.random()).location

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

        font = (self.font_manager.get(flags.get("f", ""), False) or self.font_manager.random()).location
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

            w_diff = abs(WC_WIDTH - _width) // 2
            h_diff = abs(WC_HEIGHT - _height) // 2
            colour_func = colour_func.resize((_width, _height)).crop(
                (w_diff, h_diff, WC_WIDTH + w_diff, WC_HEIGHT + h_diff))
            colour_func = ImageColorGenerator(numpy.array(colour_func))

        wc = WordCloud(width=WC_WIDTH, height=WC_HEIGHT, mode="RGBA", background_color=None,
                       font_path=font,
                       color_func=colour_func,
                       colormap=colourmap,
                       mask=mask)

        await add_embed(ctx.message, description="creating word cloud!", colour=Colours.INFO)
        try:
            wc.generate(text)
        except ValueError:
            await add_embed(ctx.message, description="Not enough text found", colour=Colours.ERROR)
            return

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
        flags = FlagConverter.from_spec(flags)
        await add_embed(ctx.message, description=f"Reading website ԅ(≖‿≖ԅ)", colour=Colours.INFO)
        async with self.bot.aiosession.get(url) as resp:
            content_type = resp.content_type
            if not content_type.startswith("text"):
                await add_embed(ctx.message, description="Can't extract any words from \"{url}\"", colour=Colours.ERROR)
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
