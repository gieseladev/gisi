import json
import os

import pytest


def pytest_sessionstart(session):
    from gisi.constants import FileLocations
    config = {
        "token": os.environ["DISCORD_TOKEN"],
        "mongodb_uri": os.environ["MONGODB_URI"],
        "google_api_key": os.environ["GOOGLE_API_KEY"]
    }
    with open(FileLocations.CONFIG, "w+") as f:
        json.dump(config, f)


@pytest.mark.asyncio
async def test_setup():
    import gisi
    gisi.Gisi()


@pytest.mark.asyncio
async def test_login():
    import gisi
    g = gisi.Gisi()
    await g.run()
