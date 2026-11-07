"""Export the selected layer experiment and frozen native RTL inputs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DMA = "24e20d13a71cf65f721a182451308f1ad01ebaec"
CONTROL = "4f1a383049de5efa472f020e352c86be8c308614"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    commit = git("rev-parse", "HEAD").decode().strip()
    files = [(commit, path) for path in git("ls-tree", "-r", "--name-only", commit,
             "project/rtl/block_v2", "project/rtl/r_local_state").decode().splitlines()
             if path.endswith((".sv", ".svh"))]
    files.extend(((commit, "project/rtl/block_feed_v1/block_feed_s16k.sv"),
                  (DMA, "project/rtl/hbm_feed/hbm_group_dma.sv"),
                  (CONTROL, "project/experiments/control_v1/native_r_lint.vlt")))
    manifest = {}
    with tarfile.open(args.out / "rtl-source.tar", "w") as archive:
        for ref, name in files:
            data = git("show", ref + ":" + name)
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            entry.mode = 0o644
            archive.addfile(entry, io.BytesIO(data))
            manifest[name] = {"sha256": hashlib.sha256(data).hexdigest(), "ref": ref}
    for path in HERE.iterdir():
        if path.suffix in (".py", ".hpp", ".sv", ".sbatch", ".vlt") and path.name != Path(__file__).name:
            (args.out / path.name).write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    summary = ROOT / "work/huangpingyang04-lgtm/197/long/long-systemc-results.json"
    (args.out / summary.name).write_bytes(summary.read_bytes().replace(b"\r\n", b"\n"))
    (args.out / "rtl-source-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    for filename in ("upload.sha256", "run-upload.sha256"):
        paths = sorted(path for path in args.out.iterdir()
                       if path.is_file() and path.suffix not in (".sha256", ".md"))
        if filename == "run-upload.sha256":
            paths = [args.out / "run.sbatch", args.out / "verify.py"]
        text = "".join(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n" for path in paths)
        (args.out / filename).write_bytes(text.encode())
    print(args.out.resolve())

if __name__ == "__main__":
    main()
