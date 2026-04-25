# Open-Source Inkjet Nail Printer

## Overview
This repository contains the hardware schematics, firmware, and software required to build a custom, desktop-scale inkjet nail printer. The system utilizes a standard thermal inkjet (TIJ) cartridge (HP 63) to deposit water-based cosmetic/edible ink directly onto a prepared human nail. 

Unlike commercial alternatives that rely on closed-source hardware and DRM-locked consumables, this project provides a fully open architecture. It uses a distributed processing model, offloading high-level computer vision and web serving to a Raspberry Pi, while delegating strict, microsecond-accurate hardware control to an ESP32 microcontroller utilizing I2S Direct Memory Access (DMA).

## System Architecture

The project is divided into three distinct operational domains:

### 1. High-Level Processing (Raspberry Pi 3B+)
* **Environment:** Python 3, FastAPI, OpenCV.
* **Function:** Operates in a headless kiosk mode serving a React/Vue frontend to a local touchscreen UI. 
* **Vision Pipeline:** Captures the finger via a fixed-focus, low-distortion downward-facing camera. Allows the user to define a bounding box, warps the selected 2D image using a 1D sine-wave pre-distortion algorithm to map to the nail's curvature, and converts the RGB image into a binary CMYK halftone matrix via Floyd-Steinberg error diffusion.
* **Communication:** Slices the halftone matrix into 32-byte chunks and transmits them via UART over USB to the ESP32 at 921,600 baud.

### 2. Real-Time Hardware Control (ESP32)
* **Environment:** ESP-IDF (C), FreeRTOS.
* **Core 0:** Dedicated to receiving UART payloads and buffering them into FreeRTOS queues.
* **Core 1:** Manages electromechanical synchronization. Triggers the I2S DMA peripheral to output perfectly timed 5µs pulses across 12 parallel GPIO pins without CPU blocking. 
* **Motion Control:** Interfaces with TMC2209 stepper drivers for silent, vibration-free gantry movement, utilizing a linear optical encoder and hardware pulse counting (PCNT) for absolute microscopic positional accuracy.

### 3. Custom PCB & Power Distribution
The electrical architecture is split across two custom KiCad boards to ensure signal integrity and isolate high voltages:
* **Stationary Mainboard:** Houses the ESP32, TMC2209 drivers, and the central Power Distribution Network (PDN). It steps a 24V DC input down to 16V (Printhead), 9V (Logic Leveling), and 5V (Raspberry Pi/ESP32 supply).
* **Smart Carriage:** A lightweight, moving PCB connected via a Flexible Flat Cable (FFC). It houses CD4504B CMOS level shifters to step 3.3V data lines to 9V, and a custom P-Channel/N-Channel discrete MOSFET array to switch 16V firing pulses millimeters away from the cartridge's pogo-pin interface, eliminating inductive ringing.

## Safety & Hardware Interlocks
A critical feature of this design is the hardware "guillotine" failsafe located on the Smart Carriage. 

Thermal inkjet resistors will permanently burn out if held high for more than a few microseconds. To protect against software lockups, the 16V firing lines are routed through an AC-coupled gate drive (capacitive differentiator). An RC time-constant enforces a strict physical timeout of approximately 10-15µs. If the ESP32 freezes while a firing pin is pulled high, the capacitor will charge and autonomously sever the 16V supply to the cartridge, preventing thermal runaway.

## The Chemical Print Workflow
Standard UV nail gel is hydrophobic, meaning water-based inkjet droplets will bead and smear upon contact. The system requires a strict chemical preparation process:
1. **Base Coat:** Apply standard UV gel base coat to protect the natural nail. Cure completely.
2. **Inkjet Receptive Coating (IRC):** Apply a specialized Print Gel (or Matte UV Top Coat) to create a hydrophilic, micro-porous surface. Cure completely.
3. **Print Phase:** The machine jets water-based ink onto the IRC. The pores instantly absorb the carrier fluid, fixing the pigment in place and preventing dot gain. Allow 60 seconds for evaporation.
4. **Encapsulation:** Seal the dry ink with a standard clear UV gel top coat. Cure completely.

## Repository Structure

* `/cad`: Onshape mechanical assemblies, STL files, and 3D printable carriage mounts.
* `/firmware/esp32`: C source code and CMake build files for the ESP-IDF environment.
* `/hardware/kicad`: PCB schematics, footprints, and Gerber files for the Mainboard and Smart Carriage.
* `/software/backend`: Python FastAPI server, serial communication protocols, and OpenCV halftoning pipelines.
* `/software/frontend`: Web-based touchscreen user interface.

## Assembly & Installation

### Prerequisites
* Raspberry Pi OS Lite (64-bit)
* Espressif ESP-IDF v5.x
* KiCad 7.0+
* 24V 3A DC Power Supply
* Modified HP 63 Tri-Color Cartridge (Flushed and refilled with water-based cosmetic/edible ink).

### Software Setup
1. Clone the repository to the Raspberry Pi.
2. Navigate to `/software/backend` and install dependencies via `pip install -r requirements.txt`.
3. Configure the Pi to launch the FastAPI server on boot via systemd.
4. Flash the ESP32 firmware using the ESP-IDF toolchain: `idf.py build flash monitor`.

### Hardware Assembly
1. Fabricate the PCBs using the provided Gerber files. 
2. Populate the boards, ensuring the LCSC part numbers match the Bill of Materials for automated surface-mount assembly.
3. Assemble the Cartesian gantry using NEMA 14 stepper motors, optical limit switches, and a 150 LPI optical encoder strip.
4. Perform the Hand-Eye Calibration routine detailed in the documentation to map camera pixel coordinates to physical stepper steps.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details. Note that any proprietary modifications to the HP 63 cartridge footprint or reverse-engineered hardware protocols are implemented here for educational and research purposes only.
