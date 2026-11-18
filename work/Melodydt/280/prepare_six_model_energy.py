"""Prepare an isolated, hash-verified frozen-plan runtime and read-only probes."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil


def file_hash(path):
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def patch(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError("unexpected frozen source anchor in {}: {}".format(path, old[:80]))
    path.write_text(text.replace(old, new))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    p.add_argument("model")
    p.add_argument("out", type=Path)
    p.add_argument("shared", type=Path)
    a = p.parse_args()
    receipt = json.loads((a.bundle / (a.model + "-transfer.json")).read_text())
    for item in receipt["files"]:
        path = Path(item["source"])
        if path.stat().st_size != item["bytes"] or file_hash(path) != item["sha256"]:
            raise ValueError("destination hash verification failed: " + str(path))
    runner = a.out / "runner"
    runner.mkdir(parents=True)
    src = Path(receipt["source_root"])
    for path in src.iterdir():
        if path.suffix in (".py", ".cpp"):
            shutil.copy2(str(path), str(runner / path.name))
    # The frozen compiler is intentionally not invoked. Disable checkpoint-only
    # imports on the Python 3.6 replay host; fail if somebody tries to compile.
    for name in ("llama_short_plan.py", "phi_short_plan.py", "gemma_short_plan.py"):
        path = runner / name
        if path.exists() and "from safetensors import safe_open" in path.read_text():
            patch(path, "from safetensors import safe_open", "def safe_open(*args, **kwargs):\n    raise RuntimeError('frozen-plan replay must not access checkpoints')")
    history = runner / "live_history.py"
    patch(history, "from hashlib import file_digest, sha256", "from hashlib import sha256")
    for name in ("fast_tlm_replay.py",):
        shutil.copy2(str(a.shared / "runner" / name), str(runner / name))
    native = Path("/public/home/yuzelu/project-circuit/issue260-native-sram512-SMbOWTw6/native_tlm_projection.py")
    shutil.copy2(str(native), str(runner / native.name))
    for filename, callback in (("pr272_native_projection.py", "m_group"), (native.name, "native_m_group")):
        path = runner / filename
        anchor = "self.edge(finish_group, 8 + 8 * (8 if head16 else 1))"
        text = path.read_text()
        if text.count(anchor) != 1:
            raise ValueError("projection timing anchor mismatch: " + filename)
        line = next(line for line in text.splitlines() if anchor in line)
        indent = line[:len(line) - len(line.lstrip())]
        patch(path, line, indent + "cycles = 8 + 8 * (8 if head16 else 1)\n" + indent +
              "self.target.component_observation.{}(self.target, self.clock.now, cycles)\n".format(callback) +
              indent + "self.edge(finish_group, cycles)")
    model = runner / "qwen3_short.py"
    patch(model, '        addr = self.plan["local"]["address"]',
          '        self.dram.capture_energy("start")\n        addr = self.plan["local"]["address"]')
    patch(model, '            residual = self.read(U, 0, self.hidden//4)',
          '            if not decode and step == 1:\n                self.dram.capture_energy("prefill_end")\n            residual = self.read(U, 0, self.hidden//4)')
    patch(model, '            (self.output / "progress.json").write_text(',
          '                self.dram.capture_energy(f"retire_{step+1}")\n            (self.output / "progress.json").write_text(')
    patch(model, '        self.dram.close()', '        self.dram.capture_energy("end")\n        self.dram.close()')
    patch(model, '            arith = self.e[site]\n\n            def begin(done):',
          '            arith = self.e[site]\n\n            def begin(done):\n                self.energy_observation.activation(site, words, gelu, sigmoid, scaled)')
    for filename in ("qwen3_component_observation.py", "six_model_observation.py", "run_frozen_model_energy.py", "qwen3_dma_windows.py", "ddr_window_energy.py"):
        shutil.copy2(str(a.bundle / filename), str(runner / filename))
    pre = json.loads((Path(receipt["baseline"]["prefill"]) / "result.json").read_text())
    dec = json.loads((Path(receipt["baseline"]["decode"]) / "result.json").read_text())
    first, second = [x["time_ps"] for x in dec["retirements"]]
    windows = {"prefill": {"start_ps": 0, "end_ps": pre["interval_ps"]},
               "first_token": {"start_ps": 0, "end_ps": first},
               "decode": {"start_ps": first, "end_ps": second}}
    (a.out / "qualified-windows.json").write_text(json.dumps(windows, indent=2) + "\n")
    (a.out / "transfer-verified.json").write_text(json.dumps({"model": a.model, "files": len(receipt["files"]),
        "receipt_sha256": file_hash(a.bundle / (a.model + "-transfer.json")), "baseline": receipt["baseline"]}, indent=2) + "\n")
    hashes = {path.name: file_hash(path) for path in sorted(runner.iterdir()) if path.is_file()}
    (a.out / "instrumented-source.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print("FROZEN_INPUTS_AND_PROBES_PREPARED", a.model, len(receipt["files"]), flush=True)


if __name__ == "__main__":
    main()
