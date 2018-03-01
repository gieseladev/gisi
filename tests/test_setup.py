import pytest


@pytest.mark.asyncio
async def test_setup():
    import gisi
    gisi.Gisi()
