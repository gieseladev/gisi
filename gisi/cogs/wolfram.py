import asyncio
from io import BytesIO

import xmltodict
from PIL import Image, ImageDraw, ImageFont, ImageOps
from aiohttp import ClientSession
from discord import File
from discord.ext.commands import command
from gisi.utils import chunks

from gisi import SetDefaults

SetDefaults({
    "wolfram_app_id": "EH8PUT-35T4RK4AVL"
})


class WolframAlpha:
    def __init__(self, bot):
        self.bot = bot
        self.aiosession = bot.aiosession
        self.wolfram_client = Client(self.bot.config.wolfram_app_id, aiosession=self.aiosession)

    @command()
    async def ask(self, ctx, query):
        doc = await self.wolfram_client.query(query)
        imgs = await doc.create_images(self.aiosession)
        files = []
        for n, im in enumerate(imgs):
            im_data = BytesIO()
            im.save(im_data, "PNG")
            im_data.seek(0)
            files.append(File(im_data, f"result_{n}.png"))
        for file_chunk in chunks(files, 10):
            await ctx.send(files=file_chunk)


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
            "appid": self.app_id
        }
        async with self.aiosession.get(self.QUERY_ENDPOINT, params=params) as resp:
            raw_xml = await resp.text()
        data = xmltodict.parse(raw_xml)["queryresult"]
        return Document.parse(data)


class Document:
    def __init__(self, pods, assumptions, **kwargs):
        self.pods = pods
        self.assumptions = assumptions

    def __str__(self):
        return f"<WolframDocument {len(self.pods)} pod(s)>"

    def __getitem__(self, item):
        return self.pods[item]

    def __iter__(self):
        return iter(self.pods)

    @classmethod
    def parse(cls, data):
        pods = []
        for raw_pod in data["pod"]:
            pods.append(Pod.parse(raw_pod))
        kwargs = {
            "success": bool(["false", "true"].index(data["@success"])),
            "pods": pods,
            "assumptions": data["assumptions"]
        }
        return cls(**kwargs)

    async def get_images(self, session):
        tasks = []
        for pod in self.pods:
            tasks.append(asyncio.ensure_future(pod.get_images(session)))
        images = await asyncio.gather(*tasks)
        return [im for pod_imgs in images for im in pod_imgs]

    async def create_images(self, session):
        max_height_per_image = 750
        horizontal_padding = 20
        vertical_padding = 40
        after_text_padding = 6
        after_image_padding = 15
        doc_font = ImageFont.truetype("arial.ttf", 17)

        images = await self.get_images(session)
        max_width = max(im.width for im in images)

        width = max_width + horizontal_padding

        doc_im = Image.new("RGBA", (width, max_height_per_image), (35, 39, 42))
        doc_draw = ImageDraw.Draw(doc_im)

        x = horizontal_padding // 2
        current_max_width = horizontal_padding
        y = vertical_padding // 2

        final_images = []

        def finalise_image():
            nonlocal doc_im, doc_draw, x, y, final_images, current_max_width
            doc_im = doc_im.crop((0, 0, current_max_width, y - after_image_padding + vertical_padding // 2))
            final_images.append(doc_im)

            doc_im = Image.new("RGBA", (width, max_height_per_image), (35, 39, 42))
            doc_draw = ImageDraw.Draw(doc_im)
            x = horizontal_padding // 2
            current_max_width = horizontal_padding
            y = vertical_padding // 2

        for pod in self.pods:
            for subpod in pod.subpods:
                im = subpod.img._image

                text = pod.title
                text_size = doc_draw.textsize(text, doc_font)

                height = text_size[1] + after_text_padding + im.height + vertical_padding // 2
                if y + height > max_height_per_image:
                    finalise_image()

                m_w = max(text_size[0], im.width) + horizontal_padding
                if m_w > current_max_width:
                    current_max_width = m_w

                doc_draw.text((x, y), text, (114, 137, 218), doc_font)
                y += text_size[1] + after_text_padding

                im = ImageOps.colorize(im.convert("L"), (255, 255, 255), (44, 47, 51))
                doc_im.paste(im, box=(x, y))
                y += im.height + after_image_padding

        finalise_image()
        return final_images


class Pod:
    def __init__(self, title, scanner, _id, position, subpods):
        self.title = title
        self.scanner = scanner
        self.id = _id
        self.position = position
        self.subpods = subpods

    def __str__(self):
        return f"<Pod {self.title} {self.id}>"

    def __getitem__(self, item):
        return self.subpods[item]

    @property
    def subpod(self):
        return self.subpods[0]

    @classmethod
    def parse(cls, data):
        subpods = []
        if isinstance(data["subpod"], list):
            for raw_subpod in data["subpod"]:
                subpods.append(SubPod.parse(raw_subpod))
        else:
            subpods = [SubPod.parse(data["subpod"])]
        kwargs = {
            "title": data["@title"],
            "scanner": data["@scanner"],
            "_id": data["@id"],
            "position": int(data["@position"]),
            "subpods": subpods
        }
        return cls(**kwargs)

    async def get_images(self, session):
        tasks = []
        for subpod in self.subpods:
            tasks.append(asyncio.ensure_future(subpod.get_image(session)))
        return await asyncio.gather(*tasks)


class SubPod:
    def __init__(self, title, text, img):
        self.title = title
        self.text = text
        self.img = img

    def __str__(self):
        return f"<SubPod {self.title}>"

    @classmethod
    def parse(cls, data):
        kwargs = {
            "title": data["@title"],
            "text": data["plaintext"],
            "img": Img.parse(data["img"])
        }
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
        kwargs = {
            "src": data["@src"],
            "alt": data["@alt"],
            "title": data["@title"],
            "width": data["@width"],
            "height": data["@height"],
        }
        return cls(**kwargs)

    async def get_image(self, session):
        if not self._image:
            async with session.get(self.src) as resp:
                data = BytesIO(await resp.read())
                self._image = Image.open(data)
        return self._image
