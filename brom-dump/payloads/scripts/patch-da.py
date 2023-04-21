#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

# This script patches the original Download Agent by injecting a BLX
# instruction at the specified offset. This instruction will jump to
# the piggyback payload located right after the original DA.

import argparse
import os
import re

from keystone import KS_ARCH_ARM, KS_MODE_THUMB, Ks


def main():
    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description="Inject BLX instruction that jumps at the end of the DA",
    )
    parser.add_argument("src", help="Source binary")
    parser.add_argument("ld", help="LD script with MEMORY region")
    parser.add_argument("pos", help="Position to inject a BLX at")
    parser.add_argument("dest", help="Output binary")
    args = parser.parse_args()

    # pos is a 0xHEX string. argparse doesn't interpret these
    # as numbers. Fix it manually
    args.pos = int(args.pos, 0)

    # Parse original DA memory region address
    ld_script = None
    with open(args.ld, "r") as fis:
        ld_script = fis.read()
    match = re.search(r"ORIGIN = (.+?),", ld_script)
    off_da = int(match.group(1), 0)

    # Get size of the source Download Agent
    src_sz = os.stat(args.src).st_size

    # Calculate the jump address (payload is right after the DA)
    off_jump = off_da + src_sz
    print(f"DA at {hex(off_da)}, put `BLX {hex(off_jump)}` at {hex(args.pos)}")

    # Generate machine code bytes for the BLX instruction
    engine = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    blx, _ = engine.asm(f"BLX {off_jump}", args.pos)
    blx = bytes(blx)

    # Read the original DA
    da = None
    with open(args.src, "rb") as fis:
        da = bytearray(fis.read())
    # Convert memory offset to file offset and patch bytes
    off_patch = args.pos - off_da
    for i in range(0, len(blx)):
        da[off_patch + i] = blx[i]

    # Save modified DA
    with open(args.dest, "wb") as fos:
        fos.write(da)


if __name__ == "__main__":
    main()
