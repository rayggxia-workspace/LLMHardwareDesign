"""Issue72 independent artifact validation; no producer imports."""
import hashlib
import json
from pathlib import Path
import re


def need(condition, label):
    if not condition:
        raise ValueError(label)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def descriptor(path):
    return {"bytes": Path(path).stat().st_size, "sha256": sha(path)}


def child(root, relative):
    need(isinstance(relative, str) and relative and "\\" not in relative
         and ":" not in relative and not Path(relative).is_absolute(), "artifact path")
    root = Path(root).resolve()
    result = (root / relative).resolve()
    need(result != root and result.is_relative_to(root), "artifact escape")
    return result


def verify_manifest(folder, *, kind=None, statuses=()):
    root = Path(folder)
    value = load_json(root / "manifest.json")
    if kind:
        need(value.get("kind") == kind, "manifest kind")
    if statuses:
        need(value.get("status") in statuses, "manifest execution status")
    artifacts = value.get("artifacts")
    if isinstance(artifacts, list):
        names = [entry["path"] for entry in artifacts]
        need(len(set(names)) == len(names), "duplicate artifact")
        entries = dict(zip(names, artifacts))
    else:
        need(isinstance(artifacts, dict), "artifact index")
        entries = artifacts
    need(len(entries) > 0, "empty artifact index")
    checked = {}
    for name, wanted in entries.items():
        need(re.fullmatch("[0-9a-f]{64}", wanted.get("sha256", "")) is not None,
             "artifact SHA format")
        actual = descriptor(child(root, name))
        need(actual == {k: wanted[k] for k in ("bytes", "sha256")}, "artifact hash/size " + name)
        checked[name] = actual
    return value, checked


def check_source(manifest, producer_source, source_field):
    wanted = sha(producer_source)
    binding = manifest.get("source", {})
    need(re.fullmatch("[0-9a-f]{40}", binding.get("commit", "")) is not None,
         "producer commit")
    need(binding.get(source_field) == wanted and manifest.get("producer_sha256") == wanted,
         "producer source SHA binding")
    return wanted


def replace_artifact_hash(folder, name):
    """Only for explicit semantic negative tests, after an actual disk mutation."""
    root = Path(folder)
    value = load_json(root / "manifest.json")
    record = descriptor(child(root, name))
    entries = value["artifacts"]
    if isinstance(entries, list):
        found = [x for x in entries if x["path"] == name]
        need(len(found) == 1, "negative artifact membership")
        found[0].update(record)
    else:
        need(name in entries, "negative artifact membership")
        entries[name].update(record)
    save_json(root / "manifest.json", value)
