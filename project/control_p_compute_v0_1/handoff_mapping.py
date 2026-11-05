"""Map the two local-controller configurations used in the handoff trial."""

from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "control_r7_v0_1"))
import synthesize


if __name__ == "__main__":
    rtl = PROJECT / "control_rtl_min_v0_1/lc_min_controller.sv"
    params = dict(ENABLE_P_HANDOFF=1, STALL_LIMIT=4096, DRAIN_LIMIT=128, LOCAL_S_BYTES=16384)
    synthesize.CASES = [
        ("handoff_source", rtl, dict(params, BLOCK_ID=0, ENABLE_M_DOT_STORE=1, M_DOT_STORE_SILU=1), "clk_i", 1),
        ("handoff_sink", rtl, dict(params, BLOCK_ID=1), "clk_i", 1),
    ]
    synthesize.main()
