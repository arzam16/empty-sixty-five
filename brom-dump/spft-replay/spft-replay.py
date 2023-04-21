#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import argparse
import logging
from functools import partial, partialmethod

from src.common import as_0x, as_hex, from_bytes
from src.device import Device
from src.manager import DeviceManager

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
    mode_parser = parser.add_mutually_exclusive_group()
    mode_parser.add_argument(
        "-r",
        dest="mode_receive",
        action="store_true",
        help="Receive mode: wait for >Mtk and <Mtk magics and save data to files",
    )
    mode_parser.add_argument(
        "-g",
        dest="mode_greedy",
        action="store_true",
        help="Greedy mode: receive and print all data after jumping to "
        "payload (4 bytes at a time)",
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
    except:
        logging.critical("Handshake error!", exc_info=True)

    manager = DeviceManager(device)
    try:
        manager.replay(da)
    except:
        logging.critical("Replay error!", exc_info=True)

    if args.mode_greedy:
        handle_greedy(device)
    elif args.mode_receive:
        handle_receive(device)

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


def handle_greedy(device):
    logging.info("Greedy mode! Waiting for incoming data... :)")
    logging.info("Hit Ctrl+C to stop waiting")
    try:
        data = None
        while True:
            data = device.read(4)
            if not data:
                logging.error("Cannot receive data!")
                break
            logging.info(f"<- DA: {as_hex(data)}")
    except KeyboardInterrupt:
        logging.info("Stopped reading")


def handle_receive(device):
    logging.info("Waiting for custom payload response")

    # This function is prone to errors.
    # TODO: add more try-except!

    seq = from_bytes(device.read(4), 4)
    if seq == 0x3E4D746B:  # >Mtk
        logging.info("Received HELLO sequence")
    else:
        logging.info(f"Received invalid data {as_hex(seq)}, expected HELLO sequence")

    idx = 1
    size = from_bytes(device.read(4), 4)
    while size != 0x4D746B3C:  # <Mtk
        logging.info(f"Reading {size} bytes")
        data = device.read(size)
        filename = f"dump-{idx}.bin"
        with open(filename, "wb") as fos:
            fos.write(data)
        logging.info(f"Saved to {filename}")

        idx += 1
        size = from_bytes(device.read(4), 4)

    logging.info("Received GOODBYE sequence")


if __name__ == "__main__":
    main()
