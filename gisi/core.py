import inspect
import itertools
import logging
import time
from datetime import timedelta

from discord import Embed
from discord.ext.commands import Command, HelpFormatter, command

from .constants import Colours, Info, Sources
from .signals import GisiSignal
from .utils import EmbedPaginator, copy_embed, text_utils

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
            em = Embed(description=f"No command called **{name}**", colour=Colours.ERROR)
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
                    await _command_not_found(name)
                    return

            embeds = await self.formatter.format_help_for(ctx, cmd)
        else:
            # handle groups
            name = commands[0]
            cmd = bot.all_commands.get(name)
            if cmd is None:
                await _command_not_found(name)
                return

            for key in commands[1:]:
                try:
                    cmd = cmd.commands.get(key)
                    if cmd is None:
                        await _command_not_found(key)
                        return
                except AttributeError:
                    em = Embed(description=f"Command **{cmd.name}** has no subcommands", colour=Colours.ERROR)
                    await ctx.send(embed=em)
                    return

            embeds = await self.formatter.format_help_for(ctx, cmd)

        for embed in embeds:
            await ctx.send(embed=embed)


class GisiHelpFormatter(HelpFormatter):
    async def format(self):
        every_embed = Embed(colour=0x15ba00)
        first_embed = copy_embed(every_embed)
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
