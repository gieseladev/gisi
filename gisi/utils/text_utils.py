"""Text utilities."""

import re
from functools import partial

# : is used for urls
DISCORD_FORMATTING_CHARS = {"*", "_", "~", "`", "\\", ":"}
BOLD_SEQ = "**"
ITALIC_SEQ = "*"
STRIKETHROUGH_SEQ = "~~"
CODE_SEQ = "`"
CODE_BLOCK_SEQ = "```"
URL_ESCAPE_SEQ = ("<", ">")

QUOTE_CHAR = "\""
ESCAPE_CHAR = "\\"


def wrap(s, wrap):
    """Wrap around text."""
    if isinstance(wrap, (tuple, list, set)):
        start, end = wrap
        return start + s + end
    return wrap + s + wrap


def is_inside(position: int, content: str, wrap: str, *, escapable=True):
    wrap = r"(?<!\\)" + wrap if escapable else wrap
    regex = re.compile(wrap + r"(?:\n|.)+?" + wrap)
    for match in regex.finditer(content):
        if match.end() > position > match.start():
            return True
    return False


bold = partial(wrap, wrap=BOLD_SEQ)
italic = partial(wrap, wrap=ITALIC_SEQ)
strikethrough = partial(wrap, wrap=STRIKETHROUGH_SEQ)
quote = partial(wrap, wrap=QUOTE_CHAR)
escape_url = partial(wrap, wrap=URL_ESCAPE_SEQ)

in_code = partial(is_inside, wrap=CODE_SEQ, escapable=True)
in_code_block = partial(is_inside, wrap=CODE_BLOCK_SEQ, escapable=True)


def is_code_block(s):
    s = s.strip()
    return s.startswith(CODE_BLOCK_SEQ) and s.endswith(CODE_BLOCK_SEQ)


def code(s, lang=""):
    """Put it in a code block."""
    return f"{CODE_BLOCK_SEQ}{lang}\n{s}{CODE_BLOCK_SEQ}"


def escape(s):
    """Escape discord formatting in string."""
    res = ""
    for c in s:
        if c in DISCORD_FORMATTING_CHARS:
            res += ESCAPE_CHAR
        res += c
    return res


def escape_if_needed(s, pos, text):
    if in_code(pos, text) or in_code_block(pos, text):
        return s
    else:
        return escape(s)


sentence_splitter = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[\.\?])\s")


def fit_sentences(text, max_length=None, max_sentences=None, at_least_one=True):
    sentences = sentence_splitter.split(text)
    new_sentences = [sentences.pop(0)] if at_least_one else []
    for sentence in sentences:
        if max_sentences and len(new_sentences) >= max_sentences:
            break
        if max_length and len(" ".join(new_sentences)) + len(sentence) > max_length:
            break
        new_sentences.append(sentence)

    return " ".join(new_sentences)
