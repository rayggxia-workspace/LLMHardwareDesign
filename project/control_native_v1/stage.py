"""Stage exact upstream control and native-block revisions for the integration."""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

CONTROL = "500f630f27c1bb49cb8d2420ec14962277ddb70a"
UCF = "ec9cc35eaf8224bbfa5dae60b15c90cc59ba75b9"
PJ = "0485ed84dd13d8711c88609668cf0a903a006773"
ABI = 0x01930001
TOPOLOGY = 0x01930010


def archive(repo, rev, paths, output):
    data = subprocess.check_output(["git", "-C", str(repo), "archive", rev, *paths])
    with tarfile.open(fileobj=io.BytesIO(data)) as files:
        files.extractall(output, filter="data")


def extend_core(path):
    # The original profile paths are unchanged. A native descriptor uses the
    # existing L_EXEC/L_WAIT framing and delegates operation-specific checking.
    src = path.read_text()
    changes = {
        "parameter bit ENABLE_U_RMS = 1'b0)": """parameter bit ENABLE_U_RMS = 1'b0,
                           parameter bit ENABLE_NATIVE = 1'b0,
                           parameter [7:0] NATIVE_BLOCK_TYPE = 0,
                           parameter [31:0] NATIVE_TOPOLOGY = 0)""",
        "wire profile_cfg_ok = ENABLE_U_RMS ?": f"""wire profile_cfg_ok = ENABLE_NATIVE ?
       (LOCAL_S_BYTES==16384 && cfg_req_abi_id_i==32'h{ABI:08x} &&
        cfg_req_topology_id_i==NATIVE_TOPOLOGY && NATIVE_TOPOLOGY!=0) : ENABLE_U_RMS ?""",
        "wire [7:0] block_type = ENABLE_U_RMS ?": "wire [7:0] block_type = ENABLE_NATIVE ? NATIVE_BLOCK_TYPE : ENABLE_U_RMS ?",
        "wire profile_header_ok = ENABLE_U_RMS ?": """wire profile_header_ok = ENABLE_NATIVE ?
       (header[240+:16]==0 && header[256+:16]!=0 && header[272+:16]==0 && resource_mask==1) :
       ENABLE_U_RMS ?""",
        "header[256+:16]<=1": "header[256+:16]<=(ENABLE_NATIVE ? 16'd32 : 16'd1)",
        "wire exec_ok = ENABLE_U_RMS ?": """wire exec_ok = ENABLE_NATIVE ?
       (exec_desc[0+:32]==1 && exec_desc[48+:16]==0 &&
        exec_desc[64+:32]==32'hffffffff && exec_desc[96+:64]==0 &&
        exec_desc[160+:48]==48'hffffffffffff && exec_desc[208+:240]==0 &&
        exec_desc[448+:32]==abi_id && exec_desc[480+:32]==0) :
       ENABLE_U_RMS ?""",
        "|| header[256+:16]!=1 ||": "|| (!ENABLE_NATIVE && header[256+:16]!=1) ||",
    }
    for old, new in changes.items():
        if src.count(old) != 1:
            raise ValueError(f"upstream control drift: {old}")
        src = src.replace(old, new)
    path.write_text(src, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--qualified-s", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    control = subprocess.check_output(
        ["git", "-C", str(args.repo), "ls-tree", "--name-only", CONTROL + ":project"], text=True
    ).splitlines()
    archive(args.repo, CONTROL, ["project/" + name for name in control if name.startswith("control_")], output)
    archive(args.repo, UCF, ["project/rtl", "project/experiments/block_ucf_v1/stage_inputs.py",
                            "project/experiments/block_ucf_v1/native_r.vlt",
                            "project/experiments/block_ucf_v1/tb_block_ucf16.sv",
                            "project/experiments/block_ucf_v1/rtl_integration.sh"], output / "ucf")
    archive(args.repo, PJ, ["project/rtl", "project/experiments/block_pj_v1"], output / "pj")
    subprocess.run(["python", str(output / "ucf/project/experiments/block_ucf_v1/stage_inputs.py"),
                    "rtl", str(output / "native")], check=True)
    extend_core(output / "project/control_rtl_min_v0_1/lc_min_controller.sv")
    if args.qualified_s:
        project = args.qualified_s / "project"
        generator = project / "experiments/block_local_s/physical.py"
        data = generator.read_bytes()
        tree = ast.parse(data)
        top_text = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "top_text")
        env = {"VARIANTS": {"p4": (4, True), "n4": (4, False)}}
        exec(compile(ast.Module(body=[top_text], type_ignores=[]), str(generator), "exec"), env)
        for variant in env["VARIANTS"]:
            (output / "native" / f"{variant}.sv").write_text(env["top_text"](variant, True),
                                                             encoding="utf-8", newline="\n")
        for relative in ("block_local_s/block_local_s_macro.sv", "block_local_s/block_local_s_arbiter.sv",
                         "block_feed_v1/block_feed_loader.sv", "s_sram/block_feed_s16k_sram.sv"):
            target = output / "native" / Path(relative).name
            accepted = (project / "rtl" / relative).read_bytes().replace(b"\r\n", b"\n")
            if target.read_bytes() != accepted:
                raise ValueError(f"P/J and U/C/F leaf sources disagree for {relative}")
    ctrl = output / "project/control_rtl_min_v0_1"
    for file, anchor, param in (
        ("tb_network_mc_wires.svh", "`ifdef TB_U_COMPUTE", f".NATIVE_ABI_ID(32'h{ABI:08x})"),
        ("tb_network_lc_wires.svh", "`ifdef TB_U_COMPUTE", ".ENABLE_NATIVE(1'b1),.NATIVE_BLOCK_TYPE(8'(KIND)),.NATIVE_TOPOLOGY(TOPOLOGY_ID)"),
    ):
        path = ctrl / file
        original = path.read_text()
        path.write_text(original.replace(anchor, f"`ifdef TB_NATIVE\n   ,{param}\n   `endif\n   {anchor}", 1),
                        encoding="utf-8", newline="\n")
    (output / "sources.json").write_text(json.dumps({
        "control": CONTROL, "ucf": UCF, "pj": PJ,
        "rtl_sha256": {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(output.rglob("*.sv"))}
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
