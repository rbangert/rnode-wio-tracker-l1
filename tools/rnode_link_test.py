#!/usr/bin/env python
"""Raw LoRa TX/RX test between two RNodes over KISS.

Opens both RNodes over USB serial, sets the same radio parameters on each,
then sends numbered packets from A to B and from B to A. Every received
packet is matched against what was sent and reported with RSSI and SNR.
This tests the radio layer only; Reticulum is not involved.

Usage:
  python tools/rnode_link_test.py COM8 COM5
  python tools/rnode_link_test.py COM8 COM5 --freq 915000000 --bw 125000 --sf 8 --cr 5 --txp 2 --count 10

Run it with the project venv (pyserial). Close rnsd, Sideband and anything
else holding the ports first.
"""

import argparse
import queue
import struct
import sys
import threading
import time

import serial

FEND, FESC, TFEND, TFESC = 0xC0, 0xDB, 0xDC, 0xDD

CMD_DATA        = 0x00
CMD_FREQUENCY   = 0x01
CMD_BANDWIDTH   = 0x02
CMD_TXPOWER     = 0x03
CMD_SF          = 0x04
CMD_CR          = 0x05
CMD_RADIO_STATE = 0x06
CMD_DETECT      = 0x08
CMD_STAT_RSSI   = 0x23
CMD_STAT_SNR    = 0x24
CMD_BOARD       = 0x47
CMD_FW_VERSION  = 0x50
CMD_ERROR       = 0x90

DETECT_REQ  = 0x73
DETECT_RESP = 0x46
RSSI_OFFSET = 157

ERRORS = {0x01: "INITRADIO", 0x02: "TXFAILED", 0x03: "EEPROM_LOCKED",
          0x04: "QUEUE_FULL", 0x05: "MEMORY_LOW", 0x06: "MODEM_TIMEOUT"}


def escape(data):
    return data.replace(bytes([FESC]), bytes([FESC, TFESC])).replace(bytes([FEND]), bytes([FESC, TFEND]))


