async def upload(session, content):
    """Upload content to hastebin.
    :param session: aiohttp ClientSession to use
    :param content: content to upload
    :returns: url to post
    """
    async with session.post("https://hastebin.com/documents", data=content.encode("utf-8")) as resp:
        data = await resp.json()
    return "https://hastebin.com/{}".format(data["key"])
