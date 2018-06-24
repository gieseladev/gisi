import asyncio

import gisi


def main():
    loop = asyncio.get_event_loop()
    g = gisi.Gisi()
    loop.run_until_complete(g.run())


if __name__ == "__main__":
    main()
