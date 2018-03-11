from os import path

import traceback
from discord import Embed, Member, User
from discord.embeds import EmptyEmbed
from discord.ext.commands import Context

from gisi.constants import Colours


def create_exception_embed(exc_type, exc_msg, exc_tb, tb_limit=None):
    stack = traceback.extract_tb(exc_tb, limit=tb_limit)

    tb = []
    for filename, line_num, func_name, text in stack[-tb_limit:]:
        try:
            filepath = path.relpath(filename)
        except ValueError:
            filepath = filename
        tb.append(f"{func_name} (line {line_num} in {filepath})\n{text}")
    formatted_tb = "\n\n".join(tb)
    return Embed(title="Exception Info", colour=Colours.ERROR,
                 description=f"type: **{exc_type}**\nmessage:```\n{exc_msg}```\n\ntraceback:```\n{formatted_tb}```")


async def add_embed(msg, *, author=None, image=None, title=EmptyEmbed, description=EmptyEmbed, colour=EmptyEmbed,
                    timestamp=EmptyEmbed, footer_text=EmptyEmbed, footer_icon=EmptyEmbed):
    if colour is True:
        colour = Colours.SUCCESS
    elif colour is False:
        colour = Colours.ERROR
    em = Embed(title=title, description=description, colour=colour, timestamp=timestamp)
    if author:
        if isinstance(author, (Member, User)):
            author = {
                "name": author.name,
                "icon_url": author.avatar_url
            }
        em.set_author(**author)
    if image:
        em.set_image(url=image)
    em.set_footer(text=footer_text, icon_url=footer_icon)
    if isinstance(msg, Context):
        msg = msg.message
    await msg.edit(embed=em)


def copy_embed(embed):
    return Embed.from_data(embed.to_dict())


class EmbedPaginator:
    MAX_FIELDS = 25
    MAX_FIELD_NAME = 256
    MAX_FIELD_VALUE = 1024
    MAX_TOTAL = 2000

    def __init__(self, *, first_embed=None, every_embed=None):
        self.every_embed = every_embed or Embed()
        self.first_embed = first_embed or self.every_embed

        self._cur_embed = copy_embed(first_embed) if first_embed else self.create_embed()
        self._embeds = []

    def __str__(self):
        return f"<EmbedPaginator>"

    def __iter__(self):
        return iter(self.embeds)

    @property
    def predefined_count(self):
        em = self._cur_embed
        return len(em.title or "") + len(em.description or "") + len(em.author.name or "") + len(em.footer.text or "")

    @property
    def total_count(self):
        return self.predefined_count + sum(len(field.name) + len(field.value) for field in self._cur_embed.fields)

    @property
    def embeds(self):
        self.close_embed()
        return self._embeds

    def create_embed(self):
        return copy_embed(self.every_embed)

    def close_embed(self):
        self._embeds.append(self._cur_embed)
        self._cur_embed = self.create_embed()

    def add_field(self, name, value, inline=False):
        if len(name) > self.MAX_FIELD_NAME:
            raise ValueError(f"Field name mustn't be longer than {self.MAX_FIELD_NAME} characters")
        if len(value) > self.MAX_FIELD_VALUE:
            raise ValueError(f"Field value mustn't be longer than {self.MAX_FIELD_VALUE} characters")
        count = len(name) + len(value)
        if self.total_count + count > self.MAX_TOTAL:
            self.close_embed()
        em = self._cur_embed
        em.add_field(name=name, value=value, inline=inline)
        if len(em.fields) >= self.MAX_FIELDS:
            self.close_embed()
