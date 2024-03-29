#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

import argparse
import logging
from functools import partial, partialmethod

from src.brom import BromProtocol
from src.common import as_0x
from src.manager import DeviceManager
from src.transport import UsbTransport

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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "-i",
        dest="mode_identify",
        action="store_true",
        help="Identify mode: print hardware info and exit",
    )
    mode.add_argument(
        "-p",
        dest="mode_payload",
        metavar="PAYLOAD",
        action="store",
        help="Payload mode: replay SP Flash Tool traffic for a device "
        "then push PAYLOAD and jump to it",
    )
    mode.add_argument(
        "-s",
        dest="mode_simple_payload",
        metavar="PAYLOAD",
        action="store",
        help="Simple payload mode: just disable the watchdog then push "
        "PAYLOAD to device and jump to it",
    )

    parser.add_argument(
        "-sr",
        dest="skip_remaining_data",
        action="store_true",
        help="[Payload mode only] Skip receiving remaining data after "
        "jumping to payload. This option is very useful for standalone "
        "payloads. However, using this option with piggyback payloads "
        "WILL BREAK the flow.",
    )

    recv = parser.add_mutually_exclusive_group()
    recv.add_argument(
        "-pr",
        dest="mode_payload_receive",
        action="store_true",
        help="[Payload mode only] Receive data: Wait for >Mtk and <Mtk "
        "magics and save data to files with sequential names.",
    )
    recv.add_argument(
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

    # spft-replay supports only the USB transport as of now, but it
    # shouldn't be hard to implement the UART transport using pyserial.
    transport = UsbTransport()
    transport.start()

    brom = BromProtocol(transport)
    try:
        brom.handshake()
    except:
        logging.critical("Handshake error!", exc_info=True)

    manager = DeviceManager(brom)
    if args.mode_identify:
        identify_mode(manager)
    elif args.mode_payload or args.mode_simple_payload:
        payload_mode(args, manager)

    logging.info("Stopping transport")
    transport.stop()


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
        payload_path = args.mode_payload or args.mode_simple_payload
        with open(payload_path, "rb") as fis:
            payload = fis.read()
        payload_len = len(payload)
        logging.info(f"Payload size {payload_len} bytes ({as_0x(payload_len)})")

        # Launch replay and push payload
        simple_mode = bool(args.mode_simple_payload)
        skip_remaining_data = args.skip_remaining_data
        manager.replay(payload, simple_mode, skip_remaining_data)

        # Handle incoming data
        if args.mode_payload_receive:
            manager.receive_data()
        elif args.mode_payload_greedy:
            manager.receive_greedy()
    except:
        logging.critical("Replay error!", exc_info=True)


if __name__ == "__main__":
    main()
