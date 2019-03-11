import logging
from typing import List, Optional

import pyppeteer
from pyppeteer.browser import Browser

log = logging.getLogger(__name__)


async def get_browser(chrome_ws: Optional[str], *, args: List[str] = None, **options) -> Browser:
    """Get a `Browser` instance.

    Args:
        chrome_ws: Remote chrome puppet to control, if `None`, a local instance is spawned.
        args: List of arguments to be passed to Chrome. If `None` a few default arguments are
            used.
        **options: Keyword arguments passed to the pyppeteer functions.
    """
    if args is None:
        args = [
            "--window-size=1920x1080",
        ]

    if chrome_ws:
        qs = "?" + "&".join(args) if args else ""
        return await pyppeteer.connect(browserWSEndpoint=chrome_ws + qs, **options)
    else:
        return await pyppeteer.launch(args=args, headless=True, **options)
