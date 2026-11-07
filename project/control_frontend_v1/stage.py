"""Stage pinned native groups against the current compact control RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
CORE = PROJECT / "control_rtl_min_v0_1"


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"staging anchor changed in {path.name}: {old}")
    path.write_text(text.replace(old, new))


def command(script, *args):
    subprocess.run([sys.executable, str(script), *(str(x) for x in args)], check=True)


def verify(root, entries):
    for name, expected in entries.items():
        data = (root / name).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != expected:
            raise ValueError(f"upstream blob changed: {name}")


def overlay(bundle):
    target = bundle / "staged/project"
    for source in PROJECT.glob("control_*"):
        if source.is_dir() and source != HERE:
            shutil.copytree(source, target / source.name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
    pair = bundle / "design/tb_native_pair.sv"
    text = pair.read_text()
    old = '    assign task_ready_i=task_target_o<2 && lc_ready[task_target_o[0]];\n    assign return_valid_i=|lc_event;\n    assign return_packet_i=lc_event[0] ? lc_packet[0] : lc_packet[1];'
    replacement = '    wire [1:0] routed_task_valid, routed_return_ready;\n    wire routed_credit;\n    wire [511:0] routed_task_packet;\n    two_local_link control_link(.clk_i,.rst_ni,.task_valid_i(task_valid_o),\n        .task_credit_i(task_credit_o),.task_target_i(task_target_o),.task_packet_i(task_packet_o),\n        .task_ready_o(task_ready_i),.local_task_valid_o(routed_task_valid),\n        .local_task_credit_o(routed_credit),.local_task_packet_o(routed_task_packet),\n        .local_task_ready_i(lc_ready),.local_return_valid_i(lc_event),\n        .local_return_packet_i({lc_packet[1],lc_packet[0]}),\n        .local_return_ready_o(routed_return_ready),.return_valid_o(return_valid_i),\n        .return_packet_o(return_packet_i),.return_ready_i(return_ready_o));'
    if text.count(old)!=1:
        raise ValueError("pair return routing changed")
    text = text.replace(old,replacement)
    text = text.replace(".task_valid_i(task_valid_o && task_target_o==8'(i)),.task_packet_i(task_packet_o),",
                        ".task_valid_i(routed_task_valid[i]),.task_packet_i(routed_task_packet),")
    text = text.replace(".task_credit_i(task_credit_o),.task_ready_o(lc_ready[i]),",
                        ".task_credit_i(routed_credit),.task_ready_o(lc_ready[i]),")
    text = text.replace(".event_ready_i(return_ready_o && (i==0 || !lc_event[0])),",
                        ".event_ready_i(routed_return_ready[i]),")
    pair.write_text(text)
    image = bundle / "design/images.py"
    replace_once(image, "from run_a2 import assemble, mem",
                 "from run_a2 import assemble as assemble_original, mem\n"
                 "    def assemble(*args, **kwargs):\n"
                 "        return assemble_original(*args, **kwargs, instruction_version=2)")
    # Keep the stock testbench's PM load/readback. Check the version independently.
    for name in ("tb_native_pair.sv", "tb_cfj_local.sv", "tb_native_local.sv"):
        bench = bundle / "design" / name
        if bench.is_file():
            anchor = "$readmemh(path,image,0,words-1);"
            text = bench.read_text()
            if anchor not in text:
                raise ValueError(f"image check missing from {name}")
            bench.write_text(text.replace(anchor, anchor +
                '\n        if (image[0][64+:16]!=2) $fatal(1,"expected compact image");'))


def native_lc(bundle):
    def include(text):
        return re.sub(r'`include "([^"]+)"',
                      lambda m: include((CORE / m[1]).read_text()), text)
    text = include((CORE / "lc_min_controller.sv").read_text())
    text = text.replace("module lc_min_controller #(parameter [7:0] BLOCK_ID = 0,",
                        "module pu_native_lc #(", 1)
    old = "parameter [7:0] NATIVE_BLOCK_TYPE = 0,\n                           parameter [31:0] NATIVE_TOPOLOGY = 0) ("
    if text.count(old) != 1:
        raise ValueError("native controller identity declaration changed")
    text = text.replace(old, "parameter [7:0] NATIVE_BLOCK_TYPE = 0) (\n"
                             "    input wire [7:0] block_id_i,\n"
                             "    input wire [31:0] topology_id_i,")
    text = re.sub(r"\bBLOCK_ID\b", "block_id_i", text)
    text = re.sub(r"\bNATIVE_TOPOLOGY\b", "topology_id_i", text)
    (bundle / "design/pu_native_lc.sv").write_text(text)
    wires = (CORE / "tb_network_lc_wires.svh").read_text()
    decl, inst = wires.split("lc_min_controller #", 1)
    (bundle / "design/pu_lc_wires.svh").write_text(decl)
    (bundle / "design/pu_legacy_lc.svh").write_text("lc_min_controller #" + inst)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("upstream213", type=Path)
    p.add_argument("upstream214", type=Path)
    p.add_argument("qualified", type=Path, help="immutable issue #193 acceptance-02 directory")
    p.add_argument("output", type=Path)
    args = p.parse_args()
    lock = json.loads((HERE / "upstream-lock.json").read_text())
    output = args.output.resolve()
    output.mkdir(exist_ok=False)
    for number, root in (("213", args.upstream213), ("214", args.upstream214)):
        verify(root, lock["dependencies"][number]["files"])
        shutil.copytree(root, output / ("dependency" + number))
    cfj = output / "dependency213"
    pu = output / "dependency214"
    qualified = args.qualified.resolve()
    archive = qualified / "bundle.tar.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != "3387aa6f05f5fdd658e0ce326fce70fd694200c1882a4a5941c4fa6ddafea281":
        raise ValueError("qualified source bundle changed")
    replay = pu / "project/experiments/pu_leaf_base/control_replay.py"
    text = replay.read_text()
    text, count = re.subn(r"^prior = Path\(.*$", "prior = Path(" + repr(str(qualified)) + ")",
                         text, count=1, flags=re.M)
    if count != 1:
        raise ValueError("qualified fixture path declaration changed")
    replay.write_text(text)
    controlled = replay.with_name("controlled.py")
    text, count = re.subn(r"^BASE = Path\(.*$", "BASE = Path(" + repr(str(qualified)) + ")",
                         controlled.read_text(), count=1, flags=re.M)
    if count != 1:
        raise ValueError("qualified controller path declaration changed")
    controlled.write_text(text)
    scripts = cfj / "project/experiments/cfj_leaf_base"
    for name in ("cfj", "duplex"):
        command(scripts / "stage_regression.py", archive, output / name, "controller")
        if name == "duplex":
            command(scripts / "stage_duplex.py", output / name)
        overlay(output / name)
    for kind in ("P", "U"):
        bundle = output / ("native-" + kind.lower())
        command(replay, pu, bundle, kind)
        overlay(bundle)
        native_lc(bundle)
    sources = {}
    for path in output.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            sources[path.relative_to(output).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / "source-sha256.json").write_text(json.dumps(sources, indent=2) + "\n")
    print(f"PASS staged {len(sources)} source files against current control")


if __name__ == "__main__":
    main()
