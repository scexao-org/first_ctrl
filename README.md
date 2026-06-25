# first_ctrl

Control software for **FIRST**, the photonic-lantern instrument operated on
**SCExAO** at the Subaru Telescope.

`first_ctrl` drives the instrument hardware (tip/tilt electronics, science
camera, Zaber injection stages, polarization optics), orchestrates data
acquisition and logging, and provides real-time displays for live alignment and
injection optimization.

## Overview

The codebase is organized into three top-level modules:

| Module | Responsibility |
| --- | --- |
| [`plcontrol/`](plcontrol/) | Hardware control, acquisition orchestration, and startup/shutdown sequences. The core of the system. |
| [`plrtd/`](plrtd/) | Real-time display (RTD) and live injection-optimization. Reconstructs flux maps from detector frames into shared memory. |
| [`polarization/`](polarization/) | Automated polarimetric calibration (half-wave plate + image-rotator sequences). |

## Architecture

The system is layered, from hardware up to high-level observing sequences:

```
Hardware (serial / DCAM camera / Zaber stages / polarization optics)
   └─ Comms bridge      plcontrol/lantern/   (serial ↔ ZMQ pub-sub, binary protocol)
       └─ Mid-level     plcontrol/plscripts/ (Base class + acq / geometry / modulation)
           └─ Sequences plcontrol/plscripts/ (startup, stopup, acquisition)
               └─ I/O    FITS logger · Redis keywords · pyMilk shared memory
                   └─ Display  plrtd/  (RTD + live optimization)
```

### `plcontrol/`

- **`lantern/`** — Bridge to the tip/tilt (piezo + modulation) electronics.
  - `lanternListener.py` — serial ↔ ZMQ bridge process with byte-escaped framing.
  - `baseDriver.py` / `lanternDriver.py` — low-level ZMQ transport and the
    high-level command API (`move_piezo`, `switch_control_loop`,
    `set_modulation_scale`, …).
  - `packerUnpacker.py` — binary packet (de)serialization with CRC32 validation.
  - `descriptors/*.yml` — YAML definitions of the telecommand/telemetry packet
    formats (`tmtc.yml`, `tc_packet_data.yml`, `tm_packet_data.yml`,
    `tc_reply_data.yml`, `errors.yml`). The wire protocol is data-driven: change
    the YAML, not the code.
  - `scripts.py` — multi-step electronics sequences (modulation upload/download,
    firmware configuration, telemetry retrieval).
- **`plscripts/`** — High-level instrument control. All scripts inherit from
  `Base` ([`base.py`](plcontrol/plscripts/base.py)) and share resources through
  the `links.py` global registry.
  - `acq.py` — acquisition control (ROLLING vs. TRIGGERED modes, readout modes,
    Wollaston prism, data-cube capture).
  - `geometry.py` — coordinate transforms between Zaber steps, tip/tilt piezo
    ADU, and camera pixels.
  - `modulation.py` — tip/tilt dither patterns (hexagon, raster, circle,
    crenels) within the firmware's 625-point limit.
  - `startup.py` / `stopup.py` — system initialization and end-of-night
    calibration (darks, flats, wavelength reference).
  - `focal.py` — focal-plane (pupil) camera control. *(Currently disabled.)*
  - `inspect.py` — photonic-lantern image reconstruction and Gaussian fitting.
- **`zaber/`** — Zaber XY injection-stage control (`zaber_chain3.py`) with an
  optional camera-offset tracking thread.

### `plrtd/`

- `plrtd.py` — `FirstPlRtd` thread: streams detector frames, reconstructs binned
  flux maps using the latest coupling/pixel calibration files, and publishes a
  display image to shared memory (`first_rtd`).
- `opti_live.py` — `LiveOptiFlux` thread: continuous injection-flux optimization
  display (`first_opti`).
- `runPL_library_*.py` — supporting libraries for pixel maps, coupling maps,
  image reconstruction, and FITS I/O.

