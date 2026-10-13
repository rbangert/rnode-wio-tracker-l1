# Seeed Wio Tracker L1 / L1 Pro port

Work-in-progress port of upstream [markqvist/RNode_Firmware](https://github.com/markqvist/RNode_Firmware)
to the Seeed Studio Wio Tracker L1 (nRF52840 + Wio-SX1262, 862-930 MHz). The L1 Pro is the same
board in an enclosure with a battery.

Board ID `BOARD_WIO_L1` (`0x45`), product `PRODUCT_WIO_L1` (`0x18`), model `MODEL_18` (`0x18`).
These IDs are **provisional** and not assigned upstream, so stock `rnodeconf` will not recognise
the device until they are (see "Provisioning" below).

## Build

Uses the Adafruit nRF52 core with the `pca10056` variant (same as the T-Echo target), where
Arduino pin numbers equal nRF GPIO numbers (`port * 32 + pin`).

The L1 ships with SoftDevice **S140 7.3.0** (factory bootloader: UF2 Bootloader 0.9.2,
Board-ID "TRACKER L1"), but `pca10056` assumes S140 6.1.1. The Wio L1 targets therefore override:

- `build.sd_version=7.3.0`: compile against the 7.3.0 SoftDevice API headers (bundled in the core)
- `build.ldscript=linker/nrf52840_s140_v7.ld`: application at `0x27000` instead of `0x26000`
- `build.sd_fwid=0x0123`: DFU package requires S140 7.3.0

`Device.h` uses the same `0x27000` application start for the firmware hash. A 6.1.1 build
flashed onto this bootloader will not boot.

```
arduino-cli core install adafruit:nrf52 --config-file arduino-cli.yaml
arduino-cli lib install "Adafruit GFX Library" "Adafruit SH110X" "Adafruit SSD1306"
make firmware-wio_l1      # compile
make release-wio_l1       # compile + DFU zip in Release/
```

Arduino requires the sketch folder to be named after `RNode_Firmware.ino`. Because this repo is
checked out as `rnode-wio-tracker-l1`, compile through a junction/symlink named `RNode_Firmware`:

```
New-Item -ItemType Junction -Path $env:TEMP\RNode_Firmware -Target <path to this repo>
cd $env:TEMP\RNode_Firmware
arduino-cli compile --fqbn adafruit:nrf52:pca10056 --build-path $env:TEMP\rnode_build `
  --build-property "build.sd_version=7.3.0" --build-property "build.sd_fwid=0x0123" `
  --build-property "build.ldscript=<path to this repo>/linker/nrf52840_s140_v7.ld" `
  --build-property "compiler.cpp.extra_flags=`"-DBOARD_MODEL=0x45`"" .
```

## Flashing

- **DFU (preferred):** `adafruit-nrfutil dfu serial -pkg rnode_firmware_wio_l1_dfu.zip -p COMx -b 115200 --singlebank`.
  This is the path rnodeconf uses, and it records the image size in the bootloader settings
  page, which RNode reads (`0xFF008`) to compute its firmware hash.
- **UF2:** double-tap reset, copy `rnode_firmware_wio_l1.uf2` onto the "TRACKER L1" drive.
  Convenient, but whether this bootloader records the image size on UF2 writes is unverified;
  if the firmware hash looks wrong after provisioning, reflash via DFU.

Libraries (from the Makefile's prep targets): Crypto, Adafruit GFX, Adafruit SH110X,
Adafruit SSD1306, Adafruit NeoPixel, XPowersLib, GxEPD2.

First successful build (adafruit:nrf52 1.7.0): 247,600 bytes flash (30%), 39,108 bytes RAM (16%).

## Pin map

Sources: Zephyr `wio_tracker_l1.dts`, Meshtastic `variants/nrf52840/seeed_wio_tracker_L1`.

| Function            | GPIO  | Arduino pin |
|---------------------|-------|-------------|
| SX1262 NSS          | P1.14 | 46 |
| SX1262 SCK          | P0.30 | 30 |
| SX1262 MOSI         | P0.28 | 28 |
| SX1262 MISO         | P0.03 | 3  |
| SX1262 RESET        | P1.07 | 39 |
| SX1262 BUSY         | P1.10 | 42 |
| SX1262 DIO1         | P0.07 | 7  |
| RX enable (LNA)     | P1.08 | 40 |
| TCXO                | DIO3, 1.8 V | - |
| TX RF switch        | DIO2  | - |
| User LED            | P1.01 | 33 |
| User button         | P0.08 | 8  |
| OLED SDA / SCL      | P0.06 / P0.05 | 6 / 5 |
| VBAT ADC (AIN7)     | P0.31 | 31 (1M/1M divider) |
| VBAT divider enable | P0.04 | 4  |
| GNSS UART TX / RX   | P0.27 / P0.26 | not used by RNode |
| Buzzer              | P1.00 | not used |
| Trackball           | P1.04 P0.12 P0.11 P1.03 P1.05 | not used |

## Decisions and open questions

- **TCXO voltage 1.8 V.** Zephyr and Meshtastic both use 1.8 V for the L1. RNode's XIAO ESP32S3
  target uses 3.3 V for the same Wio-SX1262 module; if the radio fails to init, try 3.3 V in
  `sx126x.cpp` `enableTCXO()`.
- **OLED is SH1106 at 0x3D** per Zephyr; confirmed working on hardware. The address can be
  overridden with rnodeconf (`DISP_CUSTOM_ADDR`) if a unit uses 0x3C.
- **Wire pins.** The `pca10056` variant defaults I2C to P0.26/P0.27, which are the GNSS UART on
  this board, so `display_init()` calls `Wire.setPins()` before the display driver starts I2C.
- **SoftDevice.** Confirmed S140 7.3.0 from `INFO_UF2.TXT`; handled as described under Build.
- **Battery scale** reuses the T-Echo factor (same 1:2 divider, 3.6 V reference, 10-bit ADC).
  Calibrate against a multimeter.

## Provisioning

`rnodeconf` looks up product/model IDs in its own tables, and the Wio L1 IDs are not there
upstream. `tools/patch_rnodeconf.py` adds them to the installed `rnodeconf` (idempotent; re-run
after upgrading `rns`). `tools/install_wio_l1.py` does the whole install:

```
python -m venv .venv
.venv\Scripts\pip install rns adafruit-nrfutil
.venv\Scripts\python tools\install_wio_l1.py COM5
```

1. patches `rnodeconf`
2. creates `~/.config/rnodeconf/firmware/signing.key` if missing (`rnodeconf --key`, never overwrites)
3. reboots into the bootloader with a 1200 baud touch, finds the bootloader's port (it enumerates
   as a different COM port, USB PID `0x1667` vs `0x80DA`) and flashes
   `build/wio_l1/rnode_firmware_wio_l1_dfu.zip` with `adafruit-nrfutil`
4. bootstraps the EEPROM: `rnodeconf PORT --rom --product 18 --model 18 --hwrev 1`
5. reads the device-calculated firmware hash (`-L`) and stores it (`--firmware-hash`)
6. prints `rnodeconf --info`

The COM port can change across resets; the script follows the device by USB serial number.
Use `--skip-flash` to re-provision without reflashing. Re-running the full install on a
provisioned board reflashes and updates the firmware hash; the EEPROM bootstrap step is skipped
because a valid EEPROM is already present.

**Do not install with UF2.** Copying the `.uf2` to the TRACKER L1 drive does not record the image
size in the bootloader settings page, so RNode hashes zero bytes (`e3b0c442...`, SHA-256 of empty
input) and the hash no longer matches. Confirmed on hardware; reflash over DFU to recover.

## Bluetooth / Sideband

1. `rnodeconf PORT -b` enables Bluetooth (persisted in EEPROM).
2. `rnodeconf PORT -p` enters pairing mode. The firmware only allows pairing for
   **35 seconds** (`BT_PAIRING_TIMEOUT`), no matter how long rnodeconf waits. The 6-digit PIN is
   shown on the OLED and also printed by rnodeconf.
3. Pair from the phone's Bluetooth settings with the device named `RNode XXXX`. The firmware
   disconnects right after pairing by design; the app reconnects.
4. In Sideband: Connectivity → connect via RNode; Hardware → RNode → Bluetooth on, frequency
   (MHz), bandwidth (kHz), SF, CR, TX power. Restart Sideband.

Gotchas seen on hardware:

- The BLE address does not change when the firmware is replaced, so a phone that knew the factory
  firmware keeps showing the cached name `Meshtastic_xxxx`. Sideband looks for bonded devices named
  `RNode ...`, so it will not connect until the phone has the new name. Forget the device, toggle
  Bluetooth, and re-pair. Uninstall or disconnect the Meshtastic app so it does not grab the board.
- Upstream `bt_debond_all()` was a no-op on nRF52, so `CMD_BT_UNPAIR` (`0x70 0x01`) did nothing and
  stale bonds could not be cleared. Fixed in this branch with `Bluefruit.Periph.clearBonds()`.

## Hardware test checklist

- [x] Firmware boots, enumerates over USB serial
- [x] `rnodeconf` (patched) provisions EEPROM and sets firmware hash
- [x] Radio initialises (RADIO_STATE online at 915 MHz, no INITRADIO error)
- [ ] TX/RX against another RNode at 868/915 MHz
- [x] OLED shows status screen (SH1106 at 0x3D)
- [ ] User LED blinks on RX/TX
- [x] BLE pairing and KISS over BLE (Sideband on Android, 915 MHz / 125 kHz / SF8 / CR5)
- [ ] Battery percentage plausible, matches multimeter
- [ ] Long-press sleep and button wake
