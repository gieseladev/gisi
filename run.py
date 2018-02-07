import asyncio
import os
import json
import logging
import logging.config


log = logging.getLogger("gisi")


def setup_logging(loc):
    with open(loc, "r") as f:
        config = json.load(f)
    logging.config.dictConfig(config)
    log.debug("logging setup")


def main():
    import gisi
    setup_logging(gisi.constants.FileLocations.LOGGING)

    loop = asyncio.get_event_loop()

    while True:
        try:
            g = gisi.Gisi()
            loop.run_until_complete(g.run())
            break
        except gisi.ShutdownSignal:
            log.warning("shut down")
            break
        except gisi.RestartSignal:
            log.warning("restarting...")
        except BaseException as e:
            raise
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    log.warning("exiting!")
    loop.close()


if __name__ == "__main__":
    main()
