import eventory
from discord.ext.commands import Bot
from eventory.ext.discord import EventoryCog

from gisi.constants import FileLocations

eventory.load_ext("inktory")


def setup(bot: Bot):
    bot.add_cog(EventoryCog(bot, directory=FileLocations.EVENTORY))
