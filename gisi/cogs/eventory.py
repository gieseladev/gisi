import eventory
from eventory.ext.discord import EventoryCog

eventory.load_ext("inktory")


def setup(bot):
    bot.add_cog(EventoryCog(bot))
