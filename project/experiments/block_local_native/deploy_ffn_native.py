"""Freeze the exact one-engine P profile and run a joint FFN test on c64."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile

HOST = "yuzelu@10.129.166.172"
P = "project/experiments/shared_x_control/"
N = "project/experiments/block_local_native/"
W = "project/rtl/w8a16_v1/"
S = "project/rtl/s_sram/"


def git(*cmd):
    return subprocess.check_output(["git", *cmd])


def package(output, commit, columns, w_provider, shared_dma, program):
    lock_path = P+{
        "legacy": "P_STREAM_ONE_ENGINE_SOURCE_LOCK.json",
        "serial": "P_STREAM_FOUR_W_SOURCE_LOCK.json",
        "four": "P_STREAM_FOUR_W_SOURCE_LOCK.json",
        "early": "P_STREAM_EARLY_EXEC_SOURCE_LOCK.json",
    }[w_provider]
    lock = json.loads(git("show", f"{commit}:{lock_path}"))
    items = {lock_path: git("show", f"{commit}:{lock_path}")}
    bank_sha = lock["source_sha256"]["accepted-bank/s_sram_256x128_freepdk45.v"]
    for file, expected in lock["source_sha256"].items():
        if file.startswith("accepted-bank/"):
            continue
        path = file if file.startswith("project/") else S+file.split("/")[-1]
        source = lock["M_candidate_commit"] if path.startswith(W) else commit
        raw = git("show", f"{source}:{path}")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"pinned P profile differs: {path}")
        items[path] = raw
    paths = [P+"native_s_lint.vlt", N+"real_s_lint.vlt", N+"job_ffn_native.sh",
        N+"p_scope128.json", N+"ffn_scope_emit.py", "project/rtl/block_local_native/p_stream_scope_node.sv"]
    if shared_dma:
        paths += ["project/rtl/mother_control_native/mc_dma_fabric_typed_p.sv",
                  "project/experiments/mother_control_native/typed_dma/DMA_TYPED_P.json"]
    if program:
        paths += [N+"ffn_program_emit.py", N+"ffn_program_control_fixture.sv", P+"make_lc_kernel.py", P+"p_program_lint.vlt"]
        paths += [P+"rtl/"+f+".sv" for f in ("lc_native_scope_controller", "lc_scope_fetch128", "lc_program_store_1k")]
        paths += ["project/experiments/mother_control_native/"+f for f in ("assemble_cases.py", "compile_scope_loops.py", "native_mc_lint.vlt")]
        paths += ["project/rtl/mother_control_native/"+f for f in (
            "mc_native_controller.sv", "mother_control_native64.sv", "mc_packet128_bridge.sv",
            "mother_control_native64_transport128.sv", "mc_native_ports.svh", "native_instruction_fetch.svh")]
        paths += ["project/rtl/mother_control_v1/control_pm.sv"]
    if columns:
        paths += [N+"test_ffn_native_p_node.sv", N+"test_ffn_three_p_native.sv", N+"make_ffn_native_vectors.py",
            "project/experiments/w8a16_g/reference.py", "project/experiments/w8a16_g/lut_q16.json",
            W+"g_s32.sv", W+"g_s128_frontend.sv"]
        paths += ["project/rtl/block_local_native/"+stem+".sv" for stem in (
            "s32_stripe_copy","ffn_gate_up_ring_control","ffn_gate_up_mid","ffn_stripe_commit","quant_mid_s128_router",
            "g_s128_observed_scale","native_s128_mux4")]
    for path in paths:
        items[path] = git("show", f"{commit}:{path}")
    items["source-commit.txt"] = (commit+"\n").encode()
    items["bank.sha256"] = (bank_sha+"\n").encode()
    manifest = "".join(hashlib.sha256(v).hexdigest()+"  "+p+"\n" for p,v in sorted(items.items()))
    with tarfile.open(output, "w:gz") as tar:
        for p, data in [(f"source/{p}", data) for p,data in items.items()]+[("source.sha256",manifest.encode())]:
            row = tarfile.TarInfo(p)
            row.size = len(data)
            row.mode = 0o755 if p.endswith(".sh") else 0o644
            tar.addfile(row, io.BytesIO(data))
    return len(items)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--package-dir", type=Path, required=True)
    p.add_argument("--columns", type=int, choices=(384,11008))
    p.add_argument("--down", action="store_true")
    p.add_argument("--w-provider", choices=("legacy", "serial", "four", "early"), default="legacy")
    p.add_argument("--shared-dma", action="store_true")
    p.add_argument("--program", action="store_true")
    p.add_argument("--split-up-channel", action="store_true")
    p.add_argument("--early-k-prep", action="store_true")
    p.add_argument("--partition", choices=("c64", "c96"), default="c64")
    a = p.parse_args()
    if a.down and a.columns != 11008:
        p.error("--down requires the complete 11008-column Mid")
    if a.shared_dma and a.columns is None:
        p.error("--shared-dma requires a functional fixture")
    if a.program and not a.shared_dma:
        p.error("--program requires --shared-dma for real LC descriptor reads")
    if a.early_k_prep and not a.program:
        p.error("--early-k-prep compares programmed FFN only")
    if a.split_up_channel and not a.shared_dma:
        p.error("--split-up-channel requires the actual dual-channel DMA")
    if not re.fullmatch(r"/public/home/yuzelu/project-circuit/issue250-ffnnative-[0-9]{8}-[0-9]{2}", a.root):
        raise ValueError("a fresh owned issue250-ffnnative root is required")
    a.package_dir.mkdir(parents=True, exist_ok=False)
    commit = git("rev-parse", "HEAD").decode().strip()
    archive = a.package_dir/"source.tar.gz"
    count = package(archive, commit, a.columns, a.w_provider, a.shared_dma, a.program)
    subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "mkdir "+shlex.quote(a.root)], check=True)
    subprocess.run(["scp", "-q", str(archive), HOST+":"+a.root+"/source.tar.gz"], check=True)
    cpus = 96 if a.partition == "c96" else 60
    cluster = "--partition=c96 --ntasks=8 --cpus-per-task=12 --time=00:12:00 " if a.partition == "c96" else ""
    result = subprocess.check_output(["ssh", "-o", "BatchMode=yes", HOST, "cd "+shlex.quote(a.root)+
        " && tar xzf source.tar.gz && sbatch "+cluster+"--output="+shlex.quote(a.root+"/slurm-%j.log")+" source/"+N+"job_ffn_native.sh"
        +f" {a.columns or 0} {int(a.down)} {int(a.w_provider in ('four','early'))} {int(a.shared_dma)} {int(a.program)}"
        +f" {int(a.split_up_channel)} {int(a.w_provider == 'early')} {int(a.early_k_prep)}"])
    record = dict(commit=commit, remote_root=a.root, files=count, columns=a.columns, down=a.down,w_provider=a.w_provider,
                  shared_dma=a.shared_dma, program=a.program, split_up_channel=a.split_up_channel, early_k_prep=a.early_k_prep, alloc_cpus=cpus,
                  package_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  submit=result.decode().strip())
    (a.package_dir/"submission.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
