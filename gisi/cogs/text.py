import logging
import re

from discord.ext.commands import group

from gisi import SetDefaults
from gisi.utils import text_utils

log = logging.getLogger(__name__)


class Text:
    """Convert -name- into asciimojis!

    Because you can never have enough emojis in your life! ヽ༼ຈل͜ຈ༽ﾉ
    """

    def __init__(self, bot):
        self.bot = bot
        self.replacers = bot.mongo_db.replacers
        self.cached_replacers = {}

    async def on_ready(self):
        collections = await self.bot.mongo_db.collection_names()
        if "replacers" not in collections:
            log.debug("replacer collection not found, uploading default")
            await self.replacers.insert_many(default_replacers, ordered=False)
            log.info("uploaded default replacers")

    async def get_replacement(self, key, args):
        if key in self.cached_replacers:
            repl = self.cached_replacers[key]
        else:
            repl = await self.replacers.find_one({"triggers": key})
            self.cached_replacers[key] = repl
        if not repl:
            return None
        return repl["replacement"]

    async def replace_text(self, text, require_wrapping=True):
        prog = re.compile(r"(?<!\\)-(.+)-" if require_wrapping else r"(\w+)")

        start = 0
        while True:
            match = prog.search(text, start)
            if not match:
                break
            start += match.end()
            key, *args = match.group().split()
            key = key.lower()
            new = await self.get_replacement(key, args)
            if not new:
                continue
            pre = text[:match.start()]
            after = text[match.end():]
            new = text_utils.escape(new)
            text = f"{pre}{new}{after}"

        return text

    @group()
    async def replace(self, ctx):
        """Find and convert asciimojis.

        For each word try to find a asciimoji and use it.
        """
        if ctx.invoked_subcommand:
            return

        new_content = await self.replace_text(ctx.clean_content, require_wrapping=False)
        await ctx.message.edit(content=new_content)

    @replace.group()
    async def add(self, ctx, trigger, replacement):
        """Add a replacer"""
        triggers = [trig.strip() for trig in trigger.split(",")]
        await self.replacers.insert_one({"triggers": triggers, "replacement": replacement})

    @replace.command()
    async def show(self, ctx, page: int = 1):
        """Show all the beautiful emojis
        per_page = 25
        n_pages = ceil(len(self.table) / per_page)
        if not 0 < page <= n_pages:
            await ctx.message.edit(content=f"{ctx.invocation_content} (**there are only {n_pages} pages**)")
            return
        targets = self.table[(page - 1) * 25:page * 25]
        em = Embed(colour=Colours.INFO)
        for target in targets:
            em.add_field(name=", ".join(target["words"]), value=target["ascii"])
        em.set_footer(text=f"Page {page}/{n_pages}")
        await ctx.message.edit(embed=em)"""
        pass

    @replace.command()
    async def enable(self, ctx):
        """Enable the beautiful conversion"""
        self.bot.config.ascii_enabled = True
        await ctx.message.edit(content=f"{ctx.message.content} (enabled)")

    @replace.command()
    async def disable(self, ctx):
        """Disable the beautiful conversion"""
        self.bot.config.ascii_enabled = False
        await ctx.message.edit(content=f"{ctx.message.content} (disabled)")

    async def handle_message(self, message):
        if message.author != self.bot.user:
            return
        if self.bot.config.replacer_enabled:
            new_content = await self.replace_text(message.content)
            if new_content != message.content:
                await message.edit(content=new_content)

    async def on_message(self, message):
        await self.handle_message(message)

    async def on_message_edit(self, before, after):
        await self.handle_message(after)


def setup(bot):
    SetDefaults({
        "replacer_enabled": True
    })
    bot.add_cog(Text(bot))


