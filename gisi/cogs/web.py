import logging
from io import BytesIO

from aiohttp import ClientConnectorError
from aiohttp.http_exceptions import InvalidURLError
from discord import File
from discord.ext.commands import command

from gisi.utils import UrlConverter

log = logging.getLogger(__name__)


class Web:
    def __init__(self, bot):
        self.bot = bot

    @command()
    async def show(self, ctx, url: UrlConverter):
        async with ctx.typing():
            await ctx.message.edit(content=f"checking {url}...")
            try:
                async with self.bot.aiosession.head(url, allow_redirects=True) as resp:
                    resp.raise_for_status()
            except (InvalidURLError, ClientConnectorError):
                await ctx.message.edit(content=f"<{url}> **isn't a valid url**")
                return

        async with self.bot.webdriver as driver:
            await ctx.message.edit(content=f"heading to {url}...")
            await driver.get(url)
            await ctx.message.edit(content=f"taking screenshot...")
            im = await driver.get_screenshot()
            title = driver.title
        imdata = BytesIO()
        im.save(imdata, "png")
        imdata.seek(0)
        file = File(imdata, f"{title}.png")
        await ctx.send(f"{title} (<{url}>):", file=file)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Web(bot))
