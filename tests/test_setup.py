import asyncio
import json
import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def session_start():
    from gisi.constants import FileLocations
    print(os.environ)
    config = {
        "token": os.environ["DISCORD_TOKEN"],
        "mongodb_uri": os.environ["MONGODB_URI"],
        "google_api_key": os.environ["GOOGLE_API_KEY"]
    }
    with open(FileLocations.CONFIG, "w+") as f:
        json.dump(config, f)


@pytest.mark.asyncio
async def test_login():
    import gisi
    g = gisi.Gisi()
    try:
        await asyncio.wait(g.run(), timeout=5)
    except asyncio.TimeoutError:
        pass
