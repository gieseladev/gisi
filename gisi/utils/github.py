import json

from . import JsonObject


async def create_gist(session, description, files, public=False):
    gist = {
        "description": description,
        "files": {key: {"content": str(value)} for key, value in dict(files).items()},
        "public": public
    }
    post_data = json.dumps(gist).encode("utf-8")
    async with session.post("https://api.github.com/gists", data=post_data) as resp:
        data = await resp.json()
    return JsonObject(data)
