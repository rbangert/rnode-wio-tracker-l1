#!/usr/bin/env python
"""Teach the installed rnodeconf about the Seeed Wio Tracker L1.

Adds the provisional product/model IDs used by BOARD_WIO_L1 (see Boards.h) to
rnodeconf's ROM constants, product names and model table, so that it can
bootstrap the EEPROM, print device info and validate radio parameters.

Idempotent: running it again on an already patched rnodeconf does nothing.
Re-run after upgrading the rns package.
"""

import importlib.util
import sys

MARKER = "# Wio Tracker L1 (local patch)"

# (anchor, text inserted after the anchor)
PATCHES = [
    ("    MODEL_17            = 0x17\n",
     "\n    " + MARKER + "\n"
     "    PRODUCT_WIO_L1      = 0x18\n"
     "    MODEL_18            = 0x18\n"),
    ('    ROM.PRODUCT_TECHO:  "LilyGO T-Echo",\n',
     '    ROM.PRODUCT_WIO_L1: "Seeed Wio Tracker L1",\n'),
    ('    0x17: [779000000, 928000000, 22, "779 - 928 Mhz", "rnode_firmware_techo.zip", "SX1262"],\n',
     '    0x18: [862000000, 930000000, 22, "862 - 930 MHz", "rnode_firmware_wio_l1.zip", "SX1262"],\n'),
]


def rnodeconf_path():
    spec = importlib.util.find_spec("RNS.Utilities.rnodeconf")
    if spec is None or spec.origin is None:
        sys.exit("rnodeconf not found. Install it with: pip install rns")
    return spec.origin


def patch(path=None, quiet=False):
    path = path or rnodeconf_path()
    with open(path, encoding="utf-8", newline="") as f:
        src = f.read()

    if MARKER in src:
        if not quiet:
            print(f"Already patched: {path}")
        return path

    nl = "\r\n" if "\r\n" in src else "\n"
    for anchor, addition in PATCHES:
        anchor = anchor.replace("\n", nl)
        addition = addition.replace("\n", nl)
        count = src.count(anchor)
        if count != 1:
            sys.exit(f"Patch anchor found {count} times, rnodeconf layout has changed:\n{anchor.strip()}")
        src = src.replace(anchor, anchor + addition)

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    if not quiet:
        print(f"Patched: {path}")
    return path


if __name__ == "__main__":
    patch(sys.argv[1] if len(sys.argv) > 1 else None)