class RNode:
    def __init__(self, port, name):
        self.name = name
        self.port = port
        self.ser = serial.Serial(port, 115200, timeout=0.1)
        self.frames = queue.Queue()
        self.rssi = None
        self.snr = None
        self.running = True
        threading.Thread(target=self._read_loop, daemon=True).start()

    def close(self):
        self.running = False
        try:
            self.send(CMD_RADIO_STATE, bytes([0x00]))
            time.sleep(0.2)
        finally:
            self.ser.close()

    def send(self, cmd, payload=b""):
        self.ser.write(bytes([FEND, cmd]) + escape(payload) + bytes([FEND]))

    def _read_loop(self):
        in_frame, escaped, cmd, buf = False, False, None, bytearray()
        while self.running:
            try:
                data = self.ser.read(256)
            except Exception:
                return
            for b in data:
                if b == FEND:
                    if in_frame and cmd is not None:
                        self._handle(cmd, bytes(buf))
                    in_frame, escaped, cmd, buf = True, False, None, bytearray()
                elif not in_frame:
                    continue
                elif cmd is None:
                    cmd = b
                elif b == FESC:
                    escaped = True
                else:
                    if escaped:
                        b = FEND if b == TFEND else FESC if b == TFESC else b
                        escaped = False
                    buf.append(b)

    def _handle(self, cmd, payload):
        if cmd == CMD_STAT_RSSI and payload:
            self.rssi = payload[0] - RSSI_OFFSET
        elif cmd == CMD_STAT_SNR and payload:
            self.snr = struct.unpack("b", payload[:1])[0] * 0.25
        elif cmd == CMD_ERROR and payload:
            print(f"  [{self.name}] ERROR {ERRORS.get(payload[0], hex(payload[0]))}")
        self.frames.put((cmd, payload))

    def wait_for(self, cmd, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                c, p = self.frames.get(timeout=max(0.01, deadline - time.time()))
            except queue.Empty:
                break
            if c == cmd:
                return p
        return None

    def drain(self):
        while not self.frames.empty():
            self.frames.get_nowait()

    def detect(self):
        self.ser.reset_input_buffer()
        self.send(CMD_DETECT, bytes([DETECT_REQ]))
        self.send(CMD_FW_VERSION, bytes([0x00]))
        self.send(CMD_BOARD, bytes([0x00]))
        resp = self.wait_for(CMD_DETECT, 3)
        if resp != bytes([DETECT_RESP]):
            return None
        version = self.wait_for(CMD_FW_VERSION, 1)
        return f"{version[0]}.{version[1]:02d}" if version and len(version) >= 2 else "?"

    def configure(self, freq, bw, sf, cr, txp):
        steps = [
            (CMD_FREQUENCY, struct.pack(">I", freq)),
            (CMD_BANDWIDTH, struct.pack(">I", bw)),
            (CMD_TXPOWER, bytes([txp])),
            (CMD_SF, bytes([sf])),
            (CMD_CR, bytes([cr])),
            (CMD_RADIO_STATE, bytes([0x01])),
        ]
        ok = True
        for cmd, payload in steps:
            time.sleep(0.1)
            self.drain()
            self.send(cmd, payload)
            reply = self.wait_for(cmd, 2)
            if reply != payload and not (cmd == CMD_TXPOWER and reply is not None):
                print(f"  [{self.name}] cmd 0x{cmd:02x}: sent {payload.hex()}, got {reply.hex() if reply else 'nothing'}")
                ok = False
                if cmd == CMD_RADIO_STATE:
                    print(f"  [{self.name}] radio did not start; check the firmware hash "
                          f"(rnodeconf -i) and that the EEPROM is provisioned")
            elif cmd == CMD_TXPOWER and reply != payload:
                print(f"  [{self.name}] TX power clamped to {reply[0]} dBm")
        return ok


def airtime_s(length, sf, bw, cr):
    # Semtech LoRa time-on-air, explicit header, CRC on, 8 symbol preamble
    t_sym = (2 ** sf) / bw
    de = 1 if t_sym > 0.016 else 0
    n = 8 + max(0, -(-(8 * length - 4 * sf + 28 + 16) // (4 * (sf - 2 * de)))) * cr
    return (8 + 4.25) * t_sym + n * t_sym


def run_direction(tx, rx, count, args):
    print(f"\n{tx.name} -> {rx.name}")
    received, rssis, snrs = 0, [], []
    for i in range(count):
        payload = f"rnode-link-test {tx.name}->{rx.name} #{i:03d}".encode()
        rx.drain()
        tx.send(CMD_DATA, payload)
        got = None
        deadline = time.time() + airtime_s(len(payload), args.sf, args.bw, args.cr) + 1.5
        while time.time() < deadline:
            p = rx.wait_for(CMD_DATA, deadline - time.time())
            if p is None:
                break
            if p == payload:
                got = p
                break
            print(f"  #{i:03d} unexpected frame: {p!r}")
        if got:
            received += 1
            rssis.append(rx.rssi)
            snrs.append(rx.snr)
            print(f"  #{i:03d} ok   RSSI {rx.rssi} dBm  SNR {rx.snr:+.2f} dB")
        else:
            print(f"  #{i:03d} LOST")
        time.sleep(args.gap)
    summary = f"  {received}/{count} received"
    if rssis:
        summary += f", RSSI avg {sum(rssis) / len(rssis):.1f} dBm, SNR avg {sum(snrs) / len(snrs):+.2f} dB"
    print(summary)
    return received


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port_a")
    ap.add_argument("port_b")
    ap.add_argument("--name-a", default="A")
    ap.add_argument("--name-b", default="B")
    ap.add_argument("--freq", type=int, default=915000000)
    ap.add_argument("--bw", type=int, default=125000)
    ap.add_argument("--sf", type=int, default=8)
    ap.add_argument("--cr", type=int, default=5)
    ap.add_argument("--txp", type=int, default=2, help="TX power in dBm (keep low on a bench)")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--gap", type=float, default=0.3, help="seconds between packets")
    args = ap.parse_args()

    a = RNode(args.port_a, args.name_a)
    b = RNode(args.port_b, args.name_b)
    try:
        for node in (a, b):
            version = node.detect()
            if version is None:
                print(f"{node.name} ({node.port}): no RNode answered")
                return 2
            print(f"{node.name} ({node.port}): RNode firmware {version}")

        print(f"\nRadio: {args.freq / 1e6:.3f} MHz, {args.bw / 1e3:g} kHz, SF{args.sf}, CR4/{args.cr}, {args.txp} dBm")
        for node in (a, b):
            if not node.configure(args.freq, args.bw, args.sf, args.cr, args.txp):
                print(f"{node.name}: radio configuration failed")
                return 3
        time.sleep(0.5)

        ab = run_direction(a, b, args.count, args)
        ba = run_direction(b, a, args.count, args)
        print(f"\nResult: {a.name}->{b.name} {ab}/{args.count}, {b.name}->{a.name} {ba}/{args.count}")
        return 0 if ab == args.count and ba == args.count else 1
    finally:
        a.close()
        b.close()


if __name__ == "__main__":
    sys.exit(main())
