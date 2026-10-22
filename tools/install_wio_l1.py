#!/usr/bin/env python
"""Flash and provision RNode firmware on a Seeed Wio Tracker L1.

Steps:
  1. Patch rnodeconf so it knows the Wio L1 product/model (tools/patch_rnodeconf.py)
  2. Create a local EEPROM signing key if there is none (rnodeconf --key)
  3. Flash the DFU package over USB serial (adafruit-nrfutil, 1200 baud touch)
  4. Bootstrap the EEPROM (rnodeconf --rom --product 18 --model 18)
  5. Read the firmware hash the device calculates and store it as the target hash
  6. Set the display blanking timeout (rnodeconf -t, default 15 s)

Usage:
  python tools/install_wio_l1.py COM5
  python tools/install_wio_l1.py COM5 --skip-flash     # provision only
  python tools/install_wio_l1.py COM5 --package path/to/dfu.zip
  python tools/install_wio_l1.py COM5 --display-timeout 0   # never blank the screen

Run it with the project venv, which has rns and adafruit-nrfutil installed.
"""

import argparse
import os
import subprocess
import sys
import time

import serial
from serial.tools import list_ports

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_rnodeconf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PACKAGE = os.path.join(ROOT, "Release", "rnode_firmware_wio_l1.zip")  # make release-wio_l1
SIGNING_KEY = os.path.expanduser("~/.config/rnodeconf/firmware/signing.key")

PRODUCT = "18"
MODEL = "18"
HWREV = "1"
DEFAULT_DISPLAY_TIMEOUT = 15  # seconds; RNode never blanks the screen unless this is set


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
    # rnodeconf returns before the device has reset, so let the old port drop off first
    gone_deadline = time.time() + 10
    while time.time() < gone_deadline:
        if not any(p.serial_number == serial_number for p in list_ports.comports()):
            break
        time.sleep(0.5)
    deadline = time.time() + timeout
    while time.time() < deadline:
        for p in list_ports.comports():
            if p.serial_number == serial_number:
                time.sleep(2)
                return p.device
        time.sleep(1)
    sys.exit(f"Device with USB serial {serial_number} did not reappear within {timeout}s")


def enter_bootloader(port, serial_number, timeout=20):
    """Open the port at 1200 baud to reboot into the bootloader.

    The bootloader enumerates with a different USB PID than the application,
    so Windows usually gives it a different COM port. Returns that port.
    """
    app_pid = next((p.pid for p in list_ports.comports() if p.device.lower() == port.lower()), None)
    try:
        serial.Serial(port, 1200).close()
    except serial.SerialException:
        pass  # port vanishes as the device reboots
    if serial_number is None:
        time.sleep(3)
        return port
    deadline = time.time() + timeout
    while time.time() < deadline:
        for p in list_ports.comports():
            if p.serial_number == serial_number and p.pid != app_pid:
                time.sleep(1.5)
                return p.device
        time.sleep(0.5)
    print("Bootloader port not detected; if the board is already in the bootloader, that's fine")
    return port


def main():
    parser = argparse.ArgumentParser(description="Flash and provision RNode firmware on a Wio Tracker L1")
    parser.add_argument("port", help="serial port of the Wio Tracker L1, e.g. COM5")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="DFU zip to flash")
    parser.add_argument("--skip-flash", action="store_true", help="only provision EEPROM and firmware hash")
    parser.add_argument("--display-timeout", type=int, default=DEFAULT_DISPLAY_TIMEOUT,
                        help=f"seconds before the screen blanks, 0 to disable (default {DEFAULT_DISPLAY_TIMEOUT})")
    args = parser.parse_args()
    if not 0 <= args.display_timeout <= 255:
        sys.exit("--display-timeout must be between 0 and 255 seconds")

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
        bootloader_port = enter_bootloader(port, serial_number)
        run([nrfutil, "--verbose", "dfu", "serial", "-pkg", args.package,
             "-p", bootloader_port, "-b", "115200", "--singlebank"])
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

    # Saved straight to EEPROM; the device does not reset
    run([rnodeconf, port, "-t", str(args.display_timeout)])
    time.sleep(1)

    run([rnodeconf, port, "--info"])
    print("Done.")


if __name__ == "__main__":
    main()
