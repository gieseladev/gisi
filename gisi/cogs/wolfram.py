import xmltodict
from aiohttp import ClientSession
from discord import Embed
from discord.ext.commands import command

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
        for index, pod in enumerate(doc.pods):
            em = Embed(title=pod.title, description=pod.subpod.text, colour=0xFFCAC3)
            em.set_image(url=pod.subpod.img.src)
            em.set_footer(text=f"Pod {index + 1}/{len(doc.pods)}", icon_url="https://software.duke.edu/sites/default/files/logo-wolfram-alpha-150x150.png")
            await ctx.send(embed=em)


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


class Img:
    def __init__(self, src, alt, title, width, height):
        self.src = src
        self.alt = alt
        self.title = title
        self.width = width
        self.height = height

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
