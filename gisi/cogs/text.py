import inspect
import logging
import marshal
import random
import re
import shlex
import textwrap
from collections import namedtuple

import pymongo.errors
from discord import Embed
from discord.ext.commands import group

from gisi import SetDefaults
from gisi.constants import Colours
from gisi.utils import text_utils

log = logging.getLogger(__name__)

COMPLEX_REPLACER_TESTS = [
    ["gisi"],
    ["1"],
    ["123"],
    ["gisi#0001"],
    ["gisi", "is", "the", "worst"],
    ["2", "gisis", "are", "too", "much"],
    ["01238", "1237", "19"],
    ["this is a long text for gisi"]
]


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
        await self.replacers.create_index("triggers", name="triggers", unique=True)
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
        replacement = repl["replacement"]
        if isinstance(replacement, bytes):
            replacer = parse_replacer(replacement)
            replacement = str(replacer.get(*args))
        return replacement

    async def replace_text(self, text, require_wrapping=True):
        if text_utils.is_code_block(text):
            return text

        simple_re = re.compile(r"(?<!\\)\-(\w+)\-" if require_wrapping else r"(\w+)")
        combined_open, combined_close = "<>"

        start = 0
        while True:
            match = simple_re.search(text, start)
            if not match:
                break
            start = match.end()
            if text_utils.in_code_block(start, text):
                continue
            key = match.group(1).lower()
            new = await self.get_replacement(key, ())
            if not new:
                continue
            pre = text[:match.start()]
            after = text[match.end():]
            new = text_utils.escape_if_needed(new, start, text)
            text = f"{pre}{new}{after}"

        if require_wrapping:
            stack = []
            current_string = ""
            escape = False
            for ind, char in enumerate(text):
                if escape:
                    current_string += char
                    escape = False
                    continue
                elif char is text_utils.ESCAPE_CHAR:
                    current_string += char
                    escape = True
                    continue

                if char is combined_open:
                    stack.append(current_string)
                    current_string = combined_open
                elif char is combined_close:
                    current_string += combined_close
                    part = current_string
                    new = None
                    if part and part.startswith(combined_open):
                        key, *args = shlex.split(part[1:-1])
                        key = key.lower()
                        new = await self.get_replacement(key, args)
                        if new:
                            new = text_utils.escape_if_needed(new, ind, text)
                    part = new or part
                    current_string = stack.pop() if stack else ""
                    current_string += part
                else:
                    current_string += char
            text = "".join(stack) + current_string
        return text

    @group(invoke_without_command=True)
    async def replace(self, ctx):
        """Find and convert asciimojis.

        For each word try to find a asciimoji and use it.
        """
        new_content = await self.replace_text(ctx.clean_content, require_wrapping=False)
        await ctx.message.edit(content=new_content)

    @replace.group(invoke_without_command=True)
    async def add(self, ctx):
        """Add a replacer

        Use
            [p]replace add simple - To add a simple match-replace replacer
            [p]replace add complex - To add a complex replacer
        """
        pass

    @add.command()
    async def simple(self, ctx, trigger, replacement):
        """Add a simple replacer.

        It's simple because <trigger> will be replaced with <replacement> and that's it.
        """
        triggers = [trig.strip().lower() for trig in trigger.split(",")]
        try:
            await self.replacers.insert_one({"triggers": triggers, "replacement": replacement})
        except pymongo.errors.DuplicateKeyError:
            em = Embed(description=f"There's already a replacer for {trigger}", colour=Colours.ERROR)
            await ctx.message.edit(embed=em)
        else:
            em = Embed(description=f"{trigger} -> {replacement}", colour=Colours.INFO)
            await ctx.message.edit(embed=em)

    @add.command(usage="<trigger> <code>")
    async def complex(self, ctx, trigger):
        """Add a complex replacer.

        A complex replacer calls a function to determine the proper replacement to replace <trigger> with.
        Write some kind of python code which returns the string you want to replace the <trigger> with.
        You may use the array "args" which contains the arguments that were passed.

        Example Code:
        text = args[0] if args else "Your code has to work with every kind of input!"
        return text

        This will turn -trigger some_text- into some_text
        """
        triggers = [trig.strip().lower() for trig in trigger.split(",")]
        code = ctx.clean_content[len(trigger) + 1:]
        code = code.strip("\n").strip("```python").strip("\n")
        comp = compile_replacer(code)
        replacer = parse_replacer(comp)
        try:
            tests = []
            for test in COMPLEX_REPLACER_TESTS:
                test_string = " ".join(test)
                res = replacer.get(*test)
                if not res:
                    raise ValueError(f"Test {test} didn't return a value!")
                if not test_string.startswith(res):
                    tests.append((test_string, res))
        except Exception as e:
            em = Embed(title="Your oh so \"complex\" code threw an error", description=f"{e}", colour=Colours.ERROR)
            await ctx.message.edit(embed=em)
            return
        replacement = dump_replacer(comp)
        try:
            await self.replacers.insert_one({"triggers": triggers, "replacement": replacement})
        except pymongo.errors.DuplicateKeyError:
            em = Embed(description=f"There's already a replacer for {trigger}", colour=Colours.ERROR)
            await ctx.message.edit(embed=em)
        else:
            sample = random.sample(tests, 4) if len(tests) >= 4 else tests
            replacement_string = "\n".join(f"{_trigger} -> {_replacement}" for _trigger, _replacement in sample)
            em = Embed(title=f"Added complex replacer for {trigger}", description=replacement_string,
                       colour=Colours.INFO)
            await ctx.message.edit(embed=em)

    @replace.command()
    async def remove(self, ctx, trigger):
        """Remove a replacer."""
        result = await self.replacers.delete_one({"triggers": trigger.lower()})
        self.cached_replacers.clear()
        if result.deleted_count:
            em = Embed(description=f"Removed {trigger}", colour=Colours.INFO)
            await ctx.message.edit(embed=em)
        else:
            em = Embed(description=f"There's no replacer for {trigger}", colour=Colours.ERROR)
            await ctx.message.edit(embed=em)

    @replace.group(invoke_without_command=True)
    async def alias(self, ctx):
        """Aliases for replacements.
        Use
            [p]replace alias add - To add a new alias for a replacer
            [p]replace alias remove - To remove an alias from a replacer
        """
        pass

    @alias.command(name="add")
    async def add_alias(self, ctx, trigger, new_trigger):
        """Add a new trigger for an already existing trigger"""
        new_triggers = [trig.strip().lower() for trig in new_trigger.split(",")]
        try:
            result = await self.replacers.update_one({"triggers": trigger.lower()},
                                                     {"$push": {"triggers": {"$each": new_triggers}}})
        except pymongo.errors.DuplicateKeyError:
            em = Embed(description=f"There's already a replacer for {trigger}", colour=Colours.ERROR)
            await ctx.message.edit(embed=em)
        else:
            if result.modified_count:
                em = Embed(description=f"Added {new_trigger} for {trigger}", colour=Colours.INFO)
                await ctx.message.edit(embed=em)
            else:
                em = Embed(description=f"There's no replacer for {trigger}", colour=Colours.ERROR)
                await ctx.message.edit(embed=em)

    @alias.command(name="remove")
    async def remove_alias(self, ctx, trigger):
        """Remove a trigger for an already existing trigger

        You cannot remove a trigger if it's the last trigger for a replacer.
        """
        replacer = await self.replacers.find_one({"triggers": trigger.lower()})
        self.cached_replacers.clear()
        if not replacer:
            em = Embed(description=f"Trigger {trigger} doesn't exist!", colour=Colours.ERROR)
            await ctx.message.edit(embed=em)
            return
        if len(replacer["triggers"]) <= 1:
            em = Embed(description=f"Trigger {trigger} cannot be removed as it is the only trigger for this replacer!",
                       colour=Colours.ERROR)
            await ctx.message.edit(embed=em)
            return
        await self.replacers.update_one({"triggers": trigger.lower()}, {"$pull": {"triggers": trigger.lower()}})
        em = Embed(description=f"Removed {trigger}", colour=Colours.INFO)
        await ctx.message.edit(embed=em)

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
        ctx = await self.bot.get_context(message)
        if ctx.command:
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


