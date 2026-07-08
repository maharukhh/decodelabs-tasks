"""
conveyor_sim.py
------------------
Main simulation loop for Project 4 -- PLC-Based Conveyor Sorting System.

Runs a fixed-step, deterministic scan-cycle loop (10 ms per scan, per
"The Industrial Control Paradigm" slide's "1ms-100ms CYCLIC SCAN") that:

    1. Reads simulated digital inputs (box presence, box height, E-Stop
       monitor, pushbuttons) each scan.
    2. Evaluates the ladder-logic blocks in plc_logic.py (debounce, edge
       detection, TON timer, CTU counter, FSM).
    3. Drives simulated digital outputs (conveyor motor, reject pusher,
       warning beacon).

Since there's no physical PLC or Siemens S7-PLCSIM available in this
environment, this scan loop *is* the "Virtual Commissioning" step from
the slides -- it validates the exact same three things the slide deck's
checklist calls out: FSM transition math, edge-detection fidelity, and
hardwired safety interlocks -- entirely in software, before anything
would be downloaded to a real PLC or physically wired E-Stop circuit.

Mission script (deliberately exercises every requirement from the brief):
    - 6 boxes arrive on the belt at fixed intervals; every 3rd box is
      "tall" and must be rejected 1.5s after its height sensor fires
      (matches the "Transit Timing & Pneumatic Delays" slide's own
      numbers: d=0.75m, v=0.5m/s -> 1.5s).
    - Partway through, the hardware E-Stop safety relay drops (a
      simulated e-stop press) -- the FSM must immediately fault, force
      every output off, and LATCH the fault even after the relay
      recovers, requiring an explicit manual reset (the "Latching"
      requirement from the E-Stop slide).
    - A batch is complete after BATCH_SIZE boxes have been counted via
      the rising-edge-driven CTU counter (not the raw sensor level).
"""

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from io_map import (
    PUSHER_DELAY_S,
    DEBOUNCE_TIME_S,
    BATCH_SIZE,
    PLC_SCAN_TIME_S,
)
from plc_logic import (
    Debounce,
    RisingEdgeDetector,
    TonTimer,
    CtuCounter,
    ConveyorFSM,
    IDLE,
    RUNNING,
    SORTING,
    FAULT,
)

# --- Scripted mission timeline (simulated field inputs) -----------------
SIM_DURATION_S = 16.0

# (arrival_time_s, sensor_active_duration_s, is_tall)
BOX_SCHEDULE = [
    (1.0, 0.30, False),
    (2.6, 0.30, True),
    (4.2, 0.30, False),
    (5.8, 0.30, True),   # this one's transit will be interrupted by the E-Stop below
    (9.4, 0.30, False),
    (11.0, 0.30, True),
]

ESTOP_DROP_TIME_S = 6.2      # safety relay reports unhealthy (simulated E-Stop press)
ESTOP_RECOVER_TIME_S = 6.6   # relay recovers (button released / reset)
MANUAL_RESET_TIME_S = 8.5    # operator performs manual fault reset


class TallBoxPusher:
    """
    Implements the "Transit Timing & Pneumatic Delays" slide exactly:
    on rising edge of the tall-box sensor, latch a pending-reject flag,
    feed it into a TON(1.5s) timer, and fire the reject pusher for one
    scan when the timer completes.
    """

    def __init__(self, delay_s):
        self.edge = RisingEdgeDetector()
        self.timer = TonTimer(delay_s)
        self._pending = False

    def update(self, tall_sensor_raw, dt):
        if self.edge.update(tall_sensor_raw):
            self._pending = True

        timer_done = self.timer.update(self._pending, dt)
        fire_pulse = False
        if timer_done:
            fire_pulse = True
            self._pending = False
            self.timer.reset()
        return fire_pulse


