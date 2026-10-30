#!/usr/bin/env python3
"""Host-side regression checks for nRF52 Bluetooth toggles (requires g++).

Compile the actual lifecycle functions extracted from Bluetooth.h against a
small Bluefruit mock. No Arduino toolchain or Bluetooth hardware is required.
These checks do not replace hardware tests of advertising and bonding.

Usage: python3 tools/test_nrf52_bluetooth_toggle.py
"""

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def extract(source, signature):
    section = source.index('#elif MCU_VARIANT == MCU_NRF52\n    uint32_t pairing_pin')
    start = source.index(signature, section)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


PREAMBLE = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
enum { BT_STATE_OFF, BT_STATE_ON, BT_STATE_CONNECTED, BT_STATE_PAIRING };
int bt_state = BT_STATE_OFF;
bool bt_allow_pairing = false, SerialBT_init = false;
uint32_t pairing_pin = 0, bt_ssp_pin = 0;
char bt_devname[] = "RNode TEST";
#define BLE_MANUFACTURER "Test"
#define BLE_MODEL "Test"
#define SECMODE_ENC_WITH_MITM 3
#define BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE 6
void bt_disconnect_callback(uint16_t, uint8_t);
struct Service {
    int begins = 0;
    void begin() { ++begins; }
    void setManufacturer(const char*) {}
    void setModel(const char*) {}
    void bufferTXD(bool) {}
    void setPermission(int, int) {}
} SerialBT, bledis, blebas;
struct Advertising {
    bool running = false, restart = true, succeed = true;
    int fields = 0, starts = 0;
    void restartOnDisconnect(bool value) { restart = value; }
    bool isRunning() { return running; }
    void stop() { running = false; }
    void clearData() { fields = 0; }
    void addFlags(int) { ++fields; }
    void addTxPower() { ++fields; }
    void addService(Service&) { ++fields; }
    void addName() { ++fields; }
    bool start(int) { ++starts; running = succeed; return succeed; }
};
struct BluefruitMock {
    struct Advertising Advertising, ScanResponse;
    int connections = 0, disconnects = 0;
    void setName(const char*) {}
    bool connected() { return connections > 0; }
    uint16_t connHandle() { return 0; }
    void disconnect(uint16_t handle) {
        ++disconnects;
        connections = 0;
        if (Advertising.restart) Advertising.start(0);
        bt_disconnect_callback(handle, 0x13);
    }
} Bluefruit;
'''

TESTS = r'''
int main() {
    bt_start();
    assert(bt_state == BT_STATE_ON && Bluefruit.Advertising.running);
    assert(Bluefruit.Advertising.restart);
    assert(bledis.begins == 1 && blebas.begins == 1 && SerialBT.begins == 1);
    int starts = Bluefruit.Advertising.starts;
    bt_start();
    assert(Bluefruit.Advertising.starts == starts);
    for (int i = 0; i < 100; ++i) {
        bt_allow_pairing = true;
        pairing_pin = bt_ssp_pin = 123456;
        Bluefruit.connections = 1;
        bt_state = BT_STATE_CONNECTED;
        bt_stop();
        assert(bt_state == BT_STATE_OFF && !Bluefruit.Advertising.running);
        assert(!Bluefruit.Advertising.restart && !Bluefruit.connections);
        assert(!bt_allow_pairing && !pairing_pin && !bt_ssp_pin);
        assert(Bluefruit.disconnects == i + 1);
        bt_disconnect_callback(0, 0);
        bt_disconnect_callback(0, 0x13);
        bt_disable_pairing();
        assert(bt_state == BT_STATE_OFF);
        bt_start();
        assert(bt_state == BT_STATE_ON && Bluefruit.Advertising.running);
        assert(Bluefruit.Advertising.fields == 3 && Bluefruit.ScanResponse.fields == 1);
        assert(bledis.begins == 1 && blebas.begins == 1 && SerialBT.begins == 1);
    }
    bt_state = BT_STATE_CONNECTED;
    bt_disconnect_callback(0, 0x13);
    assert(bt_state == BT_STATE_ON);
    bt_stop();
    Bluefruit.Advertising.succeed = false;
    bt_start();
    assert(bt_state == BT_STATE_OFF && !Bluefruit.Advertising.restart);
    Bluefruit.Advertising.succeed = true;
    bt_start();
    assert(bt_state == BT_STATE_ON && Bluefruit.Advertising.running);
    puts("PASS: 100 toggle cycles, service registration, payload reset, disconnect callbacks, and start failure");
}
'''


def main():
    source = (ROOT / 'Bluetooth.h').read_text()
    functions = '\n'.join(extract(source, signature) for signature in [
        'void bt_stop()', 'void bt_disable_pairing()',
        'void bt_disconnect_callback(uint16_t conn_handle, uint8_t reason)',
        'void bt_start()',
    ])
    with tempfile.TemporaryDirectory(prefix='rnode-bt-toggle-') as temp:
        cpp = Path(temp) / 'test.cpp'
        binary = Path(temp) / 'test'
        cpp.write_text(PREAMBLE + functions + TESTS)
        subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', str(cpp), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    main()
