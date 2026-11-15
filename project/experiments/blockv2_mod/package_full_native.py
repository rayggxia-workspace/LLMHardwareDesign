"""Diagnostic repackaging of archived stages; not whole-graph compilation."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tarfile
import struct

from native_vocabulary_contract import lower_vocabulary
from resident_rms_contract import lower_record


def digest(data):
    return sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def package(archive, audit_dir, replan_dir, output):
    audit = json.loads((audit_dir / "report.json").read_text())
    replan = json.loads((replan_dir / "report.json").read_text())
    profile_bytes = Path("algo1/blockv2-mod.json").read_bytes()
    profile = json.loads(profile_bytes)
    if audit["unbound_signatures"] or audit["rtl_profile_sha256"] != digest(profile_bytes):
        raise ValueError("the complete plan is not bound to the current RTL profile")
    if replan["status"] != "all_stages_replanned" or len(replan["stages"]) != 291:
        raise ValueError("full Algo1 replan missing")
    for name, expected in profile["rtl_sources_sha256"].items():
        if digest(Path("rtl", name).read_bytes()) != expected:
            raise ValueError("RTL changed after dispatch admission: " + name)
    output.mkdir()
    (output / "rtl-profile.json").write_bytes(profile_bytes)
    index = []
    with tarfile.open(archive) as source:
        def read(name):
            return source.extractfile("./" + name).read()
        stages = json.loads(read("stages.json"))
        if [s["root"] for s in stages["stages"]] != [s["stage"] for s in replan["stages"]]:
            raise ValueError("replanned stage order differs")
        for stage in stages["stages"]:
            root = stage["root"]
            prefix = root if stage["bundle"] == "." else root + "/" + stage["bundle"]
            deployment = json.loads(read(prefix + "/deployment.json"))
            dest = output / root
            dest.mkdir(parents=True)
            payloads = {}
            for name, seal in deployment["payloads"].items():
                raw = read(prefix + "/" + name)
                if len(raw) != seal["bytes"] or digest(raw) != seal["sha256"]:
                    raise ValueError("invalid payload " + prefix + "/" + name)
                payloads[name] = raw
            result = json.loads((replan_dir / root / "algo1-result.json").read_text())
            calls = deepcopy(deployment["calls"])
            adapter = None
            u_calls = [c for c in calls if c["target"] == 3]
            if u_calls:
                pm_name = "u0-gather.pm" if root == "embedding" else "u0-" + root.replace("/", "_") + ".pm"
                pm = (audit_dir / pm_name).read_bytes()
                local_name = deployment["local_images"][u_calls[0]["group"]]
                native_header = struct.unpack("<32I", payloads[local_name][:128])
                if native_header[14] != 1 or native_header[15] != profile["topology_id"]:
                    raise ValueError("unsupported native image binding")
                payloads[local_name] = pm
                adapter = {
                    "module": "mc_lc_legacy_v1_records", "target": 3,
                    "legacy_image": 1, "legacy_topology": profile["topology_id"],
                    "native_image": native_header[14],
                    "native_topology": native_header[15],
                    "native_generation": audit["scope"]["first_generation"] + len(index),
                    "local_format": "control_image_v0_1 local instruction version 2",
                }
                for original, call in enumerate(calls):
                    if call["target"] != 3:
                        continue
                    call["encoding_location"] = local_name
                    call.pop("address", None)
                    if root != "embedding":
                        raw = payloads["descriptors.bin"][128*original:128*(original+1)]
                        opcode, _ = lower_record(call, raw, profile["topology_id"])
                        call["service_signature"] = [1, 0x01930001, opcode]
                    else:
                        call["service_signature"] = [1, 0x01930001, 0x104]
                    call.pop("sha256", None)
            if root == "vocabulary":
                raw = payloads["descriptors.bin"]
                translated = b"".join(lower_vocabulary(raw[i:i+128],
                    step=audit["scope"]["position"], topology=profile["topology_id"])
                    for i in range(0, len(raw), 128))
                if translated != (audit_dir / "vocabulary-descriptors.bin").read_bytes():
                    raise ValueError("vocabulary lowering differs from admission")
                payloads["descriptors.bin"] = translated
                for i, call in enumerate(calls):
                    call["service_signature"][2] = 3
                    call["sha256"] = digest(translated[i*128:(i+1)*128])
            for name, raw in payloads.items():
                (dest / name).write_bytes(raw)
            dump(dest / "program.json", result["outputs"]["program"])
            receipt = {
                "source_deployment": deployment["source"],
                "algo1_program_sha256": digest(json.dumps(result["outputs"]["program"],sort_keys=True).encode()),
                "rtl_profile_sha256": digest(profile_bytes), "calls": calls,
                "local_images": deployment["local_images"], "adapter": adapter,
                "payloads": {name: {"bytes":len(raw),"sha256":digest(raw)} for name,raw in payloads.items()},
            }
            dump(dest / "deployment.json", receipt)
            index.append({"stage":root, "generation":audit["scope"]["first_generation"] + len(index),
                          "calls":len(calls), "deployment_sha256":digest((dest / "deployment.json").read_bytes())})
    dump(output / "manifest.json", {
        "status":"archived_stage_diagnostic_generated", "scope":audit["scope"],
        "whole_graph_compilation":False, "delivery_accepted":False,
        "machine_code_origin":"sealed archive with explicit U0/vocabulary translations",
        "connectivity_origin":"sealed archive",
        "rtl_profile_sha256":digest(profile_bytes), "stages":index,
        "replanned_tasks":sum(s["tasks"] for s in replan["stages"]),
        "unbound_native_calls":0,
    })


if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("archive","audit","replan","output"):
        cli.add_argument(name,type=Path)
    args=cli.parse_args()
    package(args.archive,args.audit,args.replan,args.output)
