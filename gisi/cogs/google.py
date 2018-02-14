import asyncio
import logging
import random
import urllib.parse
from io import BytesIO

from PIL import Image
from aiohttp import ClientSession
from discord import Embed, File
from discord.ext.commands import group

from gisi import SetDefaults
from gisi.utils import extract_keys, maybe_extract_keys, text_utils

log = logging.getLogger(__name__)

SetDefaults({
    "google_api_key": None,
    "search_engine_id": "002017775112634544492:izg2ejvnmiq"
})


class Google:
    def __init__(self, bot):
        self.bot = bot
        self.aiosession = bot.aiosession
        self.cse = CSE(self.bot.config.google_api_key, search_engine=self.bot.config.search_engine_id,
                       aiosession=self.aiosession)

    @group()
    async def search(self, ctx):
        if ctx.invoked_subcommand:
            return
        query = ctx.clean_content
        content = f"{ctx.invocation_content} `{query}`"

        await ctx.message.edit(content=f"{content} (searching...)")
        result = await self.cse.search(query)
        await ctx.message.edit(content=f"{content} (processing...)")
        line = 5 * "─"
        em = Embed(colour=random.choice([0x3cba54, 0xf4c20d, 0xdb3236, 0x4885ed]))
        em.set_author(name=query, url=f"https://www.google.com/search?q={urllib.parse.quote(query)}",
                      icon_url="http://www.pvhc.net/img207/bydtkmqbpsmeqcgkgidx.png")
        em.set_footer(text="search",
                      icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/Google-favicon-2015.png/150px-Google-favicon-2015.png")
        for item in result[:5]:
            snippet = text_utils.escape(text_utils.fit_sentences(item.snippet, max_length=200))
            em.add_field(name=item.title, value=f"[{item.link}]({item.link})\n{text_utils.italic(snippet)}\n{line}",
                         inline=False)
        await ctx.send(embed=em)
        await ctx.message.edit(content=f"{content} (done!)")

    @search.command()
    async def images(self, ctx, *, query):
        content = f"{ctx.invocation_content} `{query}`"
        await ctx.message.edit(content=f"{content} (searching...)")
        result = await self.cse.search_images(query)
        await ctx.message.edit(content=f"{content} (generating image...)")
        im = await result.create_image(self.aiosession)
        im_data = BytesIO()
        im.save(im_data, "PNG")
        im_data.seek(0)
        file = File(im_data, f"result.png")
        await ctx.message.edit(content=f"{content} (sending...)")
        await ctx.send(file=file)
        await ctx.message.edit(content=f"{content} (done!)")


def setup(bot):
    if not bot.config.google_api_key:
        log.error("No google api key found in config (key: \"google_api_key\"). Can't initialise cog!")
        return
    bot.add_cog(Google(bot))


class CSE:
    SEARCH_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key, search_engine=None, aiosession=None):
        self.api_key = api_key
        self.search_engine = search_engine

        self.aiosession = aiosession or ClientSession()

    def __str__(self):
        return f"<Gisi CSE API [{self.search_engine}]>"

    def build_params(self, query, search_engine=None, **kwargs):
        cx = search_engine or self.search_engine
        if not cx:
            raise KeyError("No search engine id provided!")
        params = {
            "cx": cx,
            "key": self.api_key,
            "q": query
        }

        if "search_type" in kwargs:
            params["searchType"] = kwargs["search_type"]

        return params

    async def search(self, query, cls=None, **kwargs):
        cls = cls or CSEResult
        params = self.build_params(query, **kwargs)
        async with self.aiosession.get(self.SEARCH_ENDPOINT, params=params) as resp:
            data = await resp.json()
        return cls.parse(query, data)

    async def search_images(self, query, **kwargs):
        return await self.search(query, cls=CSEImageResult, search_type="image", **kwargs)


class CSEResult:
    def __init__(self, search_query, context, items):
        self.search_query = search_query
        self.context = context
        self.items = items

    def __str__(self):
        return f"Result for \"{self.search_query}\" with {len(self.items)} results"

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        return self.items[item]

    @classmethod
    def parse(cls, search_query, data):
        kwargs = extract_keys(data, "context", "items")
        kwargs.update({
            "items": [CSEResultItem.parse(res) for res in kwargs["items"]]
        })
        return cls(search_query, **kwargs)


class CSEImageResult(CSEResult):
    async def get_images(self, session):
        tasks = []
        for item in self.items:
            tasks.append(asyncio.ensure_future(item.image.get_image(session)))
        return await asyncio.gather(*tasks)

    async def create_image(self, session):
        vertical_padding = 20
        horizontal_padding = 15
        line_width = 600
        horizontal_spacing = 10
        vertical_spacing = 10
        image_height = 100

        await self.get_images(session)

        lines = []
        current_images_width = 0
        current_width = 0
        current_line = []
        for result in self.items:
            img = result.image._image
            img = img.resize(((image_height * img.width) // img.height, image_height), Image.HAMMING)
            if current_width + horizontal_spacing + img.width > line_width:
                lines.append([current_width, current_images_width, current_line])
                current_line = [img]
                current_width = img.width
                current_images_width = img.width
            else:
                current_line.append(img)
                current_width += horizontal_spacing + img.width
                current_images_width += img.width
        lines.append([current_width, current_images_width, current_line])

        im_height = 2 * vertical_padding + len(lines) * image_height + (len(lines) - 1) * vertical_spacing
        line_width = max(line[0] for line in lines)
        im = Image.new("RGB", (2 * horizontal_padding + line_width, im_height), (35, 39, 42))

        current_y = vertical_padding
        for spaced_width, width, images in lines:
            x = horizontal_padding
            spacing = (line_width - width) // (len(images) - 1) if len(images) > 1 else 0
            for img in images:
                im.paste(img, box=(x, current_y))
                x += img.width + spacing
            current_y += image_height + vertical_spacing

        return im


class CSEResultItem:
    def __init__(self, title, link, display_link, snippet, image):
        self.title = title
        self.link = link
        self.display_link = display_link
        self.snippet = snippet
        self.image = image

    def __str__(self):
        return f"<SearchResult \"{self.title}\" {self.link}"

    @classmethod
    def parse(cls, data):
        kwargs = maybe_extract_keys(data, ["title", "link", "displayLink", "snippet", "image"])
        kwargs.update({
            "display_link": kwargs.pop("displayLink")
        })
        if kwargs["image"]:
            kwargs["image"] = CSEImage.parse(kwargs["image"])
        return cls(**kwargs)


class CSEImage:
    def __init__(self, contextLink, height, width, byteSize, thumbnailLink, thumbnailHeight, thumbnailWidth):
        self.context_Link = contextLink
        self.height = height
        self.width = width
        self.byte_size = byteSize
        self.thumbnail_link = thumbnailLink
        self.thumbnail_height = thumbnailHeight
        self.thumbnail_width = thumbnailWidth

        self._image = None

    def __str__(self):
        return f"<Image>"

    @classmethod
    def parse(cls, data):
        kwargs = data
        return cls(**kwargs)

    async def get_image(self, session):
        if not self._image:
            async with session.get(self.thumbnail_link) as resp:
                data = BytesIO(await resp.read())
                self._image = Image.open(data)
        return self._image
