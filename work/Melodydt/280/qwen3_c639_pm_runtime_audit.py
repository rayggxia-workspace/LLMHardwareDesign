"""Check runtime local program-memory transactions in frozen C639 capture windows."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess


PORTS = {name: 1 for name in (
    "clk", "reset", "pm_valid", "pm_ready", "pm_rsp_valid", "pm_rsp_ready", "pm_error"
)}
PORTS["pm_address"] = 14
PHASES = ("gate-up", "down", "writer-active")


def digest(path):
    result = sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(data)
    return result.hexdigest()


def count(path, scope):
    result = Counter(rising_edges=0, requests=0, responses=0, errors=0)
    addresses = Counter()
    ids, names, levels, updates, stack = {}, set(), {}, {}, []
    first_pending = None

    def edge():
        nonlocal first_pending
        if levels.get("clk") == 0 and updates.get("clk") == 1:
            if set(levels) != set(PORTS) or levels["reset"]:
                raise ValueError("reset or incomplete sample at clock edge: {}".format(scope))
            if first_pending is None:
                first_pending = levels["pm_rsp_valid"]
            result["rising_edges"] += 1
            if levels["pm_valid"] and levels["pm_ready"]:
                result["requests"] += 1
                address = levels["pm_address"]
                if address % 16:
                    raise ValueError("unaligned PM read {} in {}".format(address, scope))
                addresses[address] += 1
            if levels["pm_rsp_valid"] and levels["pm_rsp_ready"]:
                result["responses"] += 1
                result["errors"] += levels["pm_error"]
        levels.update(updates)
        updates.clear()

    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ["$scope"]:
                stack.append(fields[2])
            elif fields[:1] == ["$upscope"]:
                stack.pop()
            elif fields[:1] == ["$var"] and "/".join(stack) == scope:
                name = fields[4]
                if name in PORTS:
                    if int(fields[2]) != PORTS[name] or name in names:
                        raise ValueError("incorrect PM port declaration: {}/{}".format(scope, name))
                    ids.setdefault(fields[3], []).append(name)
                    names.add(name)
            elif fields[:1] == ["$enddefinitions"]:
                break
        if names != set(PORTS):
            raise ValueError("PM boundary {} missing {}".format(scope, sorted(set(PORTS) - names)))
        for line in stream:
            if line.startswith("#"):
                edge()
                continue
            if line[:1] in {"0", "1", "x", "z", "X", "Z"}:
                value, key = line[0], line[1:].strip()
            elif line[:1] in {"b", "B"}:
                value, key = line[1:].split()
            else:
                continue
            for name in ids.get(key, ()):
                if set(value) - {"0", "1"}:
                    raise ValueError("unknown PM value: {}/{}".format(scope, name))
                updates[name] = int(value, 2)
        edge()

    final_pending = levels.get("pm_rsp_valid")
    if (result["rising_edges"] != 8192 or result["errors"] or
            result["requests"] + first_pending - result["responses"] != final_pending):
        raise ValueError("PM request/response audit failed: {}/{}".format(scope, dict(result)))
    row = dict(result, pending_at_start=first_pending, pending_at_end=final_pending)
    row["requests_by_address_bytes"] = dict(sorted(addresses.items()))
    return row


def audit(replay, converter, activity, out, workers):
    manifest = json.loads(activity.read_text(encoding="utf-8"))
    inputs = {str(path): digest(path) for path in (activity, converter)}
    windows = {}
    samples = []
    for mode in (0, 1):
        for phase in PHASES:
            window = "mode-{}-{}".format(mode, phase)
            wave = replay / "DDR-{}".format(mode) / "ffn-{}.fst".format(phase)
            inputs[str(wave)] = digest(wave)
            if inputs[str(wave)] != manifest["windows"][window]["fst_sha256"]:
                raise ValueError("source activity hash differs: {}".format(wave))
            windows[window] = {}
            for site in range(4):
                scope = manifest["scopes"]["local_controller_{}".format(site)] + "/pm"
                samples.append((window, site, wave, scope))

    def sample(item):
        window, site, wave, scope = item
        vcd = out / "pm-runtime-{}-{}.tmp.vcd".format(window, site)
        subprocess.run([str(converter), str(wave), str(vcd), scope], check=True,
                       stdout=subprocess.DEVNULL)
        row = count(vcd, scope)
        vcd.unlink()
        return window, site, dict(row, scope=scope)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for window, site, row in pool.map(sample, samples):
            windows[window][str(site)] = row
    with (out / "pm-runtime-audit.json").open("x", encoding="utf-8") as stream:
        json.dump({"inputs_sha256": inputs, "windows": windows}, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("replay", "converter", "activity", "out"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    audit(args.replay, args.converter, args.activity, args.out, args.workers)


if __name__ == "__main__":
    main()
