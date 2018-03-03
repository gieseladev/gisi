import pytest
from discord.ext.commands import BadArgument


async def perform_test(conv, tests):
    for inp, works, expected in tests:
        try:
            out = await conv.convert(None, inp)
        except BadArgument:
            if works:
                raise Exception(f"{inp} didn't work even though it should!")
        else:
            if not works:
                raise Exception(f"{inp} worked even though it shouldn't!")
            if out != expected:
                raise Exception(f"Output didn't match expected output ({out} != {expected})")


@pytest.mark.asyncio
async def test_converter():
    from gisi.utils import converter

    await perform_test(converter.UrlConverter(), [
        ("www.google.com", True, "http://www.google.com"),
        ("keker", False, None),
        ("http://httpbin.org/", True, "http://httpbin.org/")
    ])

    flags = converter.FlagConverter.from_string("this is the first arg -flag value -g testing testing tra --tra - tra")
    assert flags.get(0) == "this is the first arg"
    assert flags.get("flag") == "value"
