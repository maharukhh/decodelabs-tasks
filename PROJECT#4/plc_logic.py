"""
plc_logic.py
-------------
The industrial "ladder logic" building blocks from the slide deck,
reimplemented as small, testable Python classes that are each called
once per PLC scan cycle -- exactly how a real ladder program is
structured (every block re-evaluates every scan, using only its own
persistent internal state).

Blocks implemented here:
    - Debounce          : software debounce filter for mechanical inputs
    - RisingEdgeDetector : R_TRIG -- "Positive Edge Detection" slide
    - TonTimer           : TON -- on-delay timer ("Timers vs. Counters" slide)
    - CtuCounter         : CTU -- up-counter ("Timers vs. Counters" slide)
    - ConveyorFSM        : the 4-state machine ("FSM Topology" +
                            "FSM Transition Logic Execution" slides)
"""


class Debounce:
    """
    Software debounce filter (per the "Diagnostic Note" on the Hardware
    Architecture slide): a mechanical input must hold a new value for
    `stable_time_s` of continuous scans before the filtered output
    changes. Protects against contact-bounce false transitions on
    pushbuttons.
    """

    def __init__(self, stable_time_s):
        self.stable_time_s = stable_time_s
        self._raw_last = False
        self._timer = 0.0
        self.output = False

    def update(self, raw_value, dt):
        if raw_value == self._raw_last:
            self._timer += dt
        else:
            self._timer = 0.0
            self._raw_last = raw_value

        if self._timer >= self.stable_time_s:
            self.output = raw_value
        return self.output


class RisingEdgeDetector:
    """
    R_TRIG block. Fires TRUE for exactly one scan the instant the input
    transitions FALSE -> TRUE, regardless of how many scans the input
    then stays TRUE for. This is the fix for the "Spatial-Temporal
    Mismatch" problem on the "Edge Detection Imperative" slide: a box
    sitting in the sensor beam for 400ms (40 scans at 10ms) must only
    ever produce ONE count, not forty.
    """

    def __init__(self):
        self._previous = False

    def update(self, current_value):
        pulse = current_value and not self._previous
        self._previous = current_value
        return pulse


class TonTimer:
    """
    TON (On-Delay Timer). Measures elapsed PHYSICAL DURATION while its
    input is held continuously TRUE. Automatically resets its elapsed
    time (ET) the instant the input drops FALSE -- per the
    "Timers vs. Counters" diagnostic slide, this is the correct block
    for "delay actuation by exactly 1.5s", NOT a counter.
    """

    def __init__(self, preset_time_s):
        self.preset_time_s = preset_time_s
        self.elapsed_time_s = 0.0
        self.done = False

    def update(self, input_value, dt):
        if input_value:
            self.elapsed_time_s = min(self.elapsed_time_s + dt, self.preset_time_s)
        else:
            self.elapsed_time_s = 0.0
        self.done = self.elapsed_time_s >= self.preset_time_s
        return self.done

    def reset(self):
        self.elapsed_time_s = 0.0
        self.done = False


class CtuCounter:
    """
    CTU (Up-Counter). Accumulates discrete EVENT occurrences, one per
    rising-edge pulse on its count input. Per the "Timers vs. Counters"
    slide, it does NOT auto-reset -- it requires an explicit RST command
    (here: an explicit call to .reset()). Correct block for "count
    exactly 5 items per batch".
    """

    def __init__(self, preset_value):
        self.preset_value = preset_value
        self.accumulated_value = 0
        self.done = False

    def update(self, count_pulse):
        if count_pulse:
            self.accumulated_value += 1
        self.done = self.accumulated_value >= self.preset_value
        return self.done

    def reset(self):
        self.accumulated_value = 0
        self.done = False


# --- FSM states ---------------------------------------------------------
IDLE = "IDLE"
RUNNING = "RUNNING"
SORTING = "SORTING"
FAULT = "FAULT"


class ConveyorFSM:
    """
    The 4-state machine from the "FSM Topology" slide. States are
    strictly mutually exclusive -- the system can never jump directly
    from IDLE to SORTING; it must always pass through the monitored
    RUNNING state, and any fault immediately forces every output to a
    fail-safe condition regardless of what state the system was in.

    Transition logic mirrors the exact boolean expressions on the
    "FSM Transition Logic Execution" slide:

        T_1->2 = i_Start_PB AND NOT(i_Stop_PB) AND i_EStop_Mon AND NOT(b_EStop_Fault)
        T_2->3 = i_Prox_Sensor AND NOT(b_EStop_Fault) AND NOT(b_Batch_Complete)
    """

    def __init__(self):
        self.state = IDLE
        self.estop_fault_latched = False
        self.batch_complete = False

    def update(self, start_pb, stop_pb, estop_mon, prox_sensor):
        # --- Fault detection: hardware E-Stop monitor is the priority
        # interlock. If the safety relay ever reports unhealthy, the FSM
        # latches a software fault immediately, regardless of what state
        # it was in -- mirrors "Strict E-Stop Safety Mandates": the
        # PLC's software fault flag is a MONITOR of the hardware cutoff,
        # never a substitute for it.
        if not estop_mon:
            self.estop_fault_latched = True

        if self.estop_fault_latched:
            self.state = FAULT
            return self.state

        if self.state == IDLE:
            can_start = start_pb and not stop_pb and estop_mon and not self.estop_fault_latched
            if can_start:
                self.state = RUNNING

        elif self.state == RUNNING:
            if stop_pb:
                self.state = IDLE
            else:
                can_sort = prox_sensor and not self.estop_fault_latched and not self.batch_complete
                if can_sort:
                    self.state = SORTING

        elif self.state == SORTING:
            # Stay in SORTING for as long as the box is actually under the
            # sensor; only fall back to RUNNING once it has fully cleared
            # (or return to IDLE on Stop / batch completion). Without this,
            # the FSM would thrash RUNNING<->SORTING every single scan
            # while one box sits in the sensor beam.
            if stop_pb:
                self.state = IDLE
            elif self.batch_complete:
                self.state = IDLE
            elif not prox_sensor:
                self.state = RUNNING

        return self.state

    def manual_reset(self):
        """Operator-initiated recovery from FAULT -- requires the E-Stop
        to be physically released (estop_mon healthy again) AND an
        explicit reset action, per the 'Latching' requirement on the
        E-Stop Identification slide."""
        self.estop_fault_latched = False
        self.batch_complete = False
        self.state = IDLE
