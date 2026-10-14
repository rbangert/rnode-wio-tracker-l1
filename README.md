# RNode Firmware: Seeed Wio Tracker L1 port (unofficial)

<p align="center">
  <img src="Documentation/images/wio_l1_rnode.jpg" alt="Wio Tracker L1 running RNode firmware, showing the status screen on its OLED" width="360">
</p>

This is an **unofficial fork** of [markqvist/RNode_Firmware](https://github.com/markqvist/RNode_Firmware)
that adds support for the **Seeed Studio Wio Tracker L1 / L1 Pro** (nRF52840 + Wio-SX1262,
862-930 MHz). 

## What changed

- `BOARD_WIO_L1` board definition (`Boards.h`, `Display.h`, `Power.h`, `Utilities.h`, `sx126x.cpp`,
  `RNode_Firmware.ino`): SX1262 with 1.8 V TCXO, DIO2 RF switch and RX enable on P1.08, SH1106
  OLED, single LED, battery ADC.
- Build for the board's factory bootloader, which uses SoftDevice S140 **7.3.0** (application at
  `0x27000`): `linker/nrf52840_s140_v7.ld`, `Device.h`, `Makefile` targets `firmware-wio_l1` and
  `release-wio_l1`.
- **nRF52 Bluetooth fix (all nRF52 boards):** `bt_debond_all()` was empty upstream, so the
  unpair command could not clear stored BLE bonds. It now calls `Bluefruit.Periph.clearBonds()`.
- `tools/patch_rnodeconf.py` and `tools/install_wio_l1.py` to flash and provision the board.

Product/model IDs (`0x18`/`0x18`, board `0x45`) are **provisional** and not assigned upstream, so
stock `rnodeconf` does not recognize the board; the patch script adds them locally.

## Status

Tested on one Wio Tracker L1 Pro: boots, provisions with `rnodeconf`, radio initialises at 915 MHz,
OLED status screen works, BLE pairing and Sideband (Android) work over Bluetooth. **Not yet
tested:** over-the-air TX/RX against another node, LED activity, battery calibration, sleep/wake.

Full build, flashing, Bluetooth and troubleshooting notes: [WIO_L1_PORT.md](WIO_L1_PORT.md).

Use at your own risk. Flashing replaces the factory firmware; the bootloader is untouched, so
you can always double-tap reset and restore Meshtastic or MeshCore.

---

## The original upstream README follows.

