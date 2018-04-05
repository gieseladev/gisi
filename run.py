import asyncio
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
            if g._signal:
                if g._signal == gisi.GisiSignal.SHUTDOWN:
                    break
            else:
                log.info("No signal found... Restarting!")
        except KeyboardInterrupt:
            log.warning("shutting down")
            break
        except BaseException as e:
            raise


if __name__ == "__main__":
    main()
