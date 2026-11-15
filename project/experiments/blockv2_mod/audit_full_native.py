"""Relink each complete native graph archive to the Block V2 RTL contracts."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from image import pack_image
from resident_gather_contract import LINK_ABI, local_image, pack_u0_records
from resident_rms_contract import lower_record
from native_vocabulary_contract import lower_vocabulary


def checksum(data):
    return sha256(data).hexdigest()


def audit(archive, sidecar, profile_bytes, output):
    profile = json.loads(profile_bytes)
    target_routes = {
        (target["id"], route["schema"], route["abi"], route["opcode"], terminal)
        for target in profile["targets"] for route in target["routes"]
        if set(route["requires"]) <= set(profile["logical_interfaces"])
        for terminal in route["completions"]
    }
    with tarfile.open(archive) as package:
        def read(name):
            return package.extractfile("./" + name).read()
        graph = json.loads(read("scope.json"))
        stages = json.loads(read("stages.json"))
        if (graph["graph_sha256"] != stages["graph_sha256"]
                or graph["stage_proofs"] != [stage["proof_sha256"] for stage in stages["stages"]]
                or graph["native_pages"] != len(stages["stages"])):
            raise ValueError("archive scope differs from the sealed stage index")
        side = sidecar[graph["position"]]
        summaries = []
        issues = Counter()
        lowered = 0
        for stage in stages["stages"]:
            root = stage["root"]
            prefix = root if stage["bundle"] == "." else f"{root}/{stage['bundle']}"
            proof = read(root + "/proof.sha256")
            if checksum(proof) != stage["proof_sha256"]:
                raise ValueError(f"invalid stage seal: {root}")
            deployment = read(prefix + "/deployment.json")
            members = dict(line.split("  ", 1)[::-1] for line in proof.decode().splitlines())
            deployment_key = prefix.removeprefix(root).lstrip("/")
            deployment_key = f"{deployment_key}/deployment.json" if deployment_key else "deployment.json"
            if checksum(deployment) != members[deployment_key]:
                raise ValueError(f"invalid deployment seal: {root}")
            calls = json.loads(deployment)["calls"]
            counts = Counter()
            for call in calls:
                counts[(call["target"], *call["service_signature"], call["required_completion"])] += 1
            if root == "embedding":
                prior = json.loads(read(root + "/compile.json"))
                command, = prior["outputs"]["program"]["locals"]["embedding"]
                if side["original_stage_proof"] != stage["proof_sha256"] or side["plan_sha256"] != prior["outputs"]["program"]["source"]["plan_sha256"]:
                    raise ValueError("gather source does not match sidecar")
                source = side["input_source"]
                kwargs = dict(image_id=1, pack_image=pack_image, prompt_address=source.get("address"),
                              retired_index={k: source[k] for k in ("word", "lane_offset")}
                              if source["kind"] == "previous_retired_token" else None)
                pm = local_image(command, topology=side["target_topology"], **kwargs)
                if len(calls) != 1 or checksum(pm) != side["pm_sha256"]:
                    raise ValueError("re-encoded Gather differs from the tested PM")
                (output / "u0-gather.pm").write_bytes(
                    local_image(command, topology=profile["topology_id"], **kwargs))
                counts = Counter({(3, 1, 0x01930001, 0x104, "destination_commit_ack"): 1})
            if root == "vocabulary":
                original = read(prefix + "/descriptors.bin")
                translated = bytearray()
                for i, call in enumerate(calls):
                    raw = original[i*128:(i+1)*128]
                    if checksum(raw) != call["sha256"]:
                        raise ValueError("vocabulary descriptor differs from sealed call")
                    translated.extend(lower_vocabulary(raw, step=graph["position"], topology=profile["topology_id"]))
                (output / "vocabulary-descriptors.bin").write_bytes(translated)
                counts = Counter((c["target"], c["service_signature"][0],
                                  c["service_signature"][1], 3, c["required_completion"]) for c in calls)
            if any(c["target"] == 3 for c in calls) and prefix != "embedding":
                descriptors = read(prefix + "/descriptors.bin")
                records = []
                for i, call in enumerate(calls):
                    raw = descriptors[128*i:128*(i+1)]
                    if checksum(raw) != call["sha256"]:
                        raise ValueError(f"invalid call descriptor seal: {root}/{i}")
                    translated = lower_record(call, raw, profile["topology_id"])
                    if translated is None:
                        continue
                    original = (call["target"], *call["service_signature"], call["required_completion"])
                    counts[original] -= 1
                    counts[(3, 1, LINK_ABI, translated[0], call["required_completion"])] += 1
                    records.append(translated)
                lowered += len(records)
                if records and len(records) == sum(c["target"] == 3 for c in calls):
                    # Save the U0 local program only when every U0 call has a lowering.
                    pm = pack_u0_records(records, topology=profile["topology_id"],
                                         image_id=1, pack_image=pack_image)
                    (output / ("u0-" + root.replace("/", "_") + ".pm")).write_bytes(pm)
            missing = {key: n for key, n in counts.items() if n and key not in target_routes}
            issues.update(missing)
            summaries.append({"stage": root, "calls": sum(counts.values()),
                              "unbound_calls": sum(missing.values())})
        assert graph["layers"] == 36 and len(summaries) == 291
        return {"scope": graph, "rtl_profile_sha256": checksum(profile_bytes),
                "calls": sum(s["calls"] for s in summaries),
                "u0_rms_and_ddr_calls_lowered": lowered,
                "unbound_signatures": [{"signature": k, "calls": n}
                                       for k, n in sorted(issues.items())],
                "first_unbound": next((s["stage"] for s in summaries if s["unbound_calls"]), None),
                "stages": summaries}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "sidecar", "profile", "output"):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    profile_bytes = args.profile.read_bytes()
    args.output.mkdir()
    report = audit(args.archive, json.loads(args.sidecar.read_text()),
                   profile_bytes, args.output)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print({k: report[k] for k in ("calls", "first_unbound")}, flush=True)
