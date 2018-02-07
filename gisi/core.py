import logging

from discord.ext.commands import command

from .signals import RestartSignal, ShutdownSignal

log = logging.getLogger(__name__)


class Core:
    def __init__(self, bot):
        self.bot = bot

    @command()
    async def shutdown(self, ctx):
        log.warning("shutting down!")
        raise ShutdownSignal

    @command()
    async def restart(self, ctx):
        log.warning("restarting!")
        raise RestartSignal