> [!WARNING]
> RNode is a free, community-developed project, and everything you need to use and build upon it is openly and freely available. Support honest, hard-working builders and maintainers, not [LLM-powered grifters](https://www.youtube.com/watch?v=_znz-3f_66Q) trying to scam you for thousands of dollars.
>
> If you want to buy an RNode device rather than build it yourself, do so from honest, accountable makers, **not** sensationalist YouTubers making outrageously false claims and selling devices for $1100, while stealing the work of the community.
>
> Several hastily launched, incorrect, and in most cases entirely LLM-generated fakes of RNode-based devices, associated tools, "guides" and "documentation" are currently being circulated, marketed and sold for outrageous prices, or being used to advertise crypto-currency tokens.
>
> Most of these hoaxes violate the open source GPLv3 and Creative Commons licenses that RNode and associated documentation and resources were published under, while at the same time claiming independent ownership and license grants.
>
> Such claims or grants are **not legally valid**, and **not** recognized by the RNode authors and copyright holders.
>
> Any claimed assertion of copyright or grant of license that such projects are making are [void grants](https://reticulum.network/manual/brandolinis.html#void-grants-legal-foundations-of-machine-generated-code).
>
> Both the violators themselves, and **all** downstream projects using the infringing derivatives, are **directly** and **personally** liable for the legal consequences.
>
> For trustworthy community resources, see the [main Reticulum repository](https://github.com/markqvist/Reticulum#community-resources). For more detailed information, see the relevant sections of the [Brandolini's Reference](https://reticulum.network/manual/brandolinis.html) chapter of the Reticulum Manual. For software and projects recognized by the Reticulum community, see the [Programs Using Reticulum](https://reticulum.network/manual/software.html) chapter.
>
> Do **not** use these "projects", they are a hazard to the entire ecosystem we have been carefully building over the last ten years.

---

*This repository is [a public mirror](./MIRROR.md). All development is happening elsewhere.*

# RNode Firmware

This is the open firmware that powers RNode devices.

For a great overview of how to get started, and what you can do with an RNode, see the community-provided [RNode Manual by RNS Moscow](https://docs.rns.moscow/rnode-manual/).

An RNode is an open, free and unrestricted digital radio transceiver. It enables anyone to send and receive any kind of data over both short and very long distances. RNodes can be used with many different kinds of programs and systems, but they are especially well suited for use with [Reticulum](https://reticulum.network).

RNode is not a product, and not any *one* specific device in particular. It is a system that is easy to replicate across space and time, that produces highly functional communications tools, which respects user autonomy and empowers individuals and communities to protect their sovereignty, privacy and ability to communicate and exchange data and ideas freely.

<img src="Documentation/images/rnv21_bgp.webp" width="100%">

<center><i>An RNode made from readily available and cheap parts, in a durable 3D printed case</i></center><br/><br/>

The RNode system is primarily software, which *transforms* different kinds of available hardware devices into functional, physical RNodes, which can then be used to solve a wide range of communications tasks. Such RNodes can be modified and built to suit the specific time, locale and environment they need to exist in.

## Latest Release

The latest release, installable through `rnodeconf`, is version `1.86`. You must have at least version `2.4.1` of `rnodeconf` installed to update the RNode Firmware to version `1.86`. Get it by updating the `rns` package to at least version `1.1.9`.

## A Self-Replicating System

If you notice the presence of a circularity in the naming of the system as a whole, and the physical devices, it is no coincidence. Every RNode contains the seeds necessary to reproduce the system, the [RNode Bootstrap Console](https://unsigned.io/rnode_bootstrap_console), which is hosted locally on every RNode, and can be activated and accesses at any time - no Internet required.

The designs, guides and software stored within allows users to create more RNodes, and even to bootstrap entire communications networks, completely independently of existing infrastructure, or in situations where infrastructure has become unreliable or is broken.

<img src="Documentation/images/126dcfe92fb7.webp" width="100%"/>

<center><i>Where there is no Internet, RNodes will still communicate</i></center><br/><br/>

The production of one particular RNode device is not an end, but the potential starting point of a new branch of devices on the tree of the RNode system as a whole.

This tree fits into the larger biome of Free & Open Communications Systems, which I hope that you - by using communications tools like RNode - will help grow and prosper.

## One Tool, Many Uses

The RNode design is meant to flexible and hackable. At it's core, it is a low-power, but extremely long-range digital radio transceiver. Coupled with Reticulum, it provides encrypted and secure communications.

Depending on configuration, it can be used for local networking purposes, or to send data over very long distances. Once you have an RNode, there is a wide variety of possible uses:

- As a network adapter for [Reticulum](https://reticulum.network)
- Messaging using [Sideband](https://unsigned.io/software/Sideband.html)
- Information sharing and communication using [Nomad Network](https://unsigned.io/software/Nomad_Network.html)
- LoRa-based [KISS-compatible amateur radio TNC](https://unsigned.io/guides/2020_05_03_using_rnodes_with_amateur_radio_software.html)
- LoRa development platform
- [Packet sniffer](https://unsigned.io/software/LoRaMon.html) for LoRa networks
- Long range [Ethernet and IP network interface](https://unsigned.io/guides/2020_05_27_ethernet-and-ip-over-packet-radio-tncs.html) on Linux
- As a general-purpose long-range data radio

## Types & Performance

RNodes can be made in many different configurations, and can use many different radio bands, but they will generally operate in the **433 MHz**, **868 MHz**, **915 MHZ** and **2.4 GHz** bands. They will usually offer configurable on-air data speeds between just a **few hundred bits per second**, up to **a couple of megabits per second**. Maximum output power will depend on the transceiver and PA setup used, but will generally lie between **17 dbm** and **27 dBm**.

The RNode system has been designed to allow reliable systems for basic human communications, over very wide areas, while using very little power, being cheap to build, free to operate, and near impossible to censor.

While **speeds are lower** than WiFi, typical communication **ranges are many times higher**. Several kilometers can be acheived with usable bitrates, even in urban areas, and over **100 kilometers** can be achieved in line-of-sight conditions.

## Supported Boards & Devices
It's easy to create your own RNodes from one of the supported development boards and devices. If a device or board you want to use is not yet supported, you are welcome to join the effort and help creating a board definition and pin mapping for it!

<img src="Documentation/images/devboards_1.webp" width="100%"/>

The RNode Firmware supports the following boards:

- LilyGO T-Beam v1.1 devices with SX1276/8 LoRa chips
- LilyGO T-Beam v1.1 devices with SX1262/8 LoRa chips
- LilyGO T-Beam Supreme devices
- LilyGO T-Deck devices (currently display is disabled)
- LilyGO LoRa32 v1.0 devices
- LilyGO LoRa32 v2.0 devices
- LilyGO LoRa32 v2.1 devices (with and without TCXO)
- LilyGO T3S3 devices with SX1276/8 LoRa chips
- LilyGO T3S3 devices with SX1262/8 LoRa chips
- LilyGO T3S3 devices with SX1280 LoRa chips
- LilyGO T-Echo devices
- Heltec LoRa32 v2 devices
- Heltec LoRa32 v3 devices
- Heltec LoRa32 v4 devices
- Heltec T114 devices
- RAK4631 devices
- SeeedStudio XIAO ESP32S3 devices (with Wio-SX1262)
- Homebrew RNodes based on ATmega1284p boards
- Homebrew RNodes based on ATmega2560 boards
- Homebrew RNodes based on Adafruit Feather ESP32 boards
- Homebrew RNodes based on generic ESP32 boards

## Supported Transceiver Modules
The RNode Firmware supports all transceiver modules based on Semtech **SX1276**, **SX1278**, **SX1262**, **SX1268** and **SX1280** chips, that have an **SPI interface** and expose the relevant **DIO** interrupt pins from the chip.

## Getting Started Fast
You can download and flash the firmware to all the supported boards using the [RNode Config Utility](https://github.com/markqvist/rnodeconfigutil). All firmware releases are now handled and installed directly through the `rnodeconf` utility, which is included in the `rns` package. It can be installed via `pip`:

```
# Install rnodeconf via rns package
pip install rns --upgrade

# Install the firmware on a board with the install guide
rnodeconf --autoinstall
```

For most of the supported device types, it is also possible to use [Liam Cottle's Web-based RNode Flasher](https://liamcottle.github.io/rnode-flasher/). This option may be easier if you're not familiar with using a command line interface.

For more detailed instruction and in-depth guides, you can have a look at some of these resources:

- Create a [basic RNode from readily available development boards](https://unsigned.io/guides/2022_01_25_installing-rnode-firmware-on-supported-devices.html)
- Follow a complete build recipe for [making a handheld RNode](https://unsigned.io/guides/2023_01_14_Making_A_Handheld_RNode.html), like the one pictured above
- Learn the basics on how to [create and build your own RNode designs](https://unsigned.io/guides/2022_01_26_how-to-make-your-own-rnodes.html) from scratch
- Once you've got the hang of it, start building RNodes for your community, or [even for selling them](https://unsigned.io/sell_rnodes.html)

If you would rather just buy a pre-made unit, you can visit one of the community vendors that produce and sell RNodes:

- [Liberated Embedded Systems](https://store.liberatedsystems.co.uk/)
- [Simply Equipped](https://simplyequipped.com/)

If you'd like to have your shop added to this list, let me know.

## Support RNode Development
You can help support the continued development of open, free and private communications systems by donating via one of the following channels:

- Monero:
  ```
  84FpY1QbxHcgdseePYNmhTHcrgMX4nFfBYtz2GKYToqHVVhJp8Eaw1Z1EedRnKD19b3B8NiLCGVxzKV17UMmmeEsCrPyA5w
  ```
- Bitcoin
  ```
  bc1pgqgu8h8xvj4jtafslq396v7ju7hkgymyrzyqft4llfslz5vp99psqfk3a6
  ```
- Ethereum
  ```
  0x91C421DdfB8a30a49A71d63447ddb54cEBe3465E
  ```
- Liberapay: https://liberapay.com/Reticulum/

- Ko-Fi: https://ko-fi.com/markqvist


## License & Use
The RNode Firmware is Copyright © 2024 Mark Qvist / [unsigned.io](https://unsigned.io), and is made available under the **GNU General Public License v3.0**. The source code includes an SX1276 driver that is released under MIT License, and Copyright © 2018 Sandeep Mistry / Mark Qvist.

You can obtain the source code from [git.unsigned.io](https://git.unsigned.io/markqvist/RNode_Firmware) or [GitHub](https://github.com/markqvist/rnode_firmware).

Every RNode also includes an internal copy of it's own firmware source code, that can be downloaded through the [RNode Bootstrap Console](https://unsigned.io/rnode_bootstrap_console), by putting the RNode into Console Mode (which can be activated by pressing the reset button two times within two seconds).

The RNode Ecosystem is free and non-proprietary, and actively seeks to distribute it's ownership and control. If you want to build RNodes for commercial purposes, including selling them, you must do so adhering to the Open Source licenses that the various parts of the RNode project is released under, and under your own responsibility.

If you distribute or modify this work, you **must** adhere to the terms of the GPLv3, including, but not limited to, providing up-to-date source code upon distribution, displaying appropriate copyright and license notices in prominent positions of all conveyed works, and making users aware of their rights to the software under the GPLv3.

In practice, this means that you can use the firmware commercially, but you must understand your obligation to provide all future users of the system with the same rights, that you have been provided by the GPLv3. If you intend using the RNode Firmware commercially, it is worth reading [this page](https://unsigned.io/sell_rnodes.html).
