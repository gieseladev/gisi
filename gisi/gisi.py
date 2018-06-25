import asyncio
import atexit
import logging
import os
import time

from aiohttp import ClientSession
from discord import AsyncWebhookAdapter, Status, Webhook
from discord.ext.commands import AutoShardedBot
from motor.motor_asyncio import AsyncIOMotorClient
from raven import Client
from raven.handlers.logging import SentryHandler

from .config import Config
from .constants import FileLocations, Info
from .core import Core
from .signals import GisiSignal
from .stats import Statistics
from .utils import FontManager, WebDriver

log = logging.getLogger(__name__)

sentry_client = Client(release=Info.version)
sentry_handler = SentryHandler(sentry_client)
sentry_handler.setLevel(logging.ERROR)

for logger in [None, "gisi"]:
    logging.getLogger(logger).addHandler(sentry_handler)


async def before_invoke(ctx):
    pre = len(ctx.prefix + ctx.command.qualified_name)
    ctx.clean_content = ctx.message.content[pre + 1:]
    ctx.invocation_content = ctx.message.content[:pre]


class Gisi(AutoShardedBot):

    def __init__(self):
        self.config = Config.load()
        super().__init__(self.config.COMMAND_PREFIX,
                         description=Info.desc,
                         self_bot=True)

        self._signal = None
        self.start_at = time.time()

        self._before_invoke = before_invoke

        self.mongo_client = AsyncIOMotorClient(self.config.MONGO_URI)
        self.mongo_db = self.mongo_client[self.config.MONGO_DATABASE]
        self.aiosession = ClientSession(headers={
            "User-Agent": f"{Info.name}/{Info.version}"
        }, loop=self.loop)
        self.webdriver = WebDriver(kill_on_exit=False)
        self.webhook = Webhook.from_url(self.config.WEBHOOK_URL, adapter=AsyncWebhookAdapter(self.aiosession)) if self.config.WEBHOOK_URL else None

        self.statistics = Statistics(self)
        self.add_cog(self.statistics)
        self.fonts = FontManager(self)
        self.add_cog(Core(self))

        self.unloaded_extensions = []
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
                except Exception as e:
                    self.unloaded_extensions.append((ext_name, ext_package, e))
                    log.exception(f"Couldn't load extension. ({ext_name})")
                else:
                    log.debug(f"loaded extension {ext_name}")
        log.info(f"loaded {len(self.extensions)} extensions")

    async def signal(self, signal):
        if not isinstance(signal, GisiSignal):
            raise ValueError(f"signal must be of type {GisiSignal}, not {type(signal)}")
        self._signal = signal
        await self.logout()

    async def blocking_dispatch(self, event, *args, **kwargs):
        method = f"on_{event}"
        handler = f"handle_{event}"
        tasks = []

        listeners = self._listeners.get(event)
        if listeners:
            removed = []
            for i, (future, condition) in enumerate(listeners):
                if future.cancelled():
                    removed.append(i)
                    continue

                try:
                    result = condition(*args)
                except Exception as e:
                    future.set_exception(e)
                    removed.append(i)
                else:
                    if result:
                        if len(args) == 0:
                            future.set_result(None)
                        elif len(args) == 1:
                            future.set_result(args[0])
                        else:
                            future.set_result(args)
                        removed.append(i)

            if len(removed) == len(listeners):
                self._listeners.pop(event)
            else:
                for idx in reversed(removed):
                    del listeners[idx]

        try:
            actual_handler = getattr(self, handler)
        except AttributeError:
            pass
        else:
            actual_handler(*args, **kwargs)

        try:
            coro = getattr(self, method)
        except AttributeError:
            pass
        else:
            tasks.append(asyncio.ensure_future(self._run_event(coro, method, *args, **kwargs), loop=self.loop))

        for event in self.extra_events.get(method, []):
            coro = self._run_event(event, event, *args, **kwargs)
            tasks.append(asyncio.ensure_future(coro, loop=self.loop))
        await asyncio.gather(*tasks, loop=self.loop)

    async def logout(self):
        log.info("logging out")
        await self.blocking_dispatch("logout")
        await super().logout()

    async def run(self):
        atexit.register(self.loop.run_until_complete, self.logout())
        return await self.start(self.config.TOKEN, bot=False)

    async def on_ready(self):
        await self.change_presence(status=Status.idle, afk=True)
        await self.webdriver.spawn()
        log.info("ready!")

    async def on_logout(self):
        log.debug("closing stuff")
        await self.aiosession.close()
        self.webdriver.close()
