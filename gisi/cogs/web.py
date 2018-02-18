import logging
from io import BytesIO

from aiohttp import ClientConnectorError, ClientResponseError
from discord import File
from discord.ext.commands import command

from gisi.utils import UrlConverter

log = logging.getLogger(__name__)


class Web:
    """Some more or less useful web operations."""

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def show(self, ctx, url: UrlConverter):
        """Show the given website.

        Send a screenshot of the website at the given url.
        """
        async with ctx.typing():
            await ctx.message.edit(content=f"checking {url}...")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0"}
                async with self.bot.aiosession.head(url, headers=headers, allow_redirects=True) as resp:
                    resp.raise_for_status()
            except ClientResponseError as e:
                await ctx.message.edit(content=f"<{url}> **isn't a valid url ({e.code}: {e.message})**")
                return
            # Invalid URL is derived from ValueError
            except (ValueError, ClientConnectorError):
                await ctx.message.edit(content=f"<{url}> **isn't a valid url**")
                return

        await ctx.message.edit(content=f"waiting for driver...")
        async with self.bot.webdriver as driver:
            await ctx.message.edit(content=f"heading to {url}...")
            await driver.get(url)
            await ctx.message.edit(content=f"taking screenshot...")
            im = await driver.get_screenshot()
            title = driver.title or "No Title"
        imdata = BytesIO()
        im.save(imdata, "png")
        imdata.seek(0)
        file = File(imdata, f"{title}.png")
        await ctx.send(f"{title} (<{url}>):", file=file)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Web(bot))
