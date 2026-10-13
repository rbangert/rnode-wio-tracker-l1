#!/usr/bin/env python
"""Flash and provision RNode firmware on a Seeed Wio Tracker L1.

Steps:
  1. Patch rnodeconf so it knows the Wio L1 product/model (tools/patch_rnodeconf.py)
  2. Create a local EEPROM signing key if there is none (rnodeconf --key)
  3. Flash the DFU package over USB serial (adafruit-nrfutil, 1200 baud touch)
  4. Bootstrap the EEPROM (rnodeconf --rom --product 18 --model 18)
  5. Read the firmware hash the device calculates and store it as the target hash

Usage:
  python tools/install_wio_l1.py COM5
  python tools/install_wio_l1.py COM5 --skip-flash     # provision only
  python tools/install_wio_l1.py COM5 --package path/to/dfu.zip

Run it with the project venv, which has rns and adafruit-nrfutil installed.
"""

import argparse
import os
import subprocess
import sys
import time

from serial.tools import list_ports

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_rnodeconf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PACKAGE = os.path.join(ROOT, "build", "wio_l1", "rnode_firmware_wio_l1_dfu.zip")
SIGNING_KEY = os.path.expanduser("~/.config/rnodeconf/firmware/signing.key")

PRODUCT = "18"
MODEL = "18"
HWREV = "1"


def tool(name):
    """Prefer the entry point next to the running interpreter (the venv)."""
    exe_dir = os.path.dirname(sys.executable)
    for candidate in (name + ".exe", name):
        path = os.path.join(exe_dir, candidate)
        if os.path.isfile(path):
            return path
    return name


def run(cmd, capture=False):
    print("> " + " ".join(cmd))
    if capture:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(result.stdout)
    else:
        result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"Command failed with exit code {result.returncode}")
    return result.stdout if capture else None


def usb_serial_number(port):
    for p in list_ports.comports():
        if p.device.lower() == port.lower():
            return p.serial_number
    return None


def wait_for_port(serial_number, fallback, timeout=40):
    """The COM port can change across resets, so find the device by USB serial number."""
    if serial_number is None:
        time.sleep(8)
        return fallback
    deadline = time.time() + timeout
    while time.time() < deadline:
        for p in list_ports.comports():
            if p.serial_number == serial_number:
                time.sleep(2)
                return p.device
        time.sleep(1)
    sys.exit(f"Device with USB serial {serial_number} did not reappear within {timeout}s")


def main():
    parser = argparse.ArgumentParser(description="Flash and provision RNode firmware on a Wio Tracker L1")
    parser.add_argument("port", help="serial port of the Wio Tracker L1, e.g. COM5")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="DFU zip to flash")
    parser.add_argument("--skip-flash", action="store_true", help="only provision EEPROM and firmware hash")
    args = parser.parse_args()

    rnodeconf = tool("rnodeconf")
    nrfutil = tool("adafruit-nrfutil")

    patch_rnodeconf.patch()

    if not os.path.isfile(SIGNING_KEY):
        run([rnodeconf, "--key"])

    port = args.port
    serial_number = usb_serial_number(port)
    if serial_number is None:
        print(f"Warning: {port} not found in the port list, cannot track it across resets")

    if not args.skip_flash:
        if not os.path.isfile(args.package):
            sys.exit(f"DFU package not found: {args.package}")
        run([nrfutil, "--verbose", "dfu", "serial", "-pkg", args.package,
             "-p", port, "-b", "115200", "--singlebank", "--touch", "1200"])
        print("Waiting for the firmware to boot...")
        time.sleep(5)
        port = wait_for_port(serial_number, port)

    run([rnodeconf, port, "--rom", "--product", PRODUCT, "--model", MODEL, "--hwrev", HWREV])
    port = wait_for_port(serial_number, port)

    output = run([rnodeconf, port, "-L"], capture=True)
    marker = "The actual firmware hash is: "
    if marker not in output:
        sys.exit("Could not read the calculated firmware hash from the device")
    firmware_hash = output.split(marker)[1].split()[0]

    run([rnodeconf, port, "--firmware-hash", firmware_hash])
    port = wait_for_port(serial_number, port)

    run([rnodeconf, port, "--info"])
    print("Done.")


if __name__ == "__main__":
    main()