ComplexReplacer = namedtuple("ComplexReplacer", ("version", "get"))


def parse_replacer(replacer):
    if not inspect.iscode(replacer):
        replacer = marshal.loads(replacer)
    repl = {}
    exec(replacer, repl)
    return ComplexReplacer(repl["version"], repl["func"])


def compile_replacer(code):
    code = textwrap.indent(textwrap.dedent(code.strip("\n")), "\t")
    source = """
    version = "1.0.0"
    def transpose(text, table, backwards=False):
        result = []
        for char in text:
            result.append(table.get(char, char))
        if backwards:
            result = reversed(result)
        return "".join(result)
    def func(*args):
    {code}
    """
    source = textwrap.dedent(source)
    source = source.format(code=code)
    try:
        comp = compile(source, "<string>", "exec", optimize=2)
    except (SyntaxError, ValueError):
        raise
    else:
        return comp


def dump_replacer(code):
    if not inspect.iscode(code):
        code = compile_replacer(code)
    return marshal.dumps(code)


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
        "triggers": ["dollarbill", "$"],
        "replacement": dump_replacer("""
            amount = args[0] if args else "10"
            table = {
                "0": "ο̲̅",
                "1": "̅ι",
                "2": "2̅",
                "3": "3̅",
                "4": "4̅",
                "5": "5̲̅",
                "6": "6̅",
                "7": "7̅",
                "8": "8̅",
                "9": "9̅",
            }
            return f"[̲̅$̲̅({transpose(amount, table)}̅)̲̅$̲̅]"
        """)
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
            "fancytext"
        ],
        "replacement": dump_replacer("""
        text = args[0] if args else "beware, i am fancy!"
        table = {
            "a": "α",
            "b": "в",
            "c": "¢",
            "d": "∂",
            "e": "є",
            "f": "ƒ",
            "g": "g",
            "h": "н",
            "i": "ι",
            "j": "נ",
            "k": "к",
            "l": "ℓ",
            "m": "м",
            "n": "η",
            "o": "σ",
            "p": "ρ",
            "q": "q",
            "r": "я",
            "s": "ѕ",
            "t": "т",
            "u": "υ",
            "v": "ν",
            "w": "ω",
            "x": "χ",
            "y": "у",
            "z": "z",
        }
        return transpose(text.lower(), table)
        """)
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
            "fliptext"
        ],
        "replacement": dump_replacer("""
        text = args[0] if args else "flip me like a table"
        table = {
            "a": "ɐ",
            "b": "q",
            "c": "ɔ",
            "d": "p",
            "e": "ǝ",
            "f": "ɟ",
            "g": "ƃ",
            "h": "ɥ",
            "i": "ı",
            "j": "ɾ",
            "k": "ʞ",
            "l": "ן",
            "m": "ɯ",
            "n": "u",
            "p": "d",
            "q": "b",
            "r": "ɹ",
            "t": "ʇ",
            "u": "n",
            "v": "ʌ",
            "w": "ʍ",
            "y": "ʎ",
            ".": "˙",
            "[": "]",
            "(": ")",
            "{": "}",
            "?": "¿",
            "!": "¡",
            "'": ",",
            "<": ">",
            "_": "‾",
            "\\"": "„",
            "\\\\": "\\\\",
            ";": "؛",
            "‿": "⁀",
            "⁅": "⁆",
            "∴": "∵"
        }
        return transpose(text.lower(), table, True)
        """)
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
            "peace"
        ],
        "replacement": "✌(-‿-)✌"
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
