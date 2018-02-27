import re
import shlex
from collections import Iterable
from contextlib import suppress

import validators
from discord.ext.commands import BadArgument, Command, Converter

_default = object()


class UrlConverter(Converter):
    scheme_check = r"^http(s?)://"

    async def convert(self, ctx, argument):
        url = argument.strip("<>")
        if not re.match(self.scheme_check, url):
            url = f"http://{url}"
        try:
            validators.url(url)
        except validators.ValidationFailure:
            raise BadArgument(f"\"{url}\" isn't a valid url!")
        return url


def convert(obj, cls):
    if cls is bool and isinstance(obj, str):
        return obj.lower() in ("y", "yes", "t", "true")
    try:
        conv = cls(obj)
    except Exception:
        raise TypeError(f"can't convert {obj} ({type(obj)}) to {cls}")
    else:
        return conv


class FlagConverter:
    def __init__(self, args, flags):
        self.args = args
        self.flags = flags

    def __getitem__(self, item):
        return self.get(item)

    def __getattr__(self, item):
        return self.get(item)

    def __contains__(self, item):
        return item in self.flags

    @property
    def arg_count(self):
        return len(self.args)

    @property
    def flag_count(self):
        return len(self.flags)

    @classmethod
    def from_spec(cls, spec: Iterable, *, flag_arg_default=True):
        args = []
        flags = {}

        current_flag = None
        current_args = []
        for sp in spec:
            if sp.startswith("-"):
                name = sp.lstrip("-")
                if not name:
                    current_args.append(sp)
                    continue
                if current_flag:
                    flags[current_flag] = " ".join(current_args) if current_args else flag_arg_default
                elif current_args:
                    args.append(" ".join(current_args))
                current_flag = name
                current_args = []
            else:
                current_args.append(sp)
        if current_flag:
            flags[current_flag] = " ".join(current_args) if current_args else flag_arg_default
        elif current_args:
            args.append(" ".join(current_args))

        return cls(args, flags)

    @classmethod
    def from_string(cls, text: str, **kwargs):
        spec = shlex.split(text)
        return cls.from_spec(spec, **kwargs)

    def get(self, key, default=_default):
        try:
            if isinstance(key, str) or not isinstance(key, Iterable):
                key = [key]
            for k in key:
                with suppress(KeyError, IndexError):
                    if isinstance(k, str):
                        return self.flags[k]
                    else:
                        return self.args[k]
            else:
                raise KeyError(f"{key} not found!")
        except KeyError as e:
            if default is _default:
                raise e
            else:
                return default

    def convert(self, key, target, default=_default):
        try:
            value = self.get(key)
            return convert(value, target)
        except (KeyError, TypeError) as e:
            if default is _default:
                raise e
            else:
                return default

    async def convert_dis(self, key, ctx, converter, default=_default):
        try:
            argument = self.get(key)
            return await Command.do_conversion(None, ctx, converter, argument)
        except Exception as e:
            if default is _default:
                raise e
            else:
                return default
