"""Standalone 300 MHz mapping entry for the extended handoff configurations."""

from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "control_r7_v0_1"))
import synthesize

CORE = PROJECT / "control_rtl_min_v0_1"
R4 = PROJECT / "control_r4_v0_1"
COMMON = dict(ENABLE_EXT_HANDOFF=1, STALL_LIMIT=4096, DRAIN_LIMIT=128, LOCAL_S_BYTES=16384)
PROFILES = {
    "u": (0x00017904, {"ENABLE_U_RMS": 1}, "lc_u_rms_adapter.sv", {}),
    "j": (0x00017905, {"EXTRA_PROFILE": 1}, "lc_j_lease_adapter.sv", {}),
    "c": (0x00017906, {"EXTRA_PROFILE": 2}, "lc_c_state_adapter.sv", {"RECEIPT_TIMEOUT_CYCLES": 256}),
}


def configs(profile):
    if profile == "common":
        return [
            ("extended_sink", CORE / "lc_min_controller.sv", dict(COMMON, BLOCK_ID=1), "clk_i", 1),
            ("raw32_adapter", R4 / "lc_raw16_s_adapter.sv", dict(ENABLE_TWO_WORD=1), "clk", 1),
            ("f_cohort6", R4 / "cohort_reset_controller.sv", dict(MEMBERS=6), "clk", 1),
        ]
    abi, params, adapter, adapter_params = PROFILES[profile]
    return [
        (f"{profile}_mother", CORE / "mc_min_controller.sv",
         dict(STALL_LIMIT=4096, NATIVE_ABI_ID=abi), "clk_i", 1),
        (f"{profile}_source", CORE / "lc_min_controller.sv",
         dict(COMMON, BLOCK_ID=0, **params), "clk_i", 1),
        (f"{profile}_compute", PROJECT / f"control_{profile}_compute_v0_1" / adapter,
         adapter_params, "clk", 1),
    ]


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in (*PROFILES, "common"):
        raise SystemExit("first argument must be u, j, c or common")
    synthesize.CASES = configs(sys.argv.pop(1))
    synthesize.main()