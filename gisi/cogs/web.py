from io import BytesIO

import logging
from aiohttp import ClientConnectorError, ClientResponseError
from discord import Embed, File
from discord.ext.commands import command

from gisi.constants import Colours
from gisi.utils import UrlConverter

log = logging.getLogger(__name__)


class Web:
    """Some more or less useful web operations."""

    def __init__(self, bot):
        self.bot = bot
        self.embed_content_types = ["image"]

    @command()
    async def show(self, ctx, url: UrlConverter):
        """Show the given website.

        Send a screenshot of the website at the given url.
        """
        await ctx.message.edit(content=f"checking {url}...")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0"}
            async with self.bot.aiosession.head(url, headers=headers, allow_redirects=True) as resp:
                resp.raise_for_status()
                embed_image_url = None
                for content_type in self.embed_content_types:
                    if resp.content_type.startswith(content_type):
                        embed_image_url = resp.url
                        break
        except ClientResponseError as e:
            if e.code in (405,):
                log.warning(f"{e.code} on {url}... I'm just going to ignore it...")
            else:
                await ctx.message.edit(content=f"<{url}> **isn't a valid url ({e.code}: {e.message})**")
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
        async with self.bot.webdriver as driver:
            await ctx.message.edit(content=f"heading to {url}...")
            await driver.get(url)
            await ctx.message.edit(content=f"taking screenshot...")
            im = await driver.get_screenshot()
            title = driver.title or "No Title"
        if not im:
            await ctx.message.edit(content=f"yeah rip that didn't work...")
            return
        imdata = BytesIO()
        im.save(imdata, "png")
        imdata.seek(0)
        file = File(imdata, f"{title}.png")
        await ctx.send(f"{title} (<{url}>):", file=file)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Web(bot))
