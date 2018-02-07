import traceback
from os import path

from discord import Embed


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
    return Embed(title="Exception Info", colour=0xFF4F48,
                 description=f"type: **{exc_type}**\nmessage:```\n{exc_msg}```\n\ntraceback:```\n{formatted_tb}```")
