import codecs
import logging

from discord import Embed
from discord.embeds import EmptyEmbed
from discord.ext.commands import BadArgument, command
from discord.ext.commands.converter import ColourConverter

from gisi.constants import Colours
from gisi.utils import FlagConverter, add_embed

log = logging.getLogger(__name__)


class Message:
    """Commands related to messages."""

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def quote(self, ctx, query):
        """Search for a message by its content and quote it."""
        query = query.lower()
        message = None
        async for message in ctx.history(before=ctx.message, limit=10000):
            if query in message.content.lower():
                break
        if not message:
            await add_embed(ctx.message, description=f"Couldn't find a message that matched the query",
                            colour=Colours.ERROR)
            return
        await add_embed(ctx.message, author=message.author, description=message.content, colour=Colours.INFO,
                        timestamp=message.created_at)

    @command(usage="[content] [flags]")
    async def embed(self, ctx, *flags):
        """Make an embed

        Flags:
          -t  <title>
          -c  <colour>
          -a  <author name>
          -ai <author image url>
          -au <author url>
          -u  <embed url>
          -i  <image url>
          -ti <thumbnail url>
          -f  <footer text>
          -fi <footer image url>
        """
        flags = FlagConverter.from_spec(flags, flag_arg_default=EmptyEmbed)
        description = flags.get(0, EmptyEmbed)
        if description:
            description = codecs.unicode_escape_decode(description)[0]
        colour = flags.get("c", EmptyEmbed)
        if colour:
            try:
                colour = await ColourConverter.convert(None, None, colour)
            except BadArgument:
                colour = EmptyEmbed
        image = flags.get("i", False)
        thumbnail = flags.get("ti", False)
        author = flags.get("a", False)
        em = Embed(title=flags.get("t", EmptyEmbed), description=description,
                   url=flags.get("u", EmptyEmbed), colour=colour)
        if image:
            em.set_image(url=image)
        if thumbnail:
            em.set_thumbnail(url=thumbnail)
        if author:
            em.set_author(name=author, url=flags.get("au", EmptyEmbed), icon_url=flags.get("ai", EmptyEmbed))

        em.set_footer(text=flags.get("f", EmptyEmbed), icon_url=flags.get("fi", EmptyEmbed))

        await ctx.message.edit(content="", embed=em)


def setup(bot):
    bot.add_cog(Message(bot))
