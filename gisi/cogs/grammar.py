import logging

from discord.ext.commands import group

from gisi import SetDefaults

log = logging.getLogger(__name__)


class Grammar:
    def __init__(self, bot):
        self.bot = bot
        self.aiosession = bot.aiosession

    async def check_grammar(self, text):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        params = {
            "text": text,
            "language": "auto",
            "preferredVariants": "en-GB, de-CH"
        }
        async with self.aiosession.post("https://languagetool.org/api/v2/check", headers=headers,
                                        data=params) as resp:
            data = await resp.json()

        new_text = list(text)
        if data["matches"]:
            offset_index = 0
            for match in data["matches"]:
                start = match["offset"] + offset_index
                old_len = match["length"]
                end = start + old_len
                new = match["replacements"][0]["value"]
                new_len = len(new)
                diff = new_len - old_len
                offset_index += diff
                new_text[start:end] = new

        return "".join(new_text)

    async def check_message(self, msg, content):
        new_content = await self.check_grammar(content)
        if msg.content != new_content:
            await msg.edit(content=new_content)

    @group()
    async def grammar(self, ctx):
        pass

    @grammar.command()
    async def check(self, ctx, *, content):
        await self.check_message(ctx.message, content)

    @grammar.command()
    async def enable(self, ctx):
        self.bot.config.grammar_check_enabled = True
        await ctx.message.edit(content=f"{ctx.message.content} (enabled)")

    @grammar.command()
    async def disable(self, ctx):
        self.bot.config.grammar_check_enabled = False
        await ctx.message.edit(content=f"{ctx.message.content} (disabled)")

    async def on_message(self, message):
        if message.author != self.bot.user:
            return
        if self.bot.config.grammar_check_enabled:
            await self.check_message(message, message.content)


def setup(bot):
    SetDefaults({
        "grammar_check_enabled": False
    })
    bot.add_cog(Grammar(bot))
