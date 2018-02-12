import asyncio
import colorsys
import logging
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat
from aiohttp import ClientSession
from discord import File
from discord.ext.commands import command

from gisi import SetDefaults
from gisi.utils import chunks, extract_keys

log = logging.getLogger(__name__)

SetDefaults({
    "wolfram_app_id": "EH8PUT-35T4RK4AVL"
})


class WolframAlpha:
    def __init__(self, bot):
        self.bot = bot
        self.aiosession = bot.aiosession
        self.wolfram_client = Client(self.bot.config.wolfram_app_id, aiosession=self.aiosession)

    @command()
    async def ask(self, ctx, *query):
        query = " ".join(query)
        content = f"{ctx.invocation_content} `{ctx.clean_content}`"
        await ctx.message.edit(content=f"{content} (processing...)")
        doc = await self.wolfram_client.query(query)
        if not doc:
            await ctx.message.edit(content=f"{content} **No Results found!**")
            return

        await ctx.message.edit(content=f"{content} (generating image...)")
        imgs = await doc.create_images(self.aiosession)
        await ctx.message.edit(content=f"{content} (processing image...)")
        files = []
        for n, im in enumerate(imgs):
            im_data = BytesIO()
            im.save(im_data, "PNG")
            im_data.seek(0)
            files.append(File(im_data, f"result_{n}.png"))
        cs = chunks(files, 10)
        uploaded = 0
        for file_chunk in cs:
            await ctx.message.edit(
                content=f"{content} (uploading image(s)... [{len(file_chunk) + uploaded}/{len(files)}])")
            await ctx.send(files=file_chunk)
            uploaded += len(file_chunk)
        await ctx.message.edit(content=f"{content} (done!)")


def setup(bot):
    bot.add_cog(WolframAlpha(bot))


class Client:
    API_ENDPOINT = "http://api.wolframalpha.com/v2"
    QUERY_ENDPOINT = f"{API_ENDPOINT}/query"

    def __init__(self, app_id, *, aiosession=None):
        self.app_id = app_id

        self.aiosession = aiosession or ClientSession()

    def __str__(self):
        return "<WolframAlpha Client>"

    def cleanup(self):
        self.aiosession.close()

    async def query(self, query):
        params = {
            "input": query,
            "mag": str(1.5),
            "appid": self.app_id,
            "output": "json"
        }
        async with self.aiosession.get(self.QUERY_ENDPOINT, params=params) as resp:
            # Wolfram doesn't return the correct content type so please ignore it, kthx
            data = await resp.json(content_type=None)
        return Document.parse(query, data["queryresult"])


class WolframError(Exception):
    pass


