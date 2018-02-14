"""Text utilities."""

from functools import partial

# : is used for urls
DISCORD_FORMATTING_CHARS = {"*", "_", "~", "`", "\\", ":"}
BOLD_SEQ = "**"
ITALIC_SEQ = "*"
STRIKETHROUGH_SEQ = "~~"
CODE_SEQ = "```"
URL_ESCAPE_SEQ = ("<", ">")

QUOTE_CHAR = "\""
ESCAPE_CHAR = "\\"


def wrap(s, wrap):
    """Wrap around text."""
    if isinstance(wrap, (tuple, list, set)):
        start, end = wrap
        return start + s + end
    return wrap + s + wrap


bold = partial(wrap, wrap=BOLD_SEQ)
italic = partial(wrap, wrap=ITALIC_SEQ)
strikethrough = partial(wrap, wrap=STRIKETHROUGH_SEQ)
quote = partial(wrap, wrap=QUOTE_CHAR)
escape_url = partial(wrap, wrap=URL_ESCAPE_SEQ)


def code(s, lang):
    """Put it in a code block."""
    return f"{CODE_SEQ}{lang}\n{s}{CODE_SEQ}"


def escape(s):
    """Escape discord formatting in string."""
    res = ""
    for c in s:
        if c in DISCORD_FORMATTING_CHARS:
            res += ESCAPE_CHAR
        res += c
    return res


def fit_sentences(text, max_length=None, max_sentences=None, at_least_one=True):
    sentences = text.split(".")
    new_sentences = [sentences.pop(0)] if at_least_one else []
    for sentence in sentences:
        if max_sentences and len(new_sentences) >= max_sentences:
            break
        if max_length and len(".".join(new_sentences)) + len(sentence) + 1 > max_length:
            break
        new_sentences.append(sentence)

    return ".".join(new_sentences) + "."
