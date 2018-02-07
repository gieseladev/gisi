import re

import validators
from discord.ext.commands import BadArgument, Converter


class UrlConverter(Converter):
    scheme_check = r"^http(s?)://"

    async def convert(self, ctx, argument):
        url = argument.strip()
        if not re.match(self.scheme_check, url):
            url = f"http://{url}"
        try:
            validators.url(url)
        except validators.ValidationFailure:
            raise BadArgument(f"\"{url}\" isn't a valid url!")
        return url