class Document:
    def __init__(self, query, pods, assumptions, **kwargs):
        self.query = query
        self.pods = pods
        self.assumptions = assumptions

    def __str__(self):
        return f"<WolframDocument {len(self.pods)} pod(s)>"

    def __getitem__(self, item):
        return self.pods[item]

    def __iter__(self):
        return iter(self.pods)

    @classmethod
    def parse(cls, query, data):
        if data["error"]:
            raise WolframError(data["error"])
        if not data["success"]:
            log.info(f"couldn't find anything for \"{query}\"")
            log.debug(data)
            return None
        pods = []
        for raw_pod in data["pods"]:
            pods.append(Pod.parse(raw_pod))
        kwargs = {
            "pods": pods,
            "assumptions": data.get("assumptions", [])
        }
        return cls(query, **kwargs)

    async def get_images(self, session):
        tasks = []
        for pod in self.pods:
            tasks.append(asyncio.ensure_future(pod.get_images(session)))
        images = await asyncio.gather(*tasks)
        return [im for pod_imgs in images for im in pod_imgs]

    async def create_images(self, session):
        min_saturation_for_colour = .175

        max_height_per_image = 750
        horizontal_padding = 20
        vertical_padding = 40
        after_text_padding = 6
        after_image_padding = 15
        doc_font = ImageFont.truetype("arial.ttf", 17)

        images = await self.get_images(session)
        max_width = max(im.width for im in images)

        width = max_width + horizontal_padding

        doc_im = Image.new("RGB", (width, max_height_per_image), (35, 39, 42))
        doc_draw = ImageDraw.Draw(doc_im)

        x = horizontal_padding // 2
        current_max_width = horizontal_padding
        y = vertical_padding // 2

        final_images = []

        def finalise_image():
            nonlocal doc_im, doc_draw, x, y, final_images, current_max_width
            doc_im = doc_im.crop((0, 0, current_max_width, y - after_image_padding + vertical_padding // 2))
            final_images.append(doc_im)

            doc_im = Image.new("RGB", (width, max_height_per_image), (35, 39, 42))
            doc_draw = ImageDraw.Draw(doc_im)
            x = horizontal_padding // 2
            current_max_width = horizontal_padding
            y = vertical_padding // 2

        for pod in self.pods:
            for subpod in pod.subpods:
                im = subpod.img._image

                text = pod.title
                text_size = doc_draw.textsize(text, doc_font)

                if text_size[0] + horizontal_padding > max_width:
                    lines = []
                    current_line = ""
                    for word in text.split():
                        current_line += f" {word}"
                        text_width = doc_draw.textsize(current_line, doc_font)[0]
                        if text_width + horizontal_padding >= max_width:
                            lines.append(current_line.strip())
                            current_line = word
                    lines.append(current_line.strip())
                    text = "\n".join(lines).strip()
                    text_size = doc_draw.textsize(text, doc_font)

                height = text_size[1] + after_text_padding + im.height + vertical_padding // 2
                if y + height > max_height_per_image:
                    finalise_image()

                m_w = max(text_size[0], im.width) + horizontal_padding
                if m_w > current_max_width:
                    current_max_width = m_w

                doc_draw.text((x, y), text, (114, 137, 218), doc_font)
                y += text_size[1] + after_text_padding

                stat = ImageStat.Stat(im.convert("RGB"))
                hsv = colorsys.rgb_to_hsv(*map(lambda v: v / 255, stat.median))
                if hsv[1] < min_saturation_for_colour:
                    im = ImageOps.colorize(im.convert("L"), (255, 255, 255), (44, 47, 51))
                doc_im.paste(im, box=(x, y))
                y += im.height + after_image_padding

        finalise_image()
        return final_images


class Pod:
    def __init__(self, title, scanner, id, position, error, subpods, states=None):
        self.title = title
        self.scanner = scanner
        self.id = id
        self.position = position
        self.subpods = subpods
        self.states = states

    def __str__(self):
        return f"<Pod {self.title} {self.id}>"

    def __getitem__(self, item):
        return self.subpods[item]

    @property
    def subpod(self):
        return self.subpods[0]

    @classmethod
    def parse(cls, data):
        kwargs = extract_keys(data, "title", "scanner", "id", "position", "error", "subpods")
        subpods = [SubPod.parse(raw_subpod) for raw_subpod in data["subpods"]]
        kwargs.update({
            "subpods": subpods
        })
        return cls(**kwargs)

    async def get_images(self, session):
        tasks = []
        for subpod in self.subpods:
            tasks.append(asyncio.ensure_future(subpod.get_image(session)))
        return await asyncio.gather(*tasks)


class SubPod:
    def __init__(self, title, text, img, imagesource=None, nodata=False, states=None):
        self.title = title
        self.text = text
        self.img = img
        self.imagesource = imagesource
        self.nodata = nodata
        self.states = states

    def __str__(self):
        return f"<SubPod {self.title}>"

    @classmethod
    def parse(cls, data):
        kwargs = data
        kwargs.update({
            "img": Img.parse(kwargs["img"]),
            "text": kwargs.pop("plaintext")
        })
        return cls(**kwargs)

    async def get_image(self, session):
        return await self.img.get_image(session)


class Img:
    def __init__(self, src, alt, title, width, height):
        self.src = src
        self.alt = alt
        self.title = title
        self.width = width
        self.height = height

        self._image = None

    def __str__(self):
        return f"<img {self.title} ({self.src})>"

    @classmethod
    def parse(cls, data):
        return cls(**data)

    async def get_image(self, session):
        if not self._image:
            async with session.get(self.src) as resp:
                data = BytesIO(await resp.read())
                self._image = Image.open(data)
        return self._image
