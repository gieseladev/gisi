import inspect
import itertools
import logging
import time
from datetime import timedelta

from discord import Embed
from discord.ext.commands import Command, HelpFormatter, command

from .constants import Colours, Info, Sources
from .signals import GisiSignal
from .utils import text_utils

log = logging.getLogger(__name__)


class Core:
    """Some veeery important operations for Gisi."""

    def __init__(self, bot):
        self.bot = bot

        self.bot.remove_command("help")
        self.formatter = GisiHelpFormatter()

    @command()
    async def shutdown(self, ctx):
        """Shutdown.

        What do you expect...?
        """
        log.warning("shutting down!")
        await self.bot.signal(GisiSignal.SHUTDOWN)

    @command()
    async def restart(self, ctx):
        """Restart.

        Keep in mind that this doesn't reload the code.
        """
        log.warning("restarting!")
        await self.bot.signal(GisiSignal.RESTART)

    @command()
    async def status(self, ctx):
        """Get some status help.

        It really just prints a lot of information for no real use.
        """
        em = Embed(title=f"{Info.name} Status", colour=Colours.INFO)
        em.add_field(name="Version", value=f"{Info.version}-{Info.release}")
        em.add_field(name="Ping", value=f"🌀")
        em.add_field(name="WS ping", value=f"{round(1000 * self.bot.latency, 2)}ms")
        uptime = timedelta(seconds=round(self.bot.uptime))
        em.add_field(name="Uptime", value=f"{uptime}")
        em.set_thumbnail(url=Sources.GISI_AVATAR)

        pre = time.time()
        await ctx.message.edit(embed=em)
        delay = time.time() - pre

        em.set_field_at(1, name="Ping", value=f"{round(1000 * delay, 2)}ms")
        await ctx.message.edit(embed=em)

    @command()
    async def help(self, ctx, *commands):
        """Help me

        [p]help [Category]
        [p]help [Command]

        Just use whatever you want ¯\_(ツ)_/¯
        """

        async def _command_not_found(name):
            em = Embed(colour="red")
            await ctx.send(embed=em)

        bot = ctx.bot
        if len(commands) == 0:
            embeds = await self.formatter.format_help_for(ctx, bot)
        elif len(commands) == 1:
            # try to see if it is a cog name
            name = commands[0]
            if name in bot.cogs:
                cmd = bot.cogs[name]
            else:
                cmd = bot.all_commands.get(name)
                if cmd is None:
                    await ctx.send(bot.command_not_found.format(name))
                    return

            embeds = await self.formatter.format_help_for(ctx, cmd)
        else:
            # handle groups
            name = commands[0]
            cmd = bot.commands.get(name)
            if cmd is None:
                await ctx.send(bot.command_not_found.format(name))
                return

            for key in commands[1:]:
                try:
                    cmd = cmd.commands.get(key)
                    if cmd is None:
                        await ctx.send(bot.command_not_found.format(key))
                        return
                except AttributeError:
                    await ctx.send(bot.command_has_no_subcommands.format(command, key))
                    return

            embeds = await self.formatter.format_help_for(ctx, cmd)

        for embed in embeds:
            await ctx.send(embed=embed)


class EmbedPaginator:
    MAX_FIELDS = 25
    MAX_FIELD_NAME = 256
    MAX_FIELD_VALUE = 1024
    MAX_TOTAL = 6000

    def __init__(self, *, first_embed=None, every_embed=None):
        self.first_embed = first_embed
        self.every_embed = every_embed

        self._cur_embed = self.copy_embed(first_embed) if first_embed else self.create_embed()
        self._embeds = []

    def __str__(self):
        return f"<EmbedPaginator>"

    def __iter__(self):
        return iter(self.embeds)

    @property
    def predefined_count(self):
        em = self._cur_embed
        return len(em.title or "") + len(em.description or "") + len(em.author.name or "") + len(em.footer.text or "")

    @property
    def total_count(self):
        return self.predefined_count + sum(len(field.name) + len(field.value) for field in self._cur_embed.fields)

    @property
    def embeds(self):
        self.close_embed()
        return self._embeds

    @classmethod
    def copy_embed(cls, embed):
        return Embed.from_data(embed.to_dict())

    def create_embed(self):
        return self.copy_embed(self.every_embed)

    def close_embed(self):
        self._embeds.append(self._cur_embed)
        self._cur_embed = self.create_embed()

    def add_field(self, name, value, inline=False):
        if len(name) > self.MAX_FIELD_NAME:
            raise ValueError(f"Field name mustn't be longer than {self.MAX_FIELD_NAME} characters")
        if len(value) > self.MAX_FIELD_VALUE:
            raise ValueError(f"Field value mustn't be longer than {self.MAX_FIELD_VALUE} characters")
        count = len(name) + len(value)
        if self.total_count + count > self.MAX_TOTAL:
            self.close_embed()
        em = self._cur_embed
        em.add_field(name=name, value=value, inline=inline)
        if len(em.fields) >= self.MAX_FIELDS:
            self.close_embed()


class GisiHelpFormatter(HelpFormatter):
    async def format(self):
        every_embed = Embed(colour=0x15ba00)
        first_embed = EmbedPaginator.copy_embed(every_embed)
        first_embed.title = f"{Info.name} Help"

        description = self.command.description if not self.is_cog() else inspect.getdoc(self.command)
        if description:
            first_embed.description = description

        paginator = EmbedPaginator(first_embed=first_embed, every_embed=every_embed)

        def get_commands_text(commands):
            max_width = self.max_name_size
            value = ""
            for name, cmd in commands:
                if name in cmd.aliases:
                    # skip aliases
                    continue

                entry = f"{name:<{max_width}} | {cmd.short_doc}"
                shortened = self.shorten(entry)
                value += shortened + "\n"
            return value

        def get_final_embeds():
            embeds = paginator.embeds
            embeds[-1].set_footer(text=self.get_ending_note(), icon_url=embeds[-1].footer.icon_url)
            return embeds

        if isinstance(self.command, Command):
            # <signature portion>
            signature = self.get_command_signature()
            paginator.add_field("Syntax", text_utils.code(signature, "fix"))

            # <long doc> section
            if self.command.help:
                paginator.add_field("Help", text_utils.code(self.command.help, "css"))

            # end it here if it's just a regular command
            if not self.has_subcommands():
                return get_final_embeds()

        def category(tup):
            cog = tup[1].cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ":" if cog is not None else "\u200bNo Category:"

        if self.is_bot():
            data = sorted(await self.filter_command_list(), key=category)
            for category, commands in itertools.groupby(data, key=category):
                # there simply is no prettier way of doing this.
                commands = list(commands)
                if len(commands) > 0:
                    name = category

                value = get_commands_text(commands)
                paginator.add_field(name, text_utils.code(value, "css"))
        else:
            value = get_commands_text(await self.filter_command_list())
            paginator.add_field("Commands", text_utils.code(value, "css"))

        return get_final_embeds()
