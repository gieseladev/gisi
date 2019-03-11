import asyncio

import sentry_sdk

import gisi


def main():
    loop = asyncio.get_event_loop()

    sentry_sdk.init(release=gisi.constants.Info.version)

    g = gisi.Gisi()
    loop.run_until_complete(g.run())


if __name__ == "__main__":
    main()
