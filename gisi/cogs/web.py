import asyncio
import logging
import tempfile
from io import BytesIO
from typing import cast

from aiohttp import ClientConnectorError, ClientResponseError
from discord import Embed, File
from discord.ext import commands
from discord.ext.commands import command

from gisi.constants import Colours
from gisi.utils import UrlConverter, get_browser

log = logging.getLogger(__name__)


class WebCog(commands.Cog, name="Web"):
    """Some more or less useful web operations."""

    def __init__(self, bot):
        self.bot = bot
        self.embed_content_types = ("image",)

    @command()
    async def show(self, ctx, url: UrlConverter):
        """Show the given website.

        Send a screenshot of the website at the given url.
        """
        url = cast(str, url)

        await ctx.message.edit(content=f"checking {url}...")
        try:
            async with self.bot.aiosession.head(url, allow_redirects=True) as resp:
                resp.raise_for_status()
                if resp.content_type.startswith(self.embed_content_types):
                    embed_image_url = resp.url
                else:
                    embed_image_url = None

        except ClientResponseError as e:
            if e.status in (405,):
                log.warning(f"{e.status} on {url}... I'm just going to ignore it...")
            else:
                await ctx.message.edit(content=f"<{url}> **isn't a valid url ({e.status}: {e.message})**")
                return

        # Invalid URL is derived from ValueError
        except (ValueError, ClientConnectorError):
            await ctx.message.edit(content=f"<{url}> **isn't a valid url**")
            return

        else:
            if embed_image_url:
                url = embed_image_url.human_repr()
                em = Embed(url=url, colour=Colours.INFO)
                em.set_image(url=url)
                await ctx.message.edit(content="", embed=em)
                return

        await ctx.message.edit(content=f"waiting for driver...")

        fd, tmpname = tempfile.mkstemp()

        browser = await get_browser(self.bot.config.CHROME_WS)
        try:
            page = await browser.newPage()
            _ = asyncio.ensure_future(ctx.message.edit(content=f"heading to {url}..."))
            await page.goto(url)

            title = await page.title() or "No Title"

            _ = asyncio.ensure_future(ctx.message.edit(content=f"taking screenshot..."))
            await page.screenshot(path=tmpname, fullPage=True, omitBackground=True, type="png")
        finally:
            await browser.close()

        with open(fd, "rb") as f:
            imdata = BytesIO(f.read())

        if not imdata:
            await ctx.message.edit(content=f"yeah rip that didn't work...")
            return

        imdata.seek(0)
        file = File(imdata, f"{title}.png")
        await ctx.send(f"{title} (<{url}>):", file=file)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(WebCog(bot))
