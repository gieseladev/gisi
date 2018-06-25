import inspect
import itertools
import logging
import sys
import time
from datetime import datetime, timedelta

from discord import Embed
from discord.ext.commands import Command, CommandInvokeError, CommandNotFound, HelpFormatter, command, \
    group

from . import utils
from .constants import Colours, Info, Sources
from .signals import GisiSignal
from .utils import EmbedPaginator, FlagConverter, copy_embed, text_utils, version

log = logging.getLogger(__name__)


class Core:
    """Some veeery important operations for Gisi."""

    def __init__(self, bot):
        self.bot = bot

        self.bot.remove_command("help")
        self.formatter = GisiHelpFormatter(width=60)

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

    @group()
    async def version(self, ctx):
        """Display some very nice version information?"""
        if ctx.invoked_subcommand:
            return

        changelog = await version.get_changelog(self.bot.aiosession)
        current_versionstamp = version.VersionStamp.from_timestamp(Info.version)

        title = "You're up to date!" if current_versionstamp == changelog.current_version.version else "There's a new version available!"

        em = Embed(title=title, colour=Colours.INFO)
        em.add_field(name="Local Version", value=f"{Info.version_name}\n{Info.version}-{Info.release}")
        em.add_field(name="Remote Version",
                     value=f"{changelog.current_version.name}\n{changelog.current_version.version}")
        await ctx.message.edit(embed=em)

    @version.command(signature="changes [flags]")
    async def changes(self, ctx, *flags):
        """Show all changes that match the given filters

        Flags:
          -v <version> | min version
          -t <type>    | min type
          -n <number>  | max number
        """
        flags = FlagConverter.from_spec(flags, flag_arg_default=None)
        filters = {
            "min_version": flags.convert("v", version.VersionStamp.from_timestamp, None),
            "min_type": flags.convert("t", lambda t: version.ChangeType[t.upper()], None),
            "max_entries": flags.convert("n", int, None)
        }

        if not any(filters.values()):
            filters["min_version"] = version.VersionStamp.from_timestamp(Info.version)

        filters["max_entries"] = filters["max_entries"] or 10

        changelog = await version.get_changelog(self.bot.aiosession)
        filtered = list(changelog.filter_history(**filters))
        if not filtered:
            await ctx.message.edit(content=f"{ctx.message.content} | **Nothing to show**")
            return
        every_embed = Embed(colour=Colours.INFO)
        paginator = EmbedPaginator(every_embed=every_embed)
        for entry in filtered:
            paginator.add_field(name=entry.change,
                                value=f"`{entry.version.timestamp}` | {entry.change_type.name.lower()}")

        embeds = paginator.embeds
        for embed in embeds:
            await ctx.send(embed=embed)

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
                    cmd = cmd.all_commands.get(key)
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

    async def on_ready(self):
        if self.bot.webhook and self.bot.unloaded_extensions:
            embeds = []
            for name, package, exc in self.bot.unloaded_extensions:
                exc_type = type(exc)
                exc_msg = str(exc)
                exc_tb = exc.__traceback__
                em = utils.embed.create_exception_embed(exc_type, exc_msg, exc_tb, 8)
                em.title = f"Couldn't load extension \"{name}\" ({package})"
                embeds.append(em)
            await self.bot.webhook.send(embeds=embeds)

    async def on_command(self, ctx):
        log.info(f"triggered command {ctx.command}")

    async def on_error(self, event_method, *args, **kwargs):
        log.exception("Client error", exc_info=True)
        if self.bot.webhook:
            args = "\n".join([f"{arg}" for arg in args])
            kwargs = "\n".join([f"{key}: {value}" for key, value in kwargs.items()])
            ctx_em = Embed(title="Context Info", timestamp=datetime.now(), colour=Colours.ERROR_INFO,
                           description=f"event: **{event_method}**\nArgs:```\n{args}```\nKwargs:```\n{kwargs}```")

            exc_em = utils.embed.create_exception_embed(*sys.exc_info(), 8)
            await self.bot.webhook.send(embeds=[ctx_em, exc_em])

    async def on_command_error(self, context, exception):
        if isinstance(exception, CommandNotFound):
            log.debug(f"ignoring unknown command {context.message.content}")
            return

        log.error(f"Command error {context} / {exception}", exc_info=True)

        if self.bot.webhook:
            ctx_em = Embed(title="Context Info", timestamp=datetime.now(), colour=Colours.ERROR_INFO,
                           description=f"cog: **{type(context.cog).__qualname__}**\nguild: **{context.guild}**\nchannel: **{context.channel}**\nauthor: **{context.author}**")
            ctx_em.add_field(name="Message",
                             value=f"id: **{context.message.id}**\ncontent:```\n{context.message.content}```",
                             inline=False)
            args = "\n".join([f"{arg}" for arg in context.args])
            kwargs = "\n".join([f"{key}: {value}" for key, value in context.kwargs.items()])
            ctx_em.add_field(name="Command",
                             value=f"name: **{context.command.name if context.command else context.command}**\nArgs:```\n{args}```\nKwargs:```\n{kwargs}```",
                             inline=False)

            if isinstance(exception, CommandInvokeError):
                exc_type = type(exception.original)
                exc_msg = str(exception.original)
                exc_tb = exception.original.__traceback__
            else:
                exc_type = type(exception)
                exc_msg = str(exception)
                exc_tb = exception.__traceback__

            exc_em = utils.embed.create_exception_embed(exc_type, exc_msg, exc_tb, 8)
            await self.bot.webhook.send(embeds=[ctx_em, exc_em])


class GisiHelpFormatter(HelpFormatter):
    async def format(self):
        every_embed = Embed(colour=Colours.INFO)
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
