#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import argparse
import logging
from functools import partial, partialmethod

from src.common import as_0x
from src.device import Device
from src.replay import replay

LOG_LEVEL_REPLAY = logging.INFO + 1
LOG_LEVEL_BROM_CMD = logging.INFO - 1
LOG_LEVEL_BROM_IO = logging.DEBUG - 1


def main():
    parser = argparse.ArgumentParser(
        prog="spft-replay",
        description="""
Replay SP Flash Tool traffic to run Download Agents that can execute arbitrary code.
This tool works only with devices booted into BROM mode as I could not be arsed
to implement crashing Preloader for old platforms.
						""",
    )
    parser.add_argument("da_file", help="File to use as a payload")
    dbg_parser = parser.add_mutually_exclusive_group()
    dbg_parser.add_argument(
        "-v",
        dest="log_level",
        action="store_const",
        const=LOG_LEVEL_BROM_CMD,
        help="Verbose: print all executed commands",
    )
    dbg_parser.add_argument(
        "-vv",
        dest="log_level",
        action="store_const",
        const=LOG_LEVEL_BROM_IO,
        help="Super verbose: also print all read/write operations",
    )
    args = parser.parse_args()

    init_logging(args)

    da = None
    with open(args.da_file, "rb") as fis:
        da = fis.read()
    da_len = len(da)
    logging.info(f"Payload size {da_len} bytes ({as_0x(da_len)})")

    device = Device().find()
    if not device:
        logging.critical("Could not find device")
        exit(1)  # Exit immediately

    try:
        device.handshake()
        replay(device, da)
    except:
        # Don't exit, try to close the device
        logging.critical("Replay error!", exc_info=True)

    logging.info("Closing device")
    device.close()


def init_logging(args):
    # Add some logging levels. Source: https://stackoverflow.com/a/55276759
    logging.REPLAY = LOG_LEVEL_REPLAY
    logging.addLevelName(logging.REPLAY, "REPLAY")
    logging.Logger.replay = partialmethod(logging.Logger.log, logging.REPLAY)
    logging.replay = partial(logging.log, logging.REPLAY)

    logging.BROM = LOG_LEVEL_BROM_CMD
    logging.addLevelName(logging.BROM, "BROM CMD")
    logging.Logger.brom = partialmethod(logging.Logger.log, logging.BROM)
    logging.brom = partial(logging.log, logging.BROM)

    logging.BROM_IO = LOG_LEVEL_BROM_IO
    logging.addLevelName(logging.BROM_IO, "BROM I/O")
    logging.Logger.BROM_IO = partialmethod(logging.Logger.log, logging.BROM_IO)
    logging.brom_io = partial(logging.log, logging.BROM_IO)

    # Apply program-wide configuration
    log_level = args.log_level if args.log_level else logging.INFO
    logging.basicConfig(
        level=log_level, format="[%(asctime)s] <%(levelname)s> %(message)s"
    )


if __name__ == "__main__":
    main()
