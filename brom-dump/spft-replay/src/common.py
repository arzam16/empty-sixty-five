# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2021 Dinolek <https://github.com/Dinolek>
# SPDX-FileContributor: chaosmaster <https://github.com/chaosmaster>
# SPDX-FileContributor: arzamas-16 <https://github.com/arzamas-16>

import logging
import struct
import time


def bit(n):
    return 1 << n


def raise_(ex):
    raise ex


def to_bytes(value, size=1, endian=">"):
    return {
        1: lambda: struct.pack(endian + "B", value),
        2: lambda: struct.pack(endian + "H", value),
        4: lambda: struct.pack(endian + "I", value),
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()


def from_bytes(value, size=1, endian=">"):
    return {
        1: lambda: struct.unpack(endian + "B", value)[0],
        2: lambda: struct.unpack(endian + "H", value)[0],
        4: lambda: struct.unpack(endian + "I", value)[0],
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()


# Represent an object as hex string
def as_hex(obj, size=4):
    if isinstance(obj, list) or isinstance(obj, tuple):
        return ", ".join(as_hex(i) for i in obj)
    elif isinstance(obj, bytes):
        return obj.hex().upper()
    elif isinstance(obj, int):
        fmt = "{:0" + str(size * 2) + "X}"
        return fmt.format(obj)
    else:
        return "?" * (size * 2)


# Same as above but prefixed with 0x
def as_0x(obj, size=4):
    if isinstance(obj, list) or isinstance(obj, tuple):
        return ", ".join("0x" + as_hex(i, size) for i in obj)
    else:
        return "0x" + as_hex(obj, size)


# Print progress every 300 ms or when reach 100%
last_progr_upd_at = 0
last_progr_perc = -1


def report_write_progress(off_start, off_end, data_sz):
    global last_progr_upd_at, last_progr_perc

    THRESHOLD = 16  # Print progress only when writing more than 16 bytes
    if data_sz < THRESHOLD:
        return

    perc_progr = int(off_end / data_sz * 100)
    if perc_progr < last_progr_perc:  # occurs when the previous transfer is done
        last_progr_perc = 0

    time_delta = time.time() - last_progr_upd_at
    if time_delta >= 0.3 or perc_progr == 0 or perc_progr == 100:
        logging.info(f"Uploaded {off_end} out of {data_sz} bytes ({perc_progr}%)")
        last_progr_upd_at = time.time()
        last_progr_perc = perc_progr


def target_config_to_string(config):
    return [
        f"Raw target config value: {as_hex(config)}",
        f"Secure boot: {'YES' if config & bit(1) else 'NO'}",
        f"Serial link auth: {'YES' if config & bit(2) else 'NO'}",
        f"Download agent auth: {'YES' if config & bit(3) else 'NO'}",
    ]
