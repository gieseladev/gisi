import asyncio
import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from functools import partial, wraps
from io import BytesIO
from threading import Lock

from PIL import Image
from selenium.webdriver import Firefox, FirefoxOptions, FirefoxProfile

from gisi.constants import FileLocations

log = logging.getLogger(__name__)


class UserAgents(Enum):
    ANDROID = "Mozilla/5.0 (Linux; Android 4.3; Nexus 7 Build/JSS15Q) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2307.2 Mobile Safari/537.36"
    DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0"


def run_in_executor(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return self.loop.run_in_executor(self.executor, partial(func, self, *args, **kwargs))

    return wrapper


class WebDriver:
    def __init__(self, user_agent=UserAgents.DESKTOP, *, loop=None, executor=None, max_workers=3, kill_on_exit=True):
        self.driver = None
        self.user_agent = user_agent

        self.loop = loop or asyncio.get_event_loop()
        self.executor = executor or ThreadPoolExecutor(max_workers)
        self.kill_on_exit = kill_on_exit
        self.lock = asyncio.Lock()
        self.spawn_lock = Lock()

    def __str__(self):
        return f"<WebDriver {self.driver}>"

    def __getattr__(self, item):
        return getattr(self.driver, item)

    async def __aenter__(self):
        await self.spawn()
        await self.lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.kill_on_exit:
            self.close()
        self.lock.release()

    @run_in_executor
    def spawn(self):
        with self.spawn_lock:
            if self.driver:
                return
            log.debug("spawning driver...")
            profile = FirefoxProfile()
            ua = self.user_agent.value if isinstance(self.user_agent, UserAgents) else str(self.user_agent)
            profile.set_preference("general.useragent.override", ua)
            options = FirefoxOptions()
            options.set_headless()
            self.driver = Firefox(firefox_profile=profile, firefox_options=options, log_path=FileLocations.GECKO_LOG)
            atexit.register(self.close)
            log.debug(f"spawned driver {self.driver}")

    def close(self):
        if not self.driver:
            return
        try:
            self.driver.close()
        except ConnectionRefusedError:
            log.warning("No idea what exactly happened, but couldn't close driver!")
        else:
            log.debug(f"killed driver {self.driver}")
        finally:
            self.driver = None
            atexit.unregister(self.close)

    @run_in_executor
    def get(self, url):
        self.driver.get(url)

    @run_in_executor
    def get_screenshot(self, size=(1280, 720)):
        current_size = self.get_window_size()

        self.set_window_size(*size)
        raw_data = self.get_screenshot_as_png()
        if not raw_data:
            return None
        data = BytesIO(raw_data)
        im = Image.open(data)

        self.set_window_size(**current_size)
        return im