### `polarization/`

- `hwp_imr_calibration.py` — `PolCalManager`: automated HWP + image-rotator
  calibration sequences.
- `cam_manager.py` — SSH-based FITS logging managers for remote acquisition.

## Getting started

### Dependencies

Python dependencies for the lantern module are listed in
[`plcontrol/lantern/requirements.txt`](plcontrol/lantern/requirements.txt):

```
zmq
byt
ruamel.yaml
pyserial
```

The full system additionally relies on the SCExAO software stack and external
services, including:

- `camstack` (Hamamatsu ORCAFlash via the DCAM API)
- `pyMilk` (shared-memory image streaming)
- `milk-streamFITSlog` (high-speed FITS data logging)
- `astropy`, `numpy`, `scipy`, `matplotlib`
- Pyro (remote camera object registry) and Redis (telescope/instrument keywords)
- `tmux` and a terminal emulator (`terminator`, falling back to `xterm`)

### Configuration

Two YAML configuration files are loaded at startup (paths are resolved relative
to `$HOME/src/firstctrl/first_ctrl/`):

- `plcontrol/lantern/config.yml` — electronics / ZMQ connection settings.
- `plcontrol/config_plcontrol.yml` — high-level control settings.

### Running

Launch scripts live in the `bin/` folders:

- [`plcontrol/bin/open_firstpl_ctrl`](plcontrol/bin/open_firstpl_ctrl) — sets up
  the persistent `tmux` dashboard (camera control, FITS merger, tip/tilt
  listener, framegrabber) and opens the 2×2 control layout.
- [`plcontrol/bin/firstpl_controller_start`](plcontrol/bin/firstpl_controller_start)
  — starts the main controller (`plcontrol_start_first.py`) in IPython. This
  brings up the camera, FITS logger, Pyro server, Zaber stages, and tip/tilt
  electronics, then wires everything together via `plscripts._linkit()`.
- [`plcontrol/bin/firstpl_tt_listener`](plcontrol/bin/firstpl_tt_listener) —
  starts the serial-to-ZMQ listener for the tip/tilt electronics.
- [`plcontrol/bin/firstpl_fitslogger`](plcontrol/bin/firstpl_fitslogger),
  [`firstpl_fitsmerger`](plcontrol/bin/firstpl_fitsmerger),
  [`firstpl_flashcode`](plcontrol/bin/firstpl_flashcode),
  [`setup_firstpl`](plcontrol/bin/setup_firstpl) — supporting backend tasks.
- [`plrtd/bin/firstpl_rtd_start`](plrtd/bin/firstpl_rtd_start) /
  [`firstpl_rtd_show`](plrtd/bin/firstpl_rtd_show) — start / attach the
  real-time display.
- [`plrtd/bin/firstpl_opti_start`](plrtd/bin/firstpl_opti_start) /
  [`firstpl_opti_show`](plrtd/bin/firstpl_opti_show) — start / attach the live
  optimization display.

## Data flow

A triggered acquisition proceeds roughly as follows:

1. `acq.set_mode_triggered()` engages the control loop and modulation on the
   tip/tilt electronics (commands relayed over ZMQ → listener → serial, with
   CRC-checked ACKs).
2. The camera is set to external trigger, synchronized to the electronics' TTL
   pulse train.
3. The FITS logger captures the data cube to disk.
4. The RTD / optimization processes read the latest FITS data, reconstruct the
   photonic-lantern image, and publish flux maps to shared memory for display.

## Notes

- Inter-module dependencies in `plscripts/` are resolved through module-level
  globals in `links.py`; objects are populated at startup by `_linkit()`.
- Several data and configuration paths are hardcoded for the SCExAO machines
  (e.g. `/mnt/sdata01/`, `/mnt/datazpool/PL/`, `$HOME/src/firstctrl/...`).
- The focal-plane (pupil) camera and UDP image streams are currently disabled in
  `plcontrol_start_first.py`.
