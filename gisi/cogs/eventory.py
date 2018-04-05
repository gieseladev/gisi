import logging

import eventory
from discord.ext.commands import Context, group
from eventory import Eventorial
from eventory.ext.discord import DiscordEventarrator

eventory.load_ext("inktory")

log = logging.getLogger(__name__)


class Eventory:
    """Eventoryyyy."""

    def __init__(self, bot):
        self.bot = bot
        self.eventorial = Eventorial(loop=self.bot.loop)

    @group()
    async def eventory(self, ctx: Context):
        """Eventory ye."""
        await self.eventorial.load("https://raw.githubusercontent.com/siku2/Eventory/master/tests/the_intercept.evory")
        eventory = self.eventorial.get("The Intercept")
        instructor = eventory.narrate(DiscordEventarrator(self.bot, ctx.channel))
        await instructor.play()


def setup(bot):
    bot.add_cog(Eventory(bot))
