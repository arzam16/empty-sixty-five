#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: 2023 arzamas-16 <https://github.com/arzamas-16>

# Piggyback payloads are placed on top of the original Download Agents.
# For building a working piggyback we must set its base address.
# This script takes the `memory.ld` script for a specific target, reads
# the base address of the original DA and recalculates it for a piggyback.
# The output LD script is then saved.

import argparse
import os
import re


def main():
    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description="Generate LD scripts for piggyback payloads",
    )
    parser.add_argument("src", help="Source LD script with DA memory region defined")
    parser.add_argument("da", help="Executable that will have a piggyback attached to")
    parser.add_argument("dest", help="Output LD script")
    args = parser.parse_args()

    ld_script = None
    with open(args.src, "r") as fis:
        ld_script = fis.read()

    # Get size of the base binary
    da_sz = os.stat(args.da).st_size

    # Parse original DA memory region address
    match = re.search(r"ORIGIN = (.+?),", ld_script)
    off_da = int(match.group(1), 16)

    # Piggyback offset is the next byte after the base executable
    off_piggyback = off_da + da_sz

    # Substitute the new value and write it
    ld_script = ld_script.replace(match.group(0), f"ORIGIN = {hex(off_piggyback)},")

    with open(args.dest, "w") as fos:
        fos.write(ld_script)


if __name__ == "__main__":
    main()
