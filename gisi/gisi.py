import logging
import os
import sys
import time
from datetime import datetime

from aiohttp import ClientSession
from discord import AsyncWebhookAdapter, Embed, Status, Webhook
from discord.ext.commands import AutoShardedBot, CommandInvokeError
from motor.motor_asyncio import AsyncIOMotorClient

from . import utils
from .config import Config
from .constants import Colours, FileLocations, Info
from .core import Core
from .signals import GisiSignal
from .utils import WebDriver

log = logging.getLogger(__name__)


async def before_invoke(ctx):
    pre = len(ctx.prefix + ctx.invoked_with)
    if ctx.invoked_subcommand is not None:
        # add 1 to account for the space between cmd and subcmd
        pre += len(ctx.subcommand_passed) + 1
    ctx.clean_content = ctx.message.content[pre:]
    ctx.invocation_content = ctx.message.content[:pre]


class Gisi(AutoShardedBot):

    def __init__(self):
        self.config = Config.load()
        super().__init__(self.config.command_prefix,
                         description=Info.desc,
                         status=Status.idle,
                         self_bot=True)

        self._signal = None
        self.start_at = time.time()

        self._before_invoke = before_invoke

        self.mongo_client = AsyncIOMotorClient(self.config.mongodb_uri)
        self.aiosession = ClientSession(headers={
            "User-Agent": f"{Info.name}/{Info.version}"
        }, loop=self.loop)
        self.webdriver = WebDriver(kill_on_exit=False)
        self.webhook = Webhook.from_url(self.config.webhook_url, adapter=AsyncWebhookAdapter(
            self.aiosession)) if self.config.webhook_url else None

        self.add_cog(Core(self))

        self.load_exts()
        log.info("Gisi setup!")

    def __str__(self):
        return f"<{Info.name}>"

    @property
    def uptime(self):
        return time.time() - self.start_at

    def load_exts(self):
        for extension in os.listdir(FileLocations.COGS):
            if extension.endswith(".py"):
                ext_name = extension[:-3]
                ext_package = f"{__package__}.cogs.{ext_name}"
                try:
                    self.load_extension(ext_package)
                except Exception:
                    log.exception(f"Couldn't load extension. ({ext_name})")
                else:
                    log.debug(f"loaded extension {ext_name}")
        log.info(f"loaded {len(self.extensions)} extensions")

    async def signal(self, signal):
        if not isinstance(signal, GisiSignal):
            raise ValueError(f"signal must be of type {GisiSignal}, not {type(signal)}")
        self._signal = signal
        await self.logout()

    async def logout(self):
        log.info("logging out")
        self.dispatch("logout")
        await super().logout()

    async def run(self):
        return await self.start(self.config.token, bot=False)

    async def on_ready(self):
        await self.webdriver.spawn()
        log.info("ready!")

    async def on_logout(self):
        log.debug("closing stuff")
        await self.aiosession.close()
        self.webdriver.close()

    async def on_command(self, ctx):
        log.info(f"triggered command {ctx.command}")

    async def on_error(self, event_method, *args, **kwargs):
        log.exception("Client error")
        if self.webhook:
            args = "\n".join([f"{arg}" for arg in args])
            kwargs = "\n".join([f"{key}: {value}" for key, value in kwargs.items()])
            ctx_em = Embed(title="Context Info", timestamp=datetime.now(), colour=Colours.ERROR_INFO,
                           description=f"event: **{event_method}**\nArgs:```\n{args}```\nKwargs:```\n{kwargs}```")

            exc_em = utils.embed.create_exception_embed(*sys.exc_info(), 8)
            await self.webhook.send(embeds=[ctx_em, exc_em])

    async def on_command_error(self, context, exception):
        log.error(f"Command error {context} / {exception}")

        if self.webhook:
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
            await self.webhook.send(embeds=[ctx_em, exc_em])
