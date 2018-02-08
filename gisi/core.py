import logging
import time
from datetime import timedelta

from discord import Embed
from discord.ext.commands import command

from .constants import Colours, Sources
from .signals import GisiSignal

log = logging.getLogger(__name__)


class Core:
    def __init__(self, bot):
        self.bot = bot

    @command()
    async def shutdown(self, ctx):
        log.warning("shutting down!")
        await self.bot.signal(GisiSignal.SHUTDOWN)

    @command()
    async def restart(self, ctx):
        log.warning("restarting!")
        await self.bot.signal(GisiSignal.RESTART)

    @command()
    async def status(self, ctx):
        em = Embed(title="Gisi Status", colour=Colours.INFO)
        em.add_field(name="Ping", value=f"🌀")
        em.add_field(name="WS ping", value=f"{round(1000 * self.bot.latency, 2)}ms")
        uptime = timedelta(seconds=round(self.bot.uptime))
        em.add_field(name="Uptime", value=f"{uptime}")
        em.set_thumbnail(url=Sources.GISI_AVATAR)

        pre = time.time()
        await ctx.message.edit(embed=em)
        delay = time.time() - pre

        em.set_field_at(0, name="Ping", value=f"{round(1000 * delay, 2)}ms")
        await ctx.message.edit(embed=em)