def run_simulation():
    n_steps = int(SIM_DURATION_S / PLC_SCAN_TIME_S)

    fsm = ConveyorFSM()
    stop_debounce = Debounce(DEBOUNCE_TIME_S)
    box_edge = RisingEdgeDetector()
    box_counter = CtuCounter(BATCH_SIZE)
    tall_pusher = TallBoxPusher(PUSHER_DELAY_S)

    history = {
        "t": [], "state": [], "motor": [], "reject_push": [],
        "warn_light": [], "prox_raw": [], "tall_raw": [],
        "box_count": [],
    }
    log = []
    manual_reset_done = False

    for step in range(n_steps):
        t = step * PLC_SCAN_TIME_S

        # --- Simulated raw field inputs for this scan --------------------
        start_pb = True   # operator holds/leaves Start engaged for the run
        stop_pb_raw = False
        estop_mon = not (ESTOP_DROP_TIME_S <= t < ESTOP_RECOVER_TIME_S)

        prox_raw = any(a <= t < a + d for (a, d, _tall) in BOX_SCHEDULE)
        tall_raw = any(a <= t < a + d for (a, d, tall) in BOX_SCHEDULE if tall)

        stop_pb = stop_debounce.update(stop_pb_raw, PLC_SCAN_TIME_S)

        # --- Manual fault reset (scripted operator action) ---------------
        if fsm.state == FAULT and not manual_reset_done and t >= MANUAL_RESET_TIME_S:
            fsm.manual_reset()
            box_counter.reset()  # operator also resets the batch, per this script
            manual_reset_done = True
            log.append(f"[t={t:6.2f}s] Operator MANUAL RESET issued. "
                       "Fault cleared, batch counter reset, returning to IDLE.")

        prev_state = fsm.state
        state = fsm.update(start_pb, stop_pb, estop_mon, prox_raw)

        if state != prev_state:
            log.append(f"[t={t:6.2f}s] State transition: {prev_state} -> {state}")
            if state == FAULT:
                log.append(f"[t={t:6.2f}s] 🛑 E-STOP FAULT: safety relay unhealthy "
                           "(i_EStop_Mon=FALSE). All outputs forced OFF and LATCHED.")

        # --- Box counting: rising edge only (never raw level) ------------
        box_pulse = box_edge.update(prox_raw) if state in (RUNNING, SORTING) else False
        if box_pulse:
            batch_done = box_counter.update(True)
            log.append(f"[t={t:6.2f}s] 📦 Box counted (rising edge). "
                       f"Batch count = {box_counter.accumulated_value}/{BATCH_SIZE}")
            fsm.batch_complete = batch_done
            if batch_done:
                log.append(f"[t={t:6.2f}s] ✅ BATCH COMPLETE ({BATCH_SIZE} boxes). "
                           "Returning to IDLE.")
        elif state not in (RUNNING, SORTING):
            box_counter.update(False)

        # --- Tall-box pneumatic reject, TON-delayed -----------------------
        reject_fire = False
        if state == FAULT:
            tall_pusher._pending = False
            tall_pusher.timer.reset()
        else:
            reject_fire = tall_pusher.update(tall_raw, PLC_SCAN_TIME_S)
            if reject_fire:
                log.append(f"[t={t:6.2f}s] 💨 REJECT PUSH fired "
                           f"({PUSHER_DELAY_S:.1f}s after tall-box detection).")

        # --- Outputs -------------------------------------------------------
        motor_on = state in (RUNNING, SORTING)
        warn_on = state == FAULT

        history["t"].append(t)
        history["state"].append(state)
        history["motor"].append(motor_on)
        history["reject_push"].append(reject_fire)
        history["warn_light"].append(warn_on)
        history["prox_raw"].append(prox_raw)
        history["tall_raw"].append(tall_raw)
        history["box_count"].append(box_counter.accumulated_value)

    return history, log


def plot_timeline(history, out_path):
    t = np.array(history["t"])
    state_codes = {IDLE: 0, RUNNING: 1, SORTING: 2, FAULT: 3}
    states_numeric = np.array([state_codes[s] for s in history["state"]])

    fig, axes = plt.subplots(5, 1, figsize=(13, 10), sharex=True)

    axes[0].step(t, states_numeric, where="post", color="#3b6fa0")
    axes[0].set_yticks(list(state_codes.values()))
    axes[0].set_yticklabels(list(state_codes.keys()))
    axes[0].set_title("FSM State")

    axes[1].step(t, history["prox_raw"], where="post", color="#4fa06e")
    axes[1].set_title("Raw Proximity Sensor (level signal)")
    axes[1].set_ylim(-0.1, 1.1)

    axes[2].step(t, history["tall_raw"], where="post", color="#c98a2b")
    axes[2].set_title("Raw Tall-Box Height Sensor (level signal)")
    axes[2].set_ylim(-0.1, 1.1)

    axes[3].step(t, history["motor"], where="post", color="#2b8a3e", label="q_Conv_Motor")
    axes[3].step(t, history["reject_push"], where="post", color="#c92b2b", label="q_Reject_Push (1-scan pulse)")
    axes[3].step(t, history["warn_light"], where="post", color="#d1a01e", label="q_Warn_Light")
    axes[3].set_title("Digital Outputs")
    axes[3].legend(loc="upper right", fontsize=8)
    axes[3].set_ylim(-0.1, 1.1)

    axes[4].step(t, history["box_count"], where="post", color="#7a4fa0")
    axes[4].set_title(f"CTU Batch Count (preset={BATCH_SIZE})")
    axes[4].set_xlabel("Time (s)")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"\nTimeline visualization saved to: {out_path}")


def main():
    print("=" * 72)
    print("PROJECT 4 -- PLC-Based Conveyor Sorting System")
    print("=" * 72)
    print(f"Scan time: {PLC_SCAN_TIME_S * 1000:.0f} ms | "
          f"Pusher delay: {PUSHER_DELAY_S:.1f} s | Batch size: {BATCH_SIZE}\n")

    history, log = run_simulation()
    for line in log:
        print(line)

    final_state = history["state"][-1]
    total_boxes_counted = history["box_count"][-1]
    total_rejects = sum(history["reject_push"])

    print("\n" + "-" * 72)
    print(f"Final FSM state: {final_state}")
    print(f"Total boxes counted toward current batch: {total_boxes_counted}/{BATCH_SIZE}")
    print(f"Total reject-pusher pulses fired: {total_rejects}")
    print("-" * 72)

    plot_timeline(history, "output/conveyor_timeline.png")


if __name__ == "__main__":
    main()
