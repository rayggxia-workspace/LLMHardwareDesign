"""Stage immutable RTL, P&R, or audit input files from this checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RTL = ROOT / "project" / "rtl"
BV1 = HERE.parent / "block_v1"
ACCEPTED_S = "ac29d11ed5728861689046d04a0f03060de2439c"

files = {
    "rtl": ("rtl_integration.sh", "tb_block_ucf16.sv", "native_r.vlt"),
    "physical": ("physical_batch.sh", "physical_candidate.py"),
    "audit": ("inspect_candidate.py", "inspect_batch.sh", "gate_regression.sh",
              "tb_block_ucf16.sv", "package_accepted.py"),
    "diagnose": ("critical_probe.sh", "critical.tcl"),
}
leaf = {
    "block_ucf_v1": ("block_ucf16.sv", "ucf_s_compute_client.sv", "ucf_r256_service.sv"),
    "block_local_s": ("block_local_s_arbiter.sv", "block_local_s_macro.sv"),
    "s_sram": ("block_feed_s16k_sram.sv",),
    "block_feed_v1": ("block_feed_s16k.sv", "block_feed_loader.sv"),
    "r_local_state": ("r_stream_local.sv", "r_state_store.sv"),
    "block_v2": ("block_v2_e.sv", "block_v2_g.sv", "block_v2_g_tables.svh",
                 "block_v2_n.sv", "block_v2_n_group.sv", "block_v2_n_exp.svh"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=files)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    paths = [HERE / name for name in files[args.stage]]
    if args.stage in ("rtl", "physical"):
        paths += [RTL / folder / name for folder, names in leaf.items() for name in names]
    if args.stage == "physical":
        paths += [HERE.parent / "block_feed_v1" / "pins.py"]
        paths += [BV1 / name for name in ("pin_contract.py", "structural_view.py",
                                           "revision300_geometry.py", "technology-2um-v1.json")]
    if args.stage == "audit":
        paths += [BV1 / name for name in ("native_annotation.py", "native_annotation.tcl",
                                           "native_passive_endpoint.py", "native_cell_gate.py",
                                           "native_sta.py", "native_sta.tcl", "native_physical.tcl",
                                           "native_undriven.tcl", "pin_contract.py",
                                           "native_logic_projection.py", "native_formal.py",
                                           "structural_view.py")]
    args.directory.mkdir(parents=True, exist_ok=False)
    manifest = {}

    def put(name, data, source):
        assert name not in manifest, name
        data = data.replace(b"\r\n", b"\n")
        (args.directory / name).write_bytes(data)
        manifest[name] = {"source": source, "sha256": hashlib.sha256(data).hexdigest()}

    for path in paths:
        put(path.name, path.read_bytes(), path.relative_to(ROOT).as_posix())
    if args.stage == "audit":
        for name in ("clock_checks.py", "clock_checks.tcl", "stream_geometry.py",
                     "stream_inventory.tcl", "formal_banks.py"):
            source = ACCEPTED_S + ":project/experiments/s_sram/" + name
            put(name, subprocess.check_output(["git", "show", source], cwd=ROOT), source)
    (args.directory / "stage.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
