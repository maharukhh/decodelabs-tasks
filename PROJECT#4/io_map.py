"""
io_map.py
----------
Digital I/O tag map for the PLC-based conveyor sorting system.

Matches the "Hardware Architecture & I/O Mapping" slide exactly: every
physical field device gets a fixed %I (input) or %Q (output) address,
the same way a real PLC's I/O table is documented before a single line
of logic is written.
"""

# --- Physical Inputs (Sensing) -----------------------------------------
I_START_PB = "%I0.0"      # i_Start_PB   - Start push button (Normally Open)
I_PROX_SENSOR = "%I0.1"   # i_Prox_Sensor - Proximity sensor (box present on belt)
I_ESTOP_MON = "%I0.2"     # i_EStop_Mon  - Safety relay monitor (healthy = TRUE)
I_STOP_PB = "%I0.3"       # i_Stop_PB    - Stop push button (Normally Closed)
I_TALL_SENSOR = "%I0.4"   # i_Tall_Sensor - High-level height sensor (oversize box)

# --- Physical Outputs (Acting) -----------------------------------------
Q_CONV_MOTOR = "%Q1.0"    # q_Conv_Motor  - Belt drive contactor
Q_REJECT_PUSH = "%Q1.1"   # q_Reject_Push - Diverter / pneumatic pusher solenoid
Q_WARN_LIGHT = "%Q1.2"    # q_Warn_Light  - Amber warning beacon

IO_MAP = {
    "inputs": {
        I_START_PB: "Start Push Button (NO)",
        I_PROX_SENSOR: "Proximity Sensor",
        I_ESTOP_MON: "Safety Relay Monitor",
        I_STOP_PB: "Stop Push Button (NC)",
        I_TALL_SENSOR: "High-Level Height Sensor",
    },
    "outputs": {
        Q_CONV_MOTOR: "Belt Drive Contactor",
        Q_REJECT_PUSH: "Diverter Solenoid Valve",
        Q_WARN_LIGHT: "Amber Warning Beacon",
    },
}

# --- Process constants (from the "Transit Timing & Pneumatic Delays" slide) ---
SENSOR_TO_PUSHER_DISTANCE_M = 0.75
BELT_SPEED_M_S = 0.5
PUSHER_DELAY_S = SENSOR_TO_PUSHER_DISTANCE_M / BELT_SPEED_M_S  # = 1.5 s

# --- Debounce / batch constants -----------------------------------------
DEBOUNCE_TIME_S = 0.5        # 500 ms software debounce on mechanical pushbuttons
BATCH_SIZE = 5               # CTU preset value: boxes per completed batch
PLC_SCAN_TIME_S = 0.01        # 10 ms cyclic scan (deterministic, per the slides)


if __name__ == "__main__":
    print("Digital Inputs:")
    for addr, name in IO_MAP["inputs"].items():
        print(f"  {addr:8s} {name}")
    print("\nDigital Outputs:")
    for addr, name in IO_MAP["outputs"].items():
        print(f"  {addr:8s} {name}")
    print(f"\nCalculated pusher delay: {PUSHER_DELAY_S:.2f} s "
          f"({SENSOR_TO_PUSHER_DISTANCE_M} m / {BELT_SPEED_M_S} m/s)")
