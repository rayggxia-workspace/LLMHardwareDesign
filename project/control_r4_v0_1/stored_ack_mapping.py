"""Map the one-slot stored acknowledgement guard at the R7.2 clock."""

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "control_r7_v0_1"))
import synthesize


if __name__ == "__main__":
    synthesize.CASES = [
        ("stored_ack_guard", HERE / "p_stored_ack_guard.sv", {"ID_BITS": 272}, "clk", 1),
    ]
    synthesize.main()
