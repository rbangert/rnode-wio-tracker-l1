#!/usr/bin/env python
"""Read the battery status an RNode reports over KISS and back out the voltage.

RNode only reports battery state and an integer percentage (CMD_STAT_BAT, about
every 5 s). On the Wio L1 the percentage is linear between BAT_V_MIN and
BAT_V_MAX (Power.h), so the voltage the firmware measured can be recovered to
within about 10 mV. Compare it with a multimeter on the battery terminals.

The estimate is only usable when the percentage is between 1 and 99; at 0 or
100 the value is clipped. Charging holds the battery near 4.2 V, which reads as
100 %, so calibrate on battery or with a partly discharged cell.

Usage:
  python tools/battery_check.py COM7
  python tools/battery_check.py COM7 --meter 3.87    # suggest a corrected scale factor

Close rnsd, Sideband and anything else holding the port first.
"""

import argparse
import sys
import time

from rnode_link_test import RNode

CMD_STAT_BAT = 0x27
STATES = {0x00: "unknown", 0x01: "discharging", 0x02: "charging", 0x03: "charged"}

# Must match the BOARD_WIO_L1 section of Power.h
BAT_V_MIN = 3.15
BAT_V_MAX = 4.16
SCALE = 0.007067


def pct_to_v(p):
    return BAT_V_MIN + p / 100.0 * (BAT_V_MAX - BAT_V_MIN)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port")
    ap.add_argument("--meter", type=float, help="battery voltage measured with a multimeter")
    ap.add_argument("--samples", type=int, default=6, help="reports to collect (about 5 s each)")
    args = ap.parse_args()

    node = RNode(args.port, "Wio")
    try:
        version = node.detect()
        if version is None:
            print(f"{args.port}: no RNode answered")
            return 2
        print(f"{args.port}: RNode firmware {version}")
        print(f"Waiting for {args.samples} battery reports (about {args.samples * 5} s)...\n")

        pcts = []
        deadline = time.time() + args.samples * 5 + 15
        while len(pcts) < args.samples and time.time() < deadline:
            p = node.wait_for(CMD_STAT_BAT, deadline - time.time())
            if p is None or len(p) < 2:
                break
            state, pct = p[0], p[1]
            pcts.append(pct)
            lo, hi = pct_to_v(pct), pct_to_v(pct + 1)
            note = "  (clipped, voltage unknown)" if pct in (0, 100) else ""
            print(f"  {STATES.get(state, hex(state)):<12} {pct:3d} %   ~{lo:.3f}-{hi:.3f} V{note}")

        if not pcts:
            print("No battery reports received. Is a battery connected, and is the firmware running?")
            return 1

        usable = [p for p in pcts if 0 < p < 100]
        if not usable:
            print("\nAll readings are clipped at 0 or 100 %, so the voltage cannot be estimated."
                  "\nUnplug USB, or let the battery run down below ~4.1 V, and try again.")
            return 1

        avg_pct = sum(usable) / len(usable) + 0.5  # integer truncation, so take the middle of the step
        est_v = pct_to_v(avg_pct)
        print(f"\nFirmware-measured battery voltage: ~{est_v:.3f} V")

        if args.meter:
            err = (est_v - args.meter) / args.meter * 100
            new_scale = SCALE * args.meter / est_v
            print(f"Multimeter:                        {args.meter:.3f} V  (firmware off by {err:+.1f} %)")
            if abs(err) < 1.0:
                print("Within 1 %, so the current scale factor is fine.")
            else:
                print(f"Suggested scale factor: {new_scale:.6f}  (currently {SCALE})")
        else:
            print("Run again with --meter <volts> to compare against a multimeter reading.")
        return 0
    finally:
        node.close()


if __name__ == "__main__":
    sys.exit(main())
