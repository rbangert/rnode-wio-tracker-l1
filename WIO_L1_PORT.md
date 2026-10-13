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

```
arduino-cli core install adafruit:nrf52 --config-file arduino-cli.yaml
arduino-cli lib install "Adafruit GFX Library" "Adafruit SH110X" "Adafruit SSD1306"
make firmware-wio_l1      # compile
make release-wio_l1       # compile + DFU zip in Release/
```

Arduino requires the sketch folder to be named after `RNode_Firmware.ino`. Because this repo is
checked out as `rnode-wio-tracker-l1`, compile through a junction/symlink named `RNode_Firmware`:

```
New-Item -ItemType Junction -Path $env:TEMP\RNode_Firmware -Target C:\Users\rbang\Projects\rnode-wio-tracker-l1
cd $env:TEMP\RNode_Firmware
arduino-cli compile --fqbn adafruit:nrf52:pca10056 --build-path $env:TEMP\rnode_build --build-property "compiler.cpp.extra_flags=`"-DBOARD_MODEL=0x45`"" .
```

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
- **OLED is SH1106 at 0x3D** per Zephyr. Meshtastic's variant names the SSD1306 driver but
  autodetects at runtime. The address can be overridden with rnodeconf (`DISP_CUSTOM_ADDR`).
- **Wire pins.** The `pca10056` variant defaults I2C to P0.26/P0.27, which are the GNSS UART on
  this board, so `display_init()` calls `Wire.setPins()` before the display driver starts I2C.
- **SoftDevice.** The `pca10056` build links against S140 v6.1.1. Check `INFO_UF2.TXT` on the
  "Tracker L1" drive (double-tap reset) to confirm the factory bootloader's SoftDevice matches,
  before flashing.
- **Battery scale** reuses the T-Echo factor (same 1:2 divider, 3.6 V reference, 10-bit ADC).
  Calibrate against a multimeter.

## Provisioning

`rnodeconf` validates product/model IDs against its own tables. Until the Wio L1 IDs are added
there, the device has to be provisioned with a locally patched `rnodeconf` (add the product,
model, and firmware filename entries alongside the T-Echo ones in `RNS/Utilities/rnodeconf.py`).

## Hardware test checklist

- [ ] Firmware boots, enumerates over USB serial
- [ ] `rnodeconf` (patched) provisions EEPROM and sets firmware hash
- [ ] Radio initialises (`rnodeconf -i` reports radio online)
- [ ] TX/RX against another RNode at 868/915 MHz
- [ ] OLED shows status screen
- [ ] User LED blinks on RX/TX
- [ ] BLE pairing and KISS over BLE (Sideband)
- [ ] Battery percentage plausible, matches multimeter
- [ ] Long-press sleep and button wake
