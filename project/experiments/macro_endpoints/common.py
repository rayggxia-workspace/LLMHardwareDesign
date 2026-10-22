"""Evidence helpers shared by capture, interpretation, and read-back."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONFIG = HERE / "inputs.json"
ALLOWED_ROOT = "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06"
EXACT_PATHS = {
    "ACT20": "act-cap20/flow/results/nangate45/parallel_opentpu_act/base/llhd_opentpu_act.lef",
    "MXU20": "mxu-cap20/flow/results/nangate45/parallel_opentpu_mxu/base/llhd_opentpu_mxu.lef",
    "GEMM20": "gemm-cap20/flow/results/nangate45/parallel_llaccel_gemm/base/gemm_engine.lef"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def check_config(cfg):
    if (cfg.get("schema") != 1 or cfg.get("input_version") != "wave2-06-ordinary-lef-snapshot-v1"
            or cfg.get("parser_profile") != "lef58-single-macro-rect-v1" or cfg.get("allowed_root") != ALLOWED_ROOT
            or cfg.get("ssh_host") != "yuzelu@10.129.166.172"):
        raise ValueError("configuration differs from the declared Issue16 capture scope")
    items = cfg["files"]
    if len(items) != 3 or {x["id"]: x["relative_path"] for x in items} != EXACT_PATHS:
        raise ValueError("only the three declared ordinary LEF files may be captured")
    if cfg["limits"] != {"max_bytes_per_lef": 2000000, "expected_dbu_per_micron": 2000}:
        raise ValueError("unexpected capture limits")
    for item in items:
        if item["qualified_hard_macro"] is not False:
            raise ValueError("this study does not qualify any hard macro")
    return cfg


def clean_provenance(names):
    dirty = git("status", "--porcelain")
    if dirty:
        raise RuntimeError("commit source/config before a formal capture or export: " + dirty)
    return {"source_commit": git("rev-parse", "HEAD"), "source_dirty": False,
            "source_sha256": {(HERE / name).relative_to(ROOT).as_posix(): sha((HERE / name).read_bytes())
                              for name in names},
            "python": sys.version, "platform": platform.platform(),
            "task_temporary_directory": os.environ.get("TEMP"),
            "python_cache_prefix": sys.pycache_prefix}


def verify_provenance(record, require_current):
    if record["source_dirty"]:
        raise AssertionError("dirty code cannot be promoted to formal evidence")
    for name, expected in record["source_sha256"].items():
        source = (ROOT / name).resolve()
        if not source.is_relative_to(ROOT):
            raise AssertionError("source path escapes project")
        committed = subprocess.check_output(["git", "show", record["source_commit"] + ":" + name], cwd=ROOT)
        if sha(committed) != expected or (require_current and sha(source.read_bytes()) != expected):
            raise AssertionError("source version/hash mismatch: " + name)


def verify_index(folder, index, manifest_name):
    folder = Path(folder).resolve()
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if actual != {*index, manifest_name}:
        raise AssertionError("unindexed or missing file")
    for name, info in index.items():
        relative = PurePosixPath(name)
        path = (folder / name).resolve()
        if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(folder):
            raise AssertionError("unsafe evidence path")
        data = path.read_bytes()
        if len(data) != info["bytes"] or sha(data) != info["sha256"]:
            raise AssertionError("input/output bytes or SHA-256 changed: " + name)


def file_index(folder):
    return {p.relative_to(folder).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
            for p in sorted(Path(folder).rglob("*")) if p.is_file()}


def check_observation(cfg, item, observed, info):
    expected_path = cfg["allowed_root"] + "/" + item["relative_path"]
    resolved = PurePosixPath(observed["resolved_path"])
    if (observed["requested_path"] != expected_path or not resolved.is_absolute()
            or ".." in resolved.parts or not str(resolved).startswith(cfg["allowed_root"] + "/")
            or observed["sha256"] != info["sha256"] or observed["bytes"] != info["bytes"]):
        raise AssertionError("source observation does not match declared path/frozen bytes")
    stamp = observed["stat_before"]
    if (stamp != observed["stat_after"] or len(stamp) != 4
            or any(type(x) is not int or x < 0 for x in stamp) or stamp[2] != info["bytes"]):
        raise AssertionError("source was unstable or its stat size differs from frozen bytes")
    if info["bytes"] != item["previous_observed_bytes"] or info["bytes"] > cfg["limits"]["max_bytes_per_lef"]:
        raise AssertionError("source size differs from the declared capture observation/limit")
    if item["upstream_expected_sha256"] is not None and info["sha256"] != item["upstream_expected_sha256"]:
        raise AssertionError("upstream file hash mismatch")


def load_snapshot(folder, check_code=True):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / "capture.json").read_bytes())
    verify_index(folder, manifest["files"], "capture.json")
    cfg_bytes = (folder / "inputs.json").read_bytes()
    cfg = check_config(json.loads(cfg_bytes))
    if manifest["remote_user"] != "yuzelu" or manifest["ssh_host"] != cfg["ssh_host"]:
        raise AssertionError("capture login/host differs from declared source")
    if sha(cfg_bytes) != manifest["config_sha256"]:
        raise AssertionError("capture configuration hash mismatch")
    config_source = (HERE / "inputs.json").relative_to(ROOT).as_posix()
    if (manifest["input_version"] != cfg["input_version"] or manifest["upstream"] != cfg["upstream"]
            or manifest["provenance"]["source_sha256"].get(config_source) != sha(cfg_bytes)):
        raise AssertionError("capture configuration is not from its declared code snapshot")
    if set(manifest["files"]) != {"inputs.json", *(x["id"] + ".lef" for x in cfg["files"])}:
        raise AssertionError("capture is not the declared three-file snapshot")
    if check_code:
        expected = {(HERE / n).relative_to(ROOT).as_posix() for n in ("common.py", "capture.py", "inputs.json")}
        if set(manifest["provenance"]["source_sha256"]) != expected:
            raise AssertionError("incomplete capture code provenance")
        verify_provenance(manifest["provenance"], require_current=False)
    if len(manifest["observations"]) != 3:
        raise AssertionError("missing source observation")
    by_id = {x["id"]: x for x in manifest["observations"]}
    for item in cfg["files"]:
        name = item["id"] + ".lef"
        info, observed = manifest["files"][name], by_id[item["id"]]
        check_observation(cfg, item, observed, info)
    return cfg, manifest
