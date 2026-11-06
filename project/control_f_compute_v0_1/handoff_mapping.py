"""Map the standalone control blocks used by the native F handoff trial."""

from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "control_r7_v0_1"))
import synthesize


if __name__ == "__main__":
    core = PROJECT / "control_rtl_min_v0_1"
    local = core / "lc_min_controller.sv"
    params = dict(ENABLE_F_HANDOFF=1, STALL_LIMIT=4096, DRAIN_LIMIT=128, LOCAL_S_BYTES=16384)
    synthesize.CASES = [
        ("f_handoff_mother", core / "mc_min_controller.sv",
         dict(STALL_LIMIT=4096, NATIVE_ABI_ID=0x00017903), "clk_i", 1),
        ("f_handoff_source", local, dict(params, BLOCK_ID=0, ENABLE_F_STORE=1), "clk_i", 1),
        ("f_handoff_sink", local, dict(params, BLOCK_ID=1), "clk_i", 1),
        ("f_handoff_compute", Path(__file__).with_name("lc_f_store_adapter.sv"), {}, "clk", 1),
    ]
    synthesize.main()