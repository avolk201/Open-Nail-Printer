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
* **Communication:** Slices the halftone matrix into 42-byte chunks and transmits them via UART over USB to the ESP32 at 921,600 baud.

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

## Repository Structure

* `/cad`: (In Progress) Onshape mechanical assemblies, STL files, and 3D printable carriage mounts.
* `/Nail-printer-embedded`: ESP-IDF C source code and FreeRTOS task configurations.
* `/NailPrinter_PCB`: KiCad 8.0 project files, library symbols, and footprints.
## Project Status

### Completed Features
* **Backend (Raspberry Pi)**
    * FastAPI server architecture with REST endpoints for system control and design management.
    * Computer Vision pipeline: Floyd-Steinberg halftoning (RGB to CMYK), 1D sine-wave nail warping, and manual affine transformations.
    * High-speed UART serial protocol (921,600 baud) for ESP32 communication.
    * MJPEG camera streaming for real-time nail alignment.
* **Frontend (Touchscreen UI)**
    * Vue 3/Vite application optimized for 7" Raspberry Pi touchscreen.
    * Interactive alignment interface with manual bounding box selection.
    * Real-time design adjustment (scale, rotation, pan) via overlay.
    * Design gallery and "Set" printing workflow for sequential multi-finger printing.
* **Firmware (ESP32)**
    * Dual-core task distribution: UART ingestion on Core 0, motion/sync on Core 1.
    * I2S Parallel DMA driver for microsecond-accurate HP 63 cartridge firing.
    * TMC2209 stepper driver integration via UART and MCPWM pulse generation.
    * Hardware pulse counting (PCNT) infrastructure for linear optical encoder feedback.
* **Hardware (KiCad)**
    * Two-board architecture: Stationary Mainboard and Smart Carriage.
    * Power distribution for 24V, 16V (firing), 9V (logic), and 5V (MCU) rails.
    * Hardware guillotine failsafe using capacitive AC-coupling.

### Pending / TODO
* **Firmware**
    * Implement hardware-level trigger linking PCNT encoder thresholds to I2S DMA output for closed-loop positional accuracy.
    * Complete homing sequence logic within limit switch ISR handlers.
    * Implement S-curve acceleration ramps for smoother gantry motion.
* **Backend**
    * Replace OpenCV camera capture with native `libcamera` or `picamera2` for Raspberry Pi hardware.
    * Implement automated nail segmentation to replace manual bounding box alignment.
* **Hardware**
    * Verify and resolve 9V/3.3V domain crossing alerts in schematic.
    * Add fiducial markers for automated pick-and-place assembly.
    * Populate manufacturer part numbers (MPNs) across the Bill of Materials.
* **Mechanics**
    * Finalize and release Onshape CAD assemblies and 3D printable STL files for the gantry and carriage.

## Development Milestones

1.  **Software**: Implementation of the FastAPI server, Vue UI, and CMYK halftoning pipeline. [DONE]
2.  **Hardware Design**: Design and layout of the Mainboard and Smart Carriage PCBs. [DONE]
3.  **Hardware Validation**: Manufacture PCBs and confirm functional operation. [TODO]
4.  **Firmware Core**: High-speed communication and raw I2S printhead driving. [DONE]
5.  **Motion Control Integration**: Synchronization of gantry movement with firmware step generation. [IN PROGRESS]
6.  **Closed-Loop Accuracy**: Linking linear optical encoder pulses to hardware-triggered ink deposition. [TODO]
7.  **Kiosk Mode Integration**: Final Raspberry Pi OS configuration for standalone touchscreen operation. [TODO]
8.  **System Validation**: Full 5-finger print test using water-based cosmetic ink. [TODO]


### Prerequisites
* Raspberry Pi OS Lite (64-bit)
* Espressif ESP-IDF v5.x
* KiCad 8.0+
* 24V 3A DC Power Supply
* Modified HP 63 Tri-Color Cartridge (Flushed and refilled with water-based cosmetic/edible ink).

### Software Setup
1. Clone the repository to the Raspberry Pi.
2. Navigate to `backend/` and install dependencies: `pip install -r requirements.txt`.
3. Configure the Pi to launch the FastAPI server on boot.
4. Flash the ESP32 firmware: `idf.py build flash monitor`.


## License
This project is licensed under the MIT License. See the `LICENSE` file for details. Note that any proprietary modifications to the HP 63 cartridge footprint are for educational and research purposes only.
