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
    mode_parser = parser.add_mutually_exclusive_group()
    mode_parser.add_argument(
        "-i",
        dest="mode_identify",
        action="store_true",
        help="Identify mode: print hardware info and exit",
    )
    mode_parser.add_argument(
        "-p",
        dest="mode_payload",
        metavar="PAYLOAD",
        action="store",
        help="Payload mode: push PAYLOAD to device",
    )
    payload_options = parser.add_mutually_exclusive_group()
    payload_options.add_argument(
        "-pr",
        dest="mode_payload_receive",
        action="store_true",
        help="[Payload mode only] Receive data: Wait for >Mtk and <Mtk "
        "magics and save data to files with sequential names.",
    )
    payload_options.add_argument(
        "-pg",
        dest="mode_payload_greedy",
        action="store_true",
        help="[Payload mode only] Be greedy: receive and print all data "
        "after jumping to payload (4 bytes at a time).",
    )
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

    device = Device().find()
    if not device:
        logging.critical("Could not find device")
        exit(1)  # Exit immediately

    try:
        device.handshake()
    except:
        logging.critical("Handshake error!", exc_info=True)

    manager = DeviceManager(device)
    if args.mode_identify:
        identify_mode(manager)
    elif args.mode_payload:
        payload_mode(args, manager)

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


def identify_mode(manager):
    try:
        manager.identify()
    except:
        logging.critical("Identification error!", exc_info=True)


def payload_mode(args, manager):
    try:
        # Read the payload from file
        payload = None
        with open(args.mode_payload, "rb") as fis:
            payload = fis.read()
        payload_len = len(payload)
        logging.info(f"Payload size {payload_len} bytes ({as_0x(payload_len)})")

        # Launch replay and push payload
        manager.replay(payload)

        # Handle incoming data
        if args.mode_payload_greedy:
            handle_greedy(manager.dev)
        elif args.mode_payload_receive:
            handle_receive(manager.dev)
    except:
        logging.critical("Replay error!", exc_info=True)


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