# SOURCE: https://github.com/hpcodecraft/ASCIImoji/blob/master/src/asciimoji.js
default_replacers = [
    {
        "triggers": [
            "acid"
        ],
        "replacement": "⊂(◉‿◉)つ"
    },
    {
        "triggers": [
            "afraid"
        ],
        "replacement": "(ㆆ _ ㆆ)"
    },
    {
        "triggers": [
            "angel"
        ],
        "replacement": "☜(⌒▽⌒)☞"
    },
    {
        "triggers": [
            "angry"
        ],
        "replacement": "•`_´•"
    },
    {
        "triggers": [
            "arrowhead"
        ],
        "replacement": "⤜(ⱺ ʖ̯ⱺ)⤏"
    },
    {
        "triggers": [
            "apple"
        ],
        "replacement": ""
    },
    {
        "triggers": [
            "ass",
            "butt"
        ],
        "replacement": "(‿|‿)"
    },
    {
        "triggers": [
            "awkward"
        ],
        "replacement": "•͡˘㇁•͡˘"
    },
    {
        "triggers": [
            "bat"
        ],
        "replacement": "/|\\ ^._.^ /|\\"
    },
    {
        "triggers": [
            "bear",
            "koala"
        ],
        "replacement": "ʕ·͡ᴥ·ʔ﻿"
    },
    {
        "triggers": [
            "bearflip"
        ],
        "replacement": "ʕノ•ᴥ•ʔノ ︵ ┻━┻"
    },
    {
        "triggers": [
            "bearhug"
        ],
        "replacement": "ʕっ•ᴥ•ʔっ"
    },
    {
        "triggers": [
            "because",
            "since"
        ],
        "replacement": "∵"
    },
    {
        "triggers": [
            "bigheart"
        ],
        "replacement": "❤"
    },
    {
        "triggers": [
            "blackeye"
        ],
        "replacement": "0__#"
    },
    {
        "triggers": [
            "blubby"
        ],
        "replacement": "(      0    _   0    )"
    },
    {
        "triggers": [
            "blush"
        ],
        "replacement": "(˵ ͡° ͜ʖ ͡°˵)"
    },
    {
        "triggers": [
            "bond",
            "007"
        ],
        "replacement": "┌( ͝° ͜ʖ͡°)=ε/̵͇̿̿/’̿’̿ ̿"
    },
    {
        "triggers": [
            "boobs"
        ],
        "replacement": "( . Y . )"
    },
    {
        "triggers": [
            "bored"
        ],
        "replacement": "(-_-)"
    },
    {
        "triggers": [
            "bribe"
        ],
        "replacement": "( •͡˘ _•͡˘)ノð"
    },
    {
        "triggers": [
            "bubbles"
        ],
        "replacement": "( ˘ ³˘)ノ°ﾟº❍｡"
    },
    {
        "triggers": [
            "butterfly"
        ],
        "replacement": "ƸӜƷ"
    },
    {
        "triggers": [
            "cat"
        ],
        "replacement": "(= ФェФ=)"
    },
    {
        "triggers": [
            "catlenny"
        ],
        "replacement": "( ͡° ᴥ ͡°)﻿"
    },
    {
        "triggers": [
            "check"
        ],
        "replacement": "✓"
    },
    {
        "triggers": [
            "chubby"
        ],
        "replacement": "╭(ʘ̆~◞౪◟~ʘ̆)╮"
    },
    {
        "triggers": [
            "claro"
        ],
        "replacement": "(͡ ° ͜ʖ ͡ °)"
    },
    {
        "triggers": [
            "clique",
            "gang",
            "squad"
        ],
        "replacement": "ヽ༼ ຈل͜ຈ༼ ▀̿̿Ĺ̯̿̿▀̿ ̿༽Ɵ͆ل͜Ɵ͆ ༽ﾉ"
    },
    {
        "triggers": [
            "cloud"
        ],
        "replacement": "☁"
    },
    {
        "triggers": [
            "club"
        ],
        "replacement": "♣"
    },
    {
        "triggers": [
            "coffee",
            "cuppa"
        ],
        "replacement": "c[_]"
    },
    {
        "triggers": [
            "cmd",
            "command"
        ],
        "replacement": "⌘"
    },
    {
        "triggers": [
            "cool",
            "csi"
        ],
        "replacement": "(•_•) ( •_•)>⌐■-■ (⌐■_■)"
    },
    {
        "triggers": [
            "copy",
            "c"
        ],
        "replacement": "©"
    },
    {
        "triggers": [
            "creep"
        ],
        "replacement": "ԅ(≖‿≖ԅ)"
    },
    {
        "triggers": [
            "creepcute"
        ],
        "replacement": "ƪ(ړײ)‎ƪ​​"
    },
    {
        "triggers": [
            "crim3s"
        ],
        "replacement": "( ✜︵✜ )"
    },
    {
        "triggers": [
            "cross"
        ],
        "replacement": "†"
    },
    {
        "triggers": [
            "cry"
        ],
        "replacement": "(╥﹏╥)"
    },
    {
        "triggers": [
            "crywave"
        ],
        "replacement": "( ╥﹏╥) ノシ"
    },
    {
        "triggers": [
            "cute"
        ],
        "replacement": "(｡◕‿‿◕｡)"
    },
    {
        "triggers": [
            "d1"
        ],
        "replacement": "⚀"
    },
    {
        "triggers": [
            "d2"
        ],
        "replacement": "⚁"
    },
    {
        "triggers": [
            "d3"
        ],
        "replacement": "⚂"
    },
    {
        "triggers": [
            "d4"
        ],
        "replacement": "⚃"
    },
    {
        "triggers": [
            "d5"
        ],
        "replacement": "⚄"
    },
    {
        "triggers": [
            "d6"
        ],
        "replacement": "⚅"
    },
    {
        "triggers": [
            "damnyou"
        ],
        "replacement": "(ᕗ ͠° ਊ ͠° )ᕗ"
    },
    {
        "triggers": [
            "dance"
        ],
        "replacement": "ᕕ(⌐■_■)ᕗ ♪♬"
    },
    {
        "triggers": [
            "dead"
        ],
        "replacement": "x⸑x"
    },
    {
        "triggers": [
            "dealwithit",
            "dwi"
        ],
        "replacement": "(⌐■_■)"
    },
    {
        "triggers": [
            "delta"
        ],
        "replacement": "Δ"
    },
    {
        "triggers": [
            "depressed"
        ],
        "replacement": "(︶︹︶)"
    },
    {
        "triggers": [
            "derp"
        ],
        "replacement": "☉ ‿ ⚆"
    },
    {
        "triggers": [
            "diamond"
        ],
        "replacement": "♦"
    },
    {
        "triggers": [
            "dog"
        ],
        "replacement": "(◕ᴥ◕ʋ)"
    },
    {
        "triggers": [
            "dollar"
        ],
        "replacement": "$"
    },
    {
        "triggers": [
            "dong"
        ],
        "replacement": "(̿▀̿ ̿Ĺ̯̿̿▀̿ ̿)̄"
    },
    {
        "triggers": [
            "donger"
        ],
        "replacement": "ヽ༼ຈل͜ຈ༽ﾉ"
    },
    {
        "triggers": [
            "dontcare"
        ],
        "replacement": "╭∩╮（︶︿︶）╭∩╮"
    },
    {
        "triggers": [
            "do not want",
            "dontwant"
        ],
        "replacement": "ヽ(｀Д´)ﾉ"
    },
    {
        "triggers": [
            "dope"
        ],
        "replacement": "<(^_^)>"
    },
    {
        "triggers": [
            "<<"
        ],
        "replacement": "«"
    },
    {
        "triggers": [
            ">>"
        ],
        "replacement": "»"
    },
    {
        "triggers": [
            "doubleflat"
        ],
        "replacement": "𝄫"
    },
    {
        "triggers": [
            "doublesharp"
        ],
        "replacement": "𝄪"
    },
    {
        "triggers": [
            "doubletableflip"
        ],
        "replacement": "┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻"
    },
    {
        "triggers": [
            "down"
        ],
        "replacement": "↓"
    },
    {
        "triggers": [
            "duckface"
        ],
        "replacement": "(・3・)"
    },
    {
        "triggers": [
            "duel"
        ],
        "replacement": "ᕕ(╭ರ╭ ͟ʖ╮•́)⊃¤=(-----"
    },
    {
        "triggers": [
            "duh"
        ],
        "replacement": "(≧︿≦)"
    },
    {
        "triggers": [
            "dunno"
        ],
        "replacement": "¯\\(°_o)/¯"
    },
    {
        "triggers": [
            "ebola"
        ],
        "replacement": "ᴇʙᴏʟᴀ"
    },
    {
        "triggers": [
            "ellipsis",
            "..."
        ],
        "replacement": "…"
    },
    {
        "triggers": [
            "emdash",
            "--"
        ],
        "replacement": "-"
    },
    {
        "triggers": [
            "emptystar"
        ],
        "replacement": "☆"
    },
    {
        "triggers": [
            "emptytriangle",
            "t2"
        ],
        "replacement": "△"
    },
    {
        "triggers": [
            "endure"
        ],
        "replacement": "(҂◡_◡) ᕤ"
    },
    {
        "triggers": [
            "envelope",
            "letter"
        ],
        "replacement": "✉︎"
    },
    {
        "triggers": [
            "epsilon"
        ],
        "replacement": "ɛ"
    },
    {
        "triggers": [
            "euro"
        ],
        "replacement": "€"
    },
    {
        "triggers": [
            "evil"
        ],
        "replacement": "ψ(｀∇´)ψ"
    },
    {
        "triggers": [
            "evillenny"
        ],
        "replacement": "(͠≖ ͜ʖ͠≖)"
    },
    {
        "triggers": [
            "execution"
        ],
        "replacement": "(⌐■_■)︻╦╤─   (╥﹏╥)"
    },
    {
        "triggers": [
            "facebook"
        ],
        "replacement": "(╯°□°)╯︵ ʞooqǝɔɐɟ"
    },
    {
        "triggers": [
            "facepalm"
        ],
        "replacement": "(－‸ლ)"
    },
    {
        "triggers": [
            "fart"
        ],
        "replacement": "(ˆ⺫ˆ๑)<3"
    },
    {
        "triggers": [
            "fight"
        ],
        "replacement": "(ง •̀_•́)ง"
    },
    {
        "triggers": [
            "finn"
        ],
        "replacement": "| (• ◡•)|"
    },
    {
        "triggers": [
            "fish"
        ],
        "replacement": "<\"(((<3"
    },
    {
        "triggers": [
            "5",
            "five"
        ],
        "replacement": "卌"
    },
    {
        "triggers": [
            "5/8"
        ],
        "replacement": "⅝"
    },
    {
        "triggers": [
            "flat",
            "bemolle"
        ],
        "replacement": "♭"
    },
    {
        "triggers": [
            "flexing"
        ],
        "replacement": "ᕙ(`▽´)ᕗ"
    },
    {
        "triggers": [
            "flipped",
            "heavytable"
        ],
        "replacement": "┬─┬﻿ ︵ /(.□. \\）"
    },
    {
        "triggers": [
            "flower",
            "flor"
        ],
        "replacement": "(✿◠‿◠)"
    },
    {
        "triggers": [
            "f"
        ],
        "replacement": "✿"
    },
    {
        "triggers": [
            "fly"
        ],
        "replacement": "─=≡Σ((( つ◕ل͜◕)つ"
    },
    {
        "triggers": [
            "friendflip"
        ],
        "replacement": "(╯°□°)╯︵ ┻━┻ ︵ ╯(°□° ╯)"
    },
    {
        "triggers": [
            "frown"
        ],
        "replacement": "(ღ˘⌣˘ღ)"
    },
    {
        "triggers": [
            "fuckoff",
            "gtfo"
        ],
        "replacement": "୧༼ಠ益ಠ╭∩╮༽"
    },
    {
        "triggers": [
            "fuckyou",
            "fu"
        ],
        "replacement": "┌П┐(ಠ_ಠ)"
    },
    {
        "triggers": [
            "gentleman",
            "sir",
            "monocle"
        ],
        "replacement": "ಠ_ರೃ"
    },
    {
        "triggers": [
            "ghast"
        ],
        "replacement": "= _ ="
    },
    {
        "triggers": [
            "ghost"
        ],
        "replacement": "༼ つ ❍_❍ ༽つ"
    },
    {
        "triggers": [
            "gift",
            "present"
        ],
        "replacement": "(´・ω・)っ由"
    },
    {
        "triggers": [
            "gimme"
        ],
        "replacement": "༼ つ ◕_◕ ༽つ"
    },
    {
        "triggers": [
            "glitter"
        ],
        "replacement": "(*・‿・)ノ⌒*:･ﾟ✧"
    },
    {
        "triggers": [
            "glasses"
        ],
        "replacement": "(⌐ ͡■ ͜ʖ ͡■)"
    },
    {
        "triggers": [
            "glassesoff"
        ],
        "replacement": "( ͡° ͜ʖ ͡°)ﾉ⌐■-■"
    },
    {
        "triggers": [
            "glitterderp"
        ],
        "replacement": "(ﾉ☉ヮ⚆)ﾉ ⌒*:･ﾟ✧"
    },
    {
        "triggers": [
            "gloomy"
        ],
        "replacement": "(_゜_゜_)"
    },
    {
        "triggers": [
            "goatse"
        ],
        "replacement": "(з๏ε)"
    },
    {
        "triggers": [
            "gotit"
        ],
        "replacement": "(☞ﾟ∀ﾟ)☞"
    },
    {
        "triggers": [
            "greet",
            "greetings"
        ],
        "replacement": "( ´◔ ω◔`) ノシ"
    },
    {
        "triggers": [
            "gun",
            "mg"
        ],
        "replacement": "︻╦╤─"
    },
    {
        "triggers": [
            "hadouken"
        ],
        "replacement": "༼つಠ益ಠ༽つ ─=≡ΣO))"
    },
    {
        "triggers": [
            "hammerandsickle",
            "hs"
        ],
        "replacement": "☭"
    },
    {
        "triggers": [
            "handleft",
            "hl"
        ],
        "replacement": "☜"
    },
    {
        "triggers": [
            "handright",
            "hr"
        ],
        "replacement": "☞"
    },
    {
        "triggers": [
            "haha"
        ],
        "replacement": "٩(^‿^)۶"
    },
    {
        "triggers": [
            "happy"
        ],
        "replacement": "٩( ๑╹ ꇴ╹)۶"
    },
    {
        "triggers": [
            "happygarry"
        ],
        "replacement": "ᕕ( ᐛ )ᕗ"
    },
    {
        "triggers": [
            "h",
            "heart"
        ],
        "replacement": "♥"
    },
    {
        "triggers": [
            "hello",
            "ohai",
            "bye"
        ],
        "replacement": "(ʘ‿ʘ)╯"
    },
    {
        "triggers": [
            "highfive"
        ],
        "replacement": "._.)/\\(._."
    },
    {
        "triggers": [
            "hitting"
        ],
        "replacement": "( ｀皿´)｡ﾐ/"
    },
    {
        "triggers": [
            "hug",
            "hugs"
        ],
        "replacement": "(づ｡◕‿‿◕｡)づ"
    },
    {
        "triggers": [
            "iknowright",
            "ikr"
        ],
        "replacement": "┐｜･ิω･ิ#｜┌"
    },
    {
        "triggers": [
            "illuminati"
        ],
        "replacement": "୧(▲ᴗ▲)ノ"
    },
    {
        "triggers": [
            "infinity",
            "inf"
        ],
        "replacement": "∞"
    },
    {
        "triggers": [
            "inlove"
        ],
        "replacement": "(っ´ω`c)♡"
    },
    {
        "triggers": [
            "int"
        ],
        "replacement": "∫"
    },
    {
        "triggers": [
            "internet"
        ],
        "replacement": "ଘ(੭*ˊᵕˋ)੭* ̀ˋ ɪɴᴛᴇʀɴᴇᴛ"
    },
    {
        "triggers": [
            "interrobang"
        ],
        "replacement": "‽"
    },
    {
        "triggers": [
            "jake"
        ],
        "replacement": "(❍ᴥ❍ʋ)"
    },
    {
        "triggers": [
            "kawaii"
        ],
        "replacement": "≧◡≦"
    },
    {
        "triggers": [
            "keen"
        ],
        "replacement": "┬┴┬┴┤Ɵ͆ل͜Ɵ͆ ༽ﾉ"
    },
    {
        "triggers": [
            "kiahh"
        ],
        "replacement": "~\\(≧▽≦)/~"
    },
    {
        "triggers": [
            "kiss"
        ],
        "replacement": "(づ ￣ ³￣)づ"
    },
    {
        "triggers": [
            "kyubey"
        ],
        "replacement": "／人◕ ‿‿ ◕人＼"
    },
    {
        "triggers": [
            "lambda"
        ],
        "replacement": "λ"
    },
    {
        "triggers": [
            "lazy"
        ],
        "replacement": "_(:3」∠)_"
    },
    {
        "triggers": [
            "left",
            "<-"
        ],
        "replacement": "←"
    },
    {
        "triggers": [
            "lenny"
        ],
        "replacement": "( ͡° ͜ʖ ͡°)"
    },
    {
        "triggers": [
            "lennybill"
        ],
        "replacement": "[̲̅$̲̅(̲̅ ͡° ͜ʖ ͡°̲̅)̲̅$̲̅]"
    },
    {
        "triggers": [
            "lennyfight"
        ],
        "replacement": "(ง ͠° ͟ʖ ͡°)ง"
    },
    {
        "triggers": [
            "lennyflip"
        ],
        "replacement": "(ノ ͡° ͜ʖ ͡°ノ)   ︵ ( ͜。 ͡ʖ ͜。)"
    },
    {
        "triggers": [
            "lennygang"
        ],
        "replacement": "( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)"
    },
    {
        "triggers": [
            "lennyshrug"
        ],
        "replacement": "¯\\_( ͡° ͜ʖ ͡°)_/¯"
    },
    {
        "triggers": [
            "lennysir"
        ],
        "replacement": "( ಠ ͜ʖ ರೃ)"
    },
    {
        "triggers": [
            "lennystalker"
        ],
        "replacement": "┬┴┬┴┤( ͡° ͜ʖ├┬┴┬┴"
    },
    {
        "triggers": [
            "lennystrong"
        ],
        "replacement": "ᕦ( ͡° ͜ʖ ͡°)ᕤ"
    },
    {
        "triggers": [
            "lennywizard"
        ],
        "replacement": "╰( ͡° ͜ʖ ͡° )つ──☆*:・ﾟ"
    },
    {
        "triggers": [
            "lol"
        ],
        "replacement": "L(° O °L)"
    },
    {
        "triggers": [
            "look"
        ],
        "replacement": "(ಡ_ಡ)☞"
    },
    {
        "triggers": [
            "love"
        ],
        "replacement": "♥‿♥"
    },
    {
        "triggers": [
            "lovebear"
        ],
        "replacement": "ʕ♥ᴥ♥ʔ"
    },
    {
        "triggers": [
            "lumpy"
        ],
        "replacement": "꒰ ꒡⌓꒡꒱"
    },
    {
        "triggers": [
            "luv"
        ],
        "replacement": "-`ღ´-"
    },
    {
        "triggers": [
            "magic"
        ],
        "replacement": "ヽ(｀Д´)⊃━☆ﾟ. * ･ ｡ﾟ,"
    },
    {
        "triggers": [
            "magicflip"
        ],
        "replacement": "(/¯◡ ‿ ◡)/¯ ~ ┻━┻"
    },
    {
        "triggers": [
            "meep"
        ],
        "replacement": "\\(°^°)/"
    },
    {
        "triggers": [
            "meh"
        ],
        "replacement": "ಠ_ಠ"
    },
    {
        "triggers": [
            "mistyeyes"
        ],
        "replacement": "ಡ_ಡ"
    },
    {
        "triggers": [
            "monster"
        ],
        "replacement": "༼ ༎ຶ ෴ ༎ຶ༽"
    },
    {
        "triggers": [
            "natural"
        ],
        "replacement": "♮"
    },
    {
        "triggers": [
            "needle",
            "inject"
        ],
        "replacement": "┌(◉ ͜ʖ◉)つ┣▇▇▇═──"
    },
    {
        "triggers": [
            "nice"
        ],
        "replacement": "( ͡° ͜ °)"
    },
    {
        "triggers": [
            "no"
        ],
        "replacement": "→_←"
    },
    {
        "triggers": [
            "noclue"
        ],
        "replacement": "／人◕ __ ◕人＼"
    },
    {
        "triggers": [
            "nom",
            "yummy",
            "delicious"
        ],
        "replacement": "(っˆڡˆς)"
    },
    {
        "triggers": [
            "note",
            "sing"
        ],
        "replacement": "♫"
    },
    {
        "triggers": [
            "nuclear",
            "radioactive",
            "nukular"
        ],
        "replacement": "☢"
    },
    {
        "triggers": [
            "nyan"
        ],
        "replacement": "~=[,,_,,]:3"
    },
    {
        "triggers": [
            "nyeh"
        ],
        "replacement": "@^@"
    },
    {
        "triggers": [
            "ohshit"
        ],
        "replacement": "( º﹃º )"
    },
    {
        "triggers": [
            "omg"
        ],
        "replacement": "◕_◕"
    },
    {
        "triggers": [
            "1/8"
        ],
        "replacement": "⅛"
    },
    {
        "triggers": [
            "1/4"
        ],
        "replacement": "¼"
    },
    {
        "triggers": [
            "1/2"
        ],
        "replacement": "½"
    },
    {
        "triggers": [
            "1/3"
        ],
        "replacement": "⅓"
    },
    {
        "triggers": [
            "opt",
            "option"
        ],
        "replacement": "⌥"
    },
    {
        "triggers": [
            "orly"
        ],
        "replacement": "(눈_눈)"
    },
    {
        "triggers": [
            "ohyou",
            "ou"
        ],
        "replacement": "(◞థ౪థ)ᴖ"
    },
    {
        "triggers": [
            "peace",
            "victory"
        ],
        "replacement": "✌(-‿-)✌"
    },
    {
        "triggers": [
            "pear"
        ],
        "replacement": "(__>-"
    },
    {
        "triggers": [
            "pi"
        ],
        "replacement": "π"
    },
    {
        "triggers": [
            "pingpong"
        ],
        "replacement": "( •_•)O*¯`·.¸.·´¯`°Q(•_• )"
    },
    {
        "triggers": [
            "plain"
        ],
        "replacement": "._."
    },
    {
        "triggers": [
            "pleased"
        ],
        "replacement": "(˶‾᷄ ⁻̫ ‾᷅˵)"
    },
    {
        "triggers": [
            "point"
        ],
        "replacement": "(☞ﾟヮﾟ)☞"
    },
    {
        "triggers": [
            "pooh"
        ],
        "replacement": "ʕ •́؈•̀)"
    },
    {
        "triggers": [
            "porcupine"
        ],
        "replacement": "(•ᴥ• )́`́\"́`́\"́⻍"
    },
    {
        "triggers": [
            "pound"
        ],
        "replacement": "£"
    },
    {
        "triggers": [
            "praise"
        ],
        "replacement": "(☝ ՞ਊ ՞)☝"
    },
    {
        "triggers": [
            "punch"
        ],
        "replacement": "O=(\"-\"Q)"
    },
    {
        "triggers": [
            "rage",
            "mad"
        ],
        "replacement": "t(ಠ益ಠt)"
    },
    {
        "triggers": [
            "rageflip"
        ],
        "replacement": "(ノಠ益ಠ)ノ彡┻━┻"
    },
    {
        "triggers": [
            "rainbowcat"
        ],
        "replacement": "(=^･ｪ･^=))ﾉ彡☆"
    },
    {
        "triggers": [
            "really"
        ],
        "replacement": "ò_ô"
    },
    {
        "triggers": [
            "r"
        ],
        "replacement": "®"
    },
    {
        "triggers": [
            "right",
            "->"
        ],
        "replacement": "→"
    },
    {
        "triggers": [
            "riot"
        ],
        "replacement": "୧༼ಠ益ಠ༽୨"
    },
    {
        "triggers": [
            "rolleyes"
        ],
        "replacement": "(◔_◔)"
    },
    {
        "triggers": [
            "rose"
        ],
        "replacement": "✿ڿڰۣ-"
    },
    {
        "triggers": [
            "run"
        ],
        "replacement": "(╯°□°)╯"
    },
    {
        "triggers": [
            "sad"
        ],
        "replacement": "ε(´סּ︵סּ`)з"
    },
    {
        "triggers": [
            "saddonger"
        ],
        "replacement": "ヽ༼ຈʖ̯ຈ༽ﾉ"
    },
    {
        "triggers": [
            "sadlenny"
        ],
        "replacement": "( ͡° ʖ̯ ͡°)"
    },
    {
        "triggers": [
            "7/8"
        ],
        "replacement": "⅞"
    },
    {
        "triggers": [
            "sharp",
            "diesis"
        ],
        "replacement": "♯"
    },
    {
        "triggers": [
            "shout"
        ],
        "replacement": "╚(•⌂•)╝"
    },
    {
        "triggers": [
            "shrug"
        ],
        "replacement": "¯\\_(ツ)_/¯"
    },
    {
        "triggers": [
            "shy"
        ],
        "replacement": "=^_^="
    },
    {
        "triggers": [
            "sigma",
            "sum"
        ],
        "replacement": "Σ"
    },
    {
        "triggers": [
            "skull"
        ],
        "replacement": "☠"
    },
    {
        "triggers": [
            "smile"
        ],
        "replacement": "ツ"
    },
    {
        "triggers": [
            "smiley"
        ],
        "replacement": "☺︎"
    },
    {
        "triggers": [
            "smirk"
        ],
        "replacement": "¬‿¬"
    },
    {
        "triggers": [
            "snowman"
        ],
        "replacement": "☃"
    },
    {
        "triggers": [
            "sob"
        ],
        "replacement": "(;´༎ຶД༎ຶ`)"
    },
    {
        "triggers": [
            "spade"
        ],
        "replacement": "♠"
    },
    {
        "triggers": [
            "sqrt"
        ],
        "replacement": "√"
    },
    {
        "triggers": [
            "squid"
        ],
        "replacement": "<コ:彡"
    },
    {
        "triggers": [
            "star"
        ],
        "replacement": "★"
    },
    {
        "triggers": [
            "strong"
        ],
        "replacement": "ᕙ(⇀‸↼‶)ᕗ"
    },
    {
        "triggers": [
            "suicide"
        ],
        "replacement": "ε/̵͇̿̿/’̿’̿ ̿(◡︵◡)"
    },
    {
        "triggers": [
            "sum"
        ],
        "replacement": "∑"
    },
    {
        "triggers": [
            "sun"
        ],
        "replacement": "☀"
    },
    {
        "triggers": [
            "surprised"
        ],
        "replacement": "(๑•́ ヮ •̀๑)"
    },
    {
        "triggers": [
            "surrender"
        ],
        "replacement": "\\_(-_-)_/"
    },
    {
        "triggers": [
            "stalker"
        ],
        "replacement": "┬┴┬┴┤(･_├┬┴┬┴"
    },
    {
        "triggers": [
            "swag"
        ],
        "replacement": "(̿▀̿‿ ̿▀̿ ̿)"
    },
    {
        "triggers": [
            "sword"
        ],
        "replacement": "o()xxxx[{::::::::::::::::::>"
    },
    {
        "triggers": [
            "tabledown"
        ],
        "replacement": "┬─┬﻿ ノ( ゜-゜ノ)"
    },
    {
        "triggers": [
            "tableflip"
        ],
        "replacement": "(ノ ゜Д゜)ノ ︵ ┻━┻"
    },
    {
        "triggers": [
            "tau"
        ],
        "replacement": "τ"
    },
    {
        "triggers": [
            "tears"
        ],
        "replacement": "(ಥ﹏ಥ)"
    },
    {
        "triggers": [
            "terrorist"
        ],
        "replacement": "୧༼ಠ益ಠ༽︻╦╤─"
    },
    {
        "triggers": [
            "thanks",
            "thankyou",
            "ty"
        ],
        "replacement": "\\(^-^)/"
    },
    {
        "triggers": [
            "therefore",
            "so"
        ],
        "replacement": "⸫"
    },
    {
        "triggers": [
            "3/8"
        ],
        "replacement": "⅜"
    },
    {
        "triggers": [
            "tiefighter"
        ],
        "replacement": "|=-(¤)-=|"
    },
    {
        "triggers": [
            "tired"
        ],
        "replacement": "(=____=)"
    },
    {
        "triggers": [
            "toldyouso",
            "toldyou"
        ],
        "replacement": "☜(꒡⌓꒡)"
    },
    {
        "triggers": [
            "toogood"
        ],
        "replacement": "ᕦ(òᴥó)ᕥ"
    },
    {
        "triggers": [
            "tm"
        ],
        "replacement": "™"
    },
    {
        "triggers": [
            "triangle",
            "t"
        ],
        "replacement": "▲"
    },
    {
        "triggers": [
            "2/3"
        ],
        "replacement": "⅔"
    },
    {
        "triggers": [
            "unflip"
        ],
        "replacement": "┬──┬ ノ(ò_óノ)"
    },
    {
        "triggers": [
            "up"
        ],
        "replacement": "↑"
    },
    {
        "triggers": [
            "victory"
        ],
        "replacement": "(๑•̀ㅂ•́)ง✧"
    },
    {
        "triggers": [
            "wat"
        ],
        "replacement": "(ÒДÓױ)"
    },
    {
        "triggers": [
            "wave"
        ],
        "replacement": "( * ^ *) ノシ"
    },
    {
        "triggers": [
            "whaa"
        ],
        "replacement": "Ö"
    },
    {
        "triggers": [
            "whistle"
        ],
        "replacement": "(っ^з^)♪♬"
    },
    {
        "triggers": [
            "whoa"
        ],
        "replacement": "(°o•)"
    },
    {
        "triggers": [
            "why"
        ],
        "replacement": "ლ(`◉◞౪◟◉‵ლ)"
    },
    {
        "triggers": [
            "woo"
        ],
        "replacement": "＼(＾O＾)／"
    },
    {
        "triggers": [
            "wtf"
        ],
        "replacement": "(⊙＿⊙\")"
    },
    {
        "triggers": [
            "wut"
        ],
        "replacement": "⊙ω⊙"
    },
    {
        "triggers": [
            "yay"
        ],
        "replacement": "\\( ﾟヮﾟ)/"
    },
    {
        "triggers": [
            "yeah",
            "yes"
        ],
        "replacement": "(•̀ᴗ•́)و ̑̑"
    },
    {
        "triggers": [
            "yen"
        ],
        "replacement": "¥"
    },
    {
        "triggers": [
            "yinyang",
            "yy"
        ],
        "replacement": "☯"
    },
    {
        "triggers": [
            "yolo"
        ],
        "replacement": "Yᵒᵘ Oᶰˡʸ Lᶤᵛᵉ Oᶰᶜᵉ"
    },
    {
        "triggers": [
            "youkids",
            "ukids"
        ],
        "replacement": "ლ༼>╭ ͟ʖ╮<༽ლ"
    },
    {
        "triggers": [
            "y u no",
            "yuno"
        ],
        "replacement": "(屮ﾟДﾟ)屮 Y U NO"
    },
    {
        "triggers": [
            "zen",
            "meditation",
            "omm"
        ],
        "replacement": "⊹╰(⌣ʟ⌣)╯⊹"
    },
    {
        "triggers": [
            "zoidberg"
        ],
        "replacement": "(V) (°,,,,°) (V)"
    },
    {
        "triggers": [
            "zombie"
        ],
        "replacement": "[¬º-°]¬"
    }
]
