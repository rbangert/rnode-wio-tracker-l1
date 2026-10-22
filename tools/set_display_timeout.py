#!/usr/bin/env python
"""Set the OLED blanking timeout on a provisioned Wio Tracker L1.

RNode never blanks the screen unless a timeout is stored in EEPROM, so a freshly
provisioned board keeps the display on. This stores one (persists across reboots
and reflashes). install_wio_l1.py does the same as its last step.

Usage:
  python tools/set_display_timeout.py COM7          # 15 s
  python tools/set_display_timeout.py COM7 30       # 30 s
  python tools/set_display_timeout.py COM7 0        # never blank

Run it with the project venv. Close rnsd, Sideband and anything else holding the port first.
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_rnodeconf
from install_wio_l1 import tool, DEFAULT_DISPLAY_TIMEOUT


def set_display_timeout(rnodeconf, port, seconds):
    cmd = [rnodeconf, port, "-t", str(seconds)]
    print("> " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", help="serial port of the Wio Tracker L1, e.g. COM7")
    ap.add_argument("seconds", nargs="?", type=int, default=DEFAULT_DISPLAY_TIMEOUT,
                    help=f"seconds before the screen blanks, 0 to disable (default {DEFAULT_DISPLAY_TIMEOUT})")
    args = ap.parse_args()

    if not 0 <= args.seconds <= 255:
        sys.exit("Timeout must be between 0 and 255 seconds (stored as one EEPROM byte)")

    patch_rnodeconf.patch()
    rc = set_display_timeout(tool("rnodeconf"), args.port, args.seconds)
    if rc == 0:
        print("Display blanking disabled." if args.seconds == 0
              else f"Display will blank after {args.seconds} s.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
