import logging
import os
import time

from aiohttp import ClientSession
from discord import AsyncWebhookAdapter, Status, Webhook
from discord.ext.commands import AutoShardedBot
from motor.motor_asyncio import AsyncIOMotorClient

from .config import Config
from .constants import FileLocations, Info
from .core import Core
from .signals import GisiSignal
from .stats import Statistics
from .utils import WebDriver

log = logging.getLogger(__name__)


async def before_invoke(ctx):
    pre = len(ctx.prefix + ctx.command.qualified_name)
    ctx.clean_content = ctx.message.content[pre + 1:]
    ctx.invocation_content = ctx.message.content[:pre]


class Gisi(AutoShardedBot):

    def __init__(self):
        self.config = Config.load()
        super().__init__(self.config.command_prefix,
                         description=Info.desc,
                         self_bot=True)

        self._signal = None
        self.start_at = time.time()

        self._before_invoke = before_invoke

        self.mongo_client = AsyncIOMotorClient(self.config.mongodb_uri)
        self.mongo_db = self.mongo_client[Info.name.lower()]
        self.aiosession = ClientSession(headers={
            "User-Agent": f"{Info.name}/{Info.version}"
        }, loop=self.loop)
        self.webdriver = WebDriver(kill_on_exit=False)
        self.webhook = Webhook.from_url(self.config.webhook_url, adapter=AsyncWebhookAdapter(
            self.aiosession)) if self.config.webhook_url else None

        self.statistics = Statistics(self)
        self.add_cog(self.statistics)
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
        await self.change_presence(status=Status.idle, afk=True)
        await self.webdriver.spawn()
        log.info("ready!")

    async def on_logout(self):
        log.debug("closing stuff")
        await self.aiosession.close()
        self.webdriver.close()
