"""Map the three controller configurations used by the bounded SiLU chain."""

from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "control_r7_v0_1"))
import synthesize


def main():
    core = PROJECT / "control_rtl_min_v0_1"
    synthesize.CASES = [
        ("silu_mother", core / "mc_min_controller.sv",
         {"STALL_LIMIT": 4096, "NATIVE_ABI_ID": 0x00017902}, "clk_i", 1),
        ("silu_local", core / "lc_min_controller.sv",
         {"BLOCK_ID": 0, "STALL_LIMIT": 4096, "DRAIN_LIMIT": 128, "LOCAL_S_BYTES": 16384,
          "ENABLE_M_DOT_STORE": 1, "M_DOT_STORE_SILU": 1}, "clk_i", 1),
        ("silu_store", Path(__file__).with_name("lc_m_dot_store_adapter.sv").resolve(),
         {"SILU": 1}, "clk", 1),
    ]
    synthesize.main()


if __name__ == "__main__":
    main()
