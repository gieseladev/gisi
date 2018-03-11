import functools
import re
from collections import OrderedDict

import asyncio
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord.ext.commands import Context, command
from typing import Any, Callable, Optional

from gisi import Gisi
from gisi.utils import FlagConverter, JsonObject, add_embed


class Wikipedia:
    """Need I really say more?"""

    def __init__(self, bot: Gisi):
        self.bot = bot
        self.aiosession = bot.aiosession
        self.wiki_api = WikipediaAPI(self.aiosession)

    @command(usage="<query> [flags...]")
    async def wiki(self, ctx: Context, *flags):
        flags = FlagConverter.from_spec(flags)
        query = flags.get(0, None)
        if not query:
            await add_embed(ctx, description="Please provide a search query", colour=False)
            return
        page = await self.wiki_api.get(query)
        print(await page.summary)
        print(await page.images)


def setup(bot: Gisi):
    bot.add_cog(Wikipedia(bot))


class WikipediaAPI:
    API_URL = "https://{lang}.wikipedia.org/w/api.php"

    def __init__(self, aiosession: ClientSession, *, lang: str = None):
        self.lang = lang.lower() if lang else "en"
        self.aiosession = aiosession

    async def get(self, title, **kwargs):
        return await WikipediaPage.load(self, title=title, **kwargs)

    async def request(self, *, action: str = "query", lang: str = None, **kwargs):
        lang = lang.lower() if lang else self.lang
        url = self.API_URL.format(lang=lang)
        params = kwargs
        params.update({
            "action": action,
            "format": "json",
            "formatversion": "2"
        })
        async with self.aiosession.get(url, params=params) as resp:
            return JsonObject(await resp.json())


def cached(func: Callable[["WikipediaPage", Optional[Any]], Any]):
    name = "_" + func.__name__

    @functools.wraps(func)
    async def wrapper(self: "WikipediaPage", *args, **kwargs):
        if not hasattr(self, name):
            value = await func(self, *args, **kwargs)
            setattr(self, name, value)
        return getattr(self, name)

    return wrapper


def async_property(func: Callable):
    @property
    @functools.wraps(func)
    def wrapper(self):
        return func(self)

    return wrapper


def cached_async_property(func: Callable):
    return async_property(cached(func))


class WikipediaPage:
    def __init__(self, api: WikipediaAPI, title: str, pageid: int):
        self.api = api
        self.title = title
        self.pageid = pageid

    def __repr__(self):
        return f"Page {self.pageid}: {self.title}"

    @classmethod
    async def load(cls, api: WikipediaAPI, *, title: str = None, pageid: int = None, redirect: bool = True,
                   preload: bool = False):
        params = {
            "prop": "info|pageprops",
            "inprop": "url",
            "ppprop": "disambiguation",
            "redirects": 1,
        }

        if title:
            params["titles"] = title
        elif pageid:
            params["pageids"] = pageid
        else:
            raise ValueError("please specify title or pageid")

        resp = await api.request(**params)

        query = resp.query
        pages = OrderedDict([(page.pageid, page) for page in query.pages])
        pageid = next(iter(pages.keys()))
        page = pages[pageid]

        # missing is present if the page is missing
        if "missing" in page:
            if title:
                raise ValueError(title)
            else:
                raise ValueError(pageid)

        # same thing for redirect, except it shows up in query instead of page for
        # whatever silly reason
        elif "redirects" in query:
            if redirect:
                redirects = query.redirects[0]
                # change the title and reload the whole object
                return await cls.load(api, title=redirects.to, redirect=redirect, preload=preload)
            else:
                raise ValueError(title or page.title)

        # since we only asked for disambiguation in ppprop,
        # if a pageprop is returned,
        # then the page must be a disambiguation page
        elif "pageprops" in page:
            params = {
                "prop": "revisions",
                "rvprop": "content",
                "rvparse": 1,
                "rvlimit": 1
            }
            if title:
                params["titles"] = title
            else:
                params["pageids"] = pageid
            resp = await api.request(**params)
            pages = OrderedDict([(page.pageid, page) for page in resp.query.pages])
            html = pages[pageid].revisions[0].content

            lis = BeautifulSoup(html, "html.parser").find_all("li")
            filtered_lis = [li for li in lis if "tocsection" not in "".join(li.get("class", []))]
            may_refer_to = [li.a.get_text() for li in filtered_lis if li.a]

            raise ValueError(title or page.title, may_refer_to)
        else:
            title = page.title

        page = cls(api, title, pageid)
        if preload:
            tasks = []
            for prop in ("content", "summary", "images", "references", "links", "sections"):
                tasks.append(asyncio.ensure_future(getattr(page, prop)))
            await asyncio.gather(*tasks)

        return page

    async def request(self, **kwargs):
        if hasattr(self, "title"):
            kwargs["titles"] = self.title
        else:
            kwargs["pageids"] = self.pageid
        return await self.api.request(**kwargs)

    async def continued_request(self, **params):

        last_continue = {}
        prop = params.get("prop", None)

        while True:
            params = params.copy()
            params.update(last_continue)

            resp = await self.request(**params)

            if "query" not in resp:
                break

            if "generator" in params:
                for datum in resp.query.pages:
                    yield datum
            else:
                page = next(page for page in resp.query.pages if page.pageid == self.pageid)
                for datum in page[prop]:
                    yield datum

            if "continue" not in resp:
                break

            last_continue = resp["continue"]

    @cached_async_property
    async def content(self):
        resp = await self.request(prop="extracts", explaintext=1)
        return next(page for page in resp.query.pages if page.pageid == self.pageid).extract

    @cached_async_property
    async def summary(self):
        params = {
            "prop": "extracts",
            "explaintext": 1,
            "exintro": 1,
        }

        resp = await self.request(**params)
        return next(page for page in resp.query.pages if page.pageid == self.pageid).extract

    @cached_async_property
    async def images(self):
        params = {
            "generator": "images",
            "gimlimit": "max",
            "prop": "imageinfo",
            "iiprop": "url",
        }
        pages = self.continued_request(**params)
        return [page.imageinfo[0].url async for page in pages if "imageinfo" in page]

    @cached_async_property
    async def coordinates(self):
        params = {
            "prop": "coordinates",
            "colimit": "max"
        }
        resp = await self.request(**params)

        if "query" in resp:
            coordinates = next(page for page in resp.query.pages if page.pageid == self.pageid).coordinates[0]
            return coordinates["lon"], coordinates["lat"]
        else:
            return None

    @cached_async_property
    async def references(self):
        def add_protocol(url):
            return url if url.startswith("http") else "http:" + url

        params = {
            "prop": "extlinks",
            "ellimit": "max"
        }
        links = self.continued_request(**params)
        return [add_protocol(link.url) async for link in links]

    @cached_async_property
    async def links(self):
        params = {
            "prop": "links",
            "plnamespace": 0,
            "pllimit": "max"
        }
        links = self.continued_request(**params)
        return [link.title async for link in links]

    @cached_async_property
    async def categories(self):
        params = {
            "prop": "categories",
            "cllimit": "max"
        }
        resp = self.continued_request(**params)
        raw_titles = [link.title async for link in resp]
        return [re.sub(r"^Category:", "", raw_title) for raw_title in raw_titles]

    @cached_async_property
    async def sections(self):
        params = {
            "action": "parse",
            "prop": "sections",
        }

        resp = await self.request(**params)
        return [section.line for section in resp.parse.sections]

    async def section(self, section_title):
        section = f"== {section_title} =="
        try:
            index = self.content.index(section) + len(section)
        except ValueError:
            return None

        try:
            next_index = self.content.index("==", index)
        except ValueError:
            next_index = len(self.content)

        return (await self.content)[index:next_index].lstrip("=").strip()
