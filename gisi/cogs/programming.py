import json
import logging
import textwrap
import traceback

from discord import Embed
from discord.ext.commands import command

from gisi.constants import Colours
from gisi.utils import hastebin, text_utils

log = logging.getLogger(__name__)


class Programming:
    """Programming for the cool kids"""

    def __init__(self, bot):
        self.bot = bot
        self.aiosession = bot.aiosession

    @command(usage="<instructions>")
    async def eval(self, ctx):
        """A simple eval command which evaluates the given instructions.

        To be honest it actually executes them but uhm... bite me!
        """
        inst = textwrap.indent(ctx.clean_content, "\t")
        statement = f"out = []\ndef print(*args):\n\tout.append(\" \".join(str(arg) for arg in args))\nasync def func():\n{inst}"
        env = {**globals(), **locals()}

        em = Embed(
            title="Parsing",
            description=text_utils.code(ctx.clean_content, "python"),
            colour=0xffff80
        )
        await ctx.message.edit(content="", embed=em)

        try:
            exec(statement, env)
        except SyntaxError as e:
            em.colour = Colours.ERROR
            em.add_field(
                name="Syntax Error",
                value="".join(traceback.format_exception_only(type(e), e))
            )
            log.exception("Here's the detailed syntax error:")
            await ctx.message.edit(embed=em)
            return
        func = env["func"]

        em.title = "Executing..."
        em.colour = 0xff9900
        await ctx.message.edit(embed=em)

        try:
            ret = await func()
            out = env["out"]
        except BaseException as e:
            em.colour = Colours.ERROR
            em.add_field(
                name="Error",
                value="".join(traceback.format_exception_only(type(e), e))
            )
            log.exception("Here's the detailed syntax error:")
            await ctx.message.edit(embed=em)
            return

        em.title = "Done"
        em.colour = Colours.SUCCESS
        if str(ret):
            try:
                raw_result = json.dumps(ret, indent=2)
                result = text_utils.code(raw_result, "json")
            except TypeError:
                raw_result = result = str(ret)
            if len(result) > 1024:
                link = await hastebin.upload(self.aiosession, raw_result)
                em.url = link
                result = f"The result is too big. [Here's a link to Hastebin]({link})"
            em.add_field(
                name="Result",
                value=result
            )
        if out:
            result = "\n".join(out)
            if len(result) > 1024:
                link = await hastebin.upload(self.aiosession, result)
                result = f"The Output is too big. [Here's a link to Hastebin]({link})"
            em.add_field(
                name="Output",
                value=result
            )

        await ctx.message.edit(embed=em)


def setup(bot):
    bot.add_cog(Programming(bot))
