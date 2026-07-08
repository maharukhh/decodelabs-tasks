# Project 4 — PLC-Based Conveyor Sorting System
### DecodeLabs Robotics & Automation Internship — Industrial Training Kit (Optional Mastery Phase)

## 🎯 Goal
Design the industrial control logic for a conveyor line that sorts boxes,
diverting any oversize ("tall") box with a pneumatic pusher — with a
fully mapped I/O table, a sequence-based state machine, and strict
hardwired safety interlocks.

## 📁 Folder contents

```
project4/
├── README.md                    ← this file
├── requirements.txt
├── io_map.py                    ← digital I/O tag table + process constants
├── plc_logic.py                 ← Debounce, R_TRIG, TON, CTU, and the FSM
├── conveyor_sim.py              ← main scan-cycle simulation loop (run this)
└── output/
    └── conveyor_timeline.png    ← generated after running
```

> **Why a Python scan loop instead of real Siemens S7-PLCSIM /
> ladder logic?** The brief's tools (a real PLC, ladder-logic IDE,
> physical hardware) aren't available in this environment. Every piece
> of *logic* those tools exist to run — I/O mapping, debounce filtering,
> rising-edge detection, on-delay timers, up-counters, and the finite
> state machine itself — is implemented for real in the `.py` files
> below, running on a fixed 10 ms scan-cycle loop that mirrors a real
> PLC's deterministic cyclic scan exactly (see "The Industrial Control
> Paradigm" slide). `conveyor_sim.py`'s console log + timeline plot are
> this project's stand-in for the "Virtual Commissioning" workflow — the
> exact three things its own checklist calls out (FSM transition math,
> edge-detection fidelity, hardwired safety interlocks) are all
> validated here before anything would be downloaded to real hardware.

## 🧠 The pipeline (matches the slide deck's architecture)

### 1. I/O Mapping (`io_map.py`)
Every physical field device gets a fixed `%I` / `%Q` tag address, exactly
matching the "Hardware Architecture & I/O Mapping" slide:

| Tag | Device |
|---|---|
| `%I0.0` | Start Push Button (NO) |
| `%I0.1` | Proximity Sensor |
| `%I0.2` | Safety Relay Monitor |
| `%I0.3` | Stop Push Button (NC) |
| `%I0.4` | High-Level Height Sensor |
| `%Q1.0` | Belt Drive Contactor |
| `%Q1.1` | Diverter Solenoid Valve |
| `%Q1.2` | Amber Warning Beacon |

It also derives the pusher delay directly from the slide's own transit
physics: `d=0.75m / v=0.5m/s = 1.5s`.

### 2. Ladder-logic building blocks (`plc_logic.py`)
- **`Debounce`** — 500 ms software debounce filter on mechanical
  pushbuttons (per the "Diagnostic Note" on the Hardware Architecture
  slide).
- **`RisingEdgeDetector` (R_TRIG)** — fires exactly one pulse per
  physical box, no matter how many scans it blocks the sensor beam for.
  This is the fix for the "Spatial-Temporal Mismatch" called out on the
  "Edge Detection Imperative" slide (a box sitting in the beam for 400 ms
  at a 10 ms scan rate would otherwise register 40 false counts).
- **`TonTimer` (TON)** — measures elapsed *duration*, auto-resets on
  FALSE. Used to delay the reject pusher by exactly 1.5 s after a tall
  box is detected.
- **`CtuCounter` (CTU)** — accumulates *discrete events* (one batch = 5
  boxes), and does **not** auto-reset — matches the "Timers vs. Counters"
  diagnostic slide's distinction exactly.
- **`ConveyorFSM`** — the 4-state machine (`IDLE → RUNNING → SORTING`,
  with any-state-to-`FAULT`) from the "FSM Topology" slide. States are
  strictly mutually exclusive; the system can never jump straight from
  `IDLE` to `SORTING` without passing through the monitored `RUNNING`
  state, and its transition conditions are the exact boolean expressions
  from the "FSM Transition Logic Execution" slide
  (`T_1->2`, `T_2->3`).

### 3. Safety interlocks
Per the "Strict E-Stop Safety Mandates" slide, a real E-Stop circuit
cuts motor power at the **hardware relay**, never through the PLC's CPU
alone (a firmware lockup could otherwise fail to de-energize outputs).
This simulation models that distinction: `i_EStop_Mon` represents the
*hardware* safety relay's health, and the FSM's software fault flag is
only ever a **monitor** of it, never a substitute. Once tripped, the
fault **latches** — even after the relay recovers, the system stays in
`FAULT` until an explicit operator `manual_reset()`, matching the
"Latching" requirement from the "E-Stop Identification & PLC
Coordination" slide.

### 4. The mission script (`conveyor_sim.py`)
6 boxes cross the sensor at scripted intervals (every 3rd one is
"tall"); partway through, a simulated E-Stop press drops the safety
relay for 0.4 s. The FSM must fault immediately, force every output off,
and stay latched in `FAULT` until a scripted manual reset at t=8.5s —
after which the line resumes and finishes counting toward a fresh batch
of 5.

## ▶️ How to run

```bash
pip install numpy matplotlib --break-system-packages
python3 conveyor_sim.py
```

### Sample console output
```
[t=  0.00s] State transition: IDLE -> RUNNING
[t=  1.00s] State transition: RUNNING -> SORTING
[t=  1.00s] 📦 Box counted (rising edge). Batch count = 1/5
[t=  1.30s] State transition: SORTING -> RUNNING
...
[t=  4.09s] 💨 REJECT PUSH fired (1.5s after tall-box detection).
...
[t=  6.20s] State transition: RUNNING -> FAULT
[t=  6.20s] 🛑 E-STOP FAULT: safety relay unhealthy (i_EStop_Mon=FALSE). All outputs forced OFF and LATCHED.
[t=  8.50s] Operator MANUAL RESET issued. Fault cleared, batch counter reset, returning to IDLE.
[t=  8.50s] State transition: IDLE -> RUNNING
...
Final FSM state: RUNNING
Total boxes counted toward current batch: 2/5
Total reject-pusher pulses fired: 2
```

The saved `output/conveyor_timeline.png` stacks five synchronized
panels: FSM state, the two raw sensor level signals, all three digital
outputs, and the running CTU batch count — so you can visually confirm
the reject pusher fires exactly 1.5 s after each tall-box detection, and
that every output snaps to zero the instant the fault hits.

## 🔧 Tuning knobs
| Setting | File | Effect |
|---|---|---|
| `BOX_SCHEDULE`, `ESTOP_DROP_TIME_S`, `MANUAL_RESET_TIME_S` | `conveyor_sim.py` | Mission timeline / when events happen |
| `PUSHER_DELAY_S`, `DEBOUNCE_TIME_S`, `BATCH_SIZE`, `PLC_SCAN_TIME_S` | `io_map.py` | Physical/process constants |
| `preset_time_s` / `preset_value` args | `plc_logic.py` (TonTimer / CtuCounter) | Timer & counter presets |

## 📝 What to submit
1. The three `.py` files
2. `output/conveyor_timeline.png`
3. The console log showing the E-Stop fault + latch + manual reset
   sequence (proves the safety interlock actually triggers, not just
   that boxes happen to get sorted)
4. A short note on how you'd wire this to a real Siemens S7-PLCSIM /
   TIA Portal project, and what would change moving from a simulated
   sensor level to a real 24VDC discrete input
