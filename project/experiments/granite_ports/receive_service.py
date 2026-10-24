"""Independent Issue76 packed-weight and finite Granite service receipts.

No producer or old-closure imports.  Actual packed/captured arrays are only
received on the authorized server; local tests use small synthetic blocks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from audit_io76 import (descriptor, load_json, need, replace_artifact_hash,
                        save_json, sha, source_binding, verify_manifest)


REVISION = "a02780686e08a03fe0d2679a293b5c74a90efa89"


def array_sha(value):
    value = np.ascontiguousarray(value)
    prefix = str(value.dtype).encode()+json.dumps(list(value.shape), separators=(",", ":")).encode()
    return hashlib.sha256(prefix+value.tobytes()).hexdigest()


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        result = {key: archive[key] for key in archive.files}
    need(all(x.dtype.kind != "O" for x in result.values()), "no object NPZ arrays")
    return result


def same(actual, expected, label):
    need(actual.dtype == expected.dtype and actual.shape == expected.shape and np.array_equal(actual, expected), label)


def restore_blocks(packed):
    """Check the documented address relation by explicit small block mapping."""
    p = np.asarray(packed)
    need(p.dtype == np.int8 and p.ndim == 5 and p.shape[-2:] == (16, 16), "typed packed W8 geometry")
    experts, oblocks, kblocks = p.shape[:3]
    restored = np.empty((experts, 16*oblocks, 16*kblocks), np.int8)
    for expert in range(experts):
        for output in range(oblocks):
            for inner in range(kblocks):
                restored[expert, 16*output:16*(output+1), 16*inner:16*(inner+1)] = p[expert, output, inner].T
    return restored


def verify_pack(packed, compiled, producer_source):
    packed, compiled = Path(packed), Path(compiled)
    manifest, artifacts = verify_manifest(packed, kind="granite-packed76-v1", statuses=("PACKED_NOT_EXECUTED",))
    cm, ca = verify_manifest(compiled, kind="granite-moe-compiled74-v1", statuses=("COMPILED_NOT_EXECUTED",))
    source_binding(manifest, {"service_sha256": producer_source})
    need(manifest["producer_sha256"] == sha(producer_source) and manifest["model_revision"] == cm["model_revision"] == REVISION
         and manifest["compiled_manifest_sha256"] == sha(compiled/"manifest.json") and manifest["layer"] in (0, 13),
         "packed source/current-layer/compiler/revision qualification")
    layer = manifest["layer"]
    layout = load_json(packed/"layout.json")
    need(layout["schema"] == "granite-packed-layout76-v1" and layout["layer"] == layer
         and layout["total_deployed_weight_bytes"] == 94371840 and layout["perlayer_scale_bytes"] == 614400
         and layout["matrix_physical_tile"] == {"O": 16, "K": 512, "bytes": 8192}
         and layout["M_effective_B1_PEs"] == 16, "one packed physical weight deployment")
    records = layout["arrays"]
    need(len(records) == 2 and {record["which"] for record in records} == {"gate_up", "down"}, "complete two packed matrices")
    indexed = {record["which"]: record for record in records}
    values = arrays(packed/"packed.npz")
    need(set(values) == {"gate_up_w8", "down_w8"}, "no hidden duplicate deployment arrays")
    checked, bytes_checked = 0, 0
    with np.load(compiled/"constants.npz", allow_pickle=False) as source:
        for name, shape in (("gate_up", (40, 1024, 1536)), ("down", (40, 1536, 512))):
            key = "L%d.%s_w8" % (layer, name)
            raw, p = source[key], values[name+"_w8"]
            need(raw.shape == shape and raw.dtype == np.int8 and p.shape == (40, shape[1]//16, shape[2]//16, 16, 16),
                 "all40 packed physical W8 shape")
            record = indexed[name]
            wanted = {"which": name, "source_key": key, "original_shape": list(shape), "packed_shape": list(p.shape),
                      "dtype": "int8", "bytes": p.nbytes, "original_array_sha256": array_sha(raw), "packed_array_sha256": array_sha(p)}
            need(record == wanted, "packed full-array metadata and compiler code binding")
            restored = restore_blocks(p)
            same(restored, raw, "packed actual W8 code/address mismatch")
            # The four-dimensional physical address is in bytes because W8.
            for expert, output, inner, ki, oi in ((0, 0, 0, 0, 0), (39, shape[1]//16-1, shape[2]//16-1, 15, 15)):
                address = expert*shape[1]*shape[2]+output*16*shape[2]+inner*256+ki*16+oi
                need(int(p.reshape(-1)[address]) == int(raw[expert, output*16+oi, inner*16+ki]), "packed boundary linear address")
            checked += raw.size
            bytes_checked += p.nbytes
    need(bytes_checked == 94371840, "single deployed packed weight byte count")
    return {"schema": "granite-packed-independent76-v1", "status": "PASS_PACK_CODES", "layer": layer,
            "producer_manifest": descriptor(packed/"manifest.json"), "compiled_manifest": descriptor(compiled/"manifest.json"),
            "artifacts": artifacts, "compiled_artifacts": ca, "W8_codes_checked": checked,
            "deployed_packed_weight_bytes": bytes_checked, "static_scale_bytes": 614400,
            "limits": ["Exact offline layout/inverse proof for already compiled W8, not service execution or model/RTL/PPA acceptance",
                       "Original scientific weights are provenance, not a second hardware EXT copy; inference IO remains payable"]}


def negative_pack(packed, compiled, producer_source, out):
    destination = Path(out)/"negative-packed-code"
    shutil.copytree(packed, destination)
    value = arrays(destination/"packed.npz")
    value["gate_up_w8"].flat[0] = int(value["gate_up_w8"].flat[0]) ^ 1
    np.savez_compressed(destination/"packed.npz", **value)
    layout = load_json(destination/"layout.json")
    next(record for record in layout["arrays"] if record["which"] == "gate_up")["packed_array_sha256"] = array_sha(value["gate_up_w8"])
    save_json(destination/"layout.json", layout)
    replace_artifact_hash(destination, "packed.npz")
    replace_artifact_hash(destination, "layout.json")
    verify_manifest(destination, statuses=("PACKED_NOT_EXECUTED",))
    try:
        verify_pack(destination, compiled, producer_source)
    except ValueError as error:
        need(str(error) == "packed actual W8 code/address mismatch", "packed negative must reach actual mathematical mapping")
        return {"status": "REJECTED_AFTER_SHA_REWRITE", "reason": str(error),
                "packed_artifact": descriptor(destination/"packed.npz")}
    raise ValueError("corrupted deployed W8 code accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack")
    for key in ("packed", "compiled", "producer-source", "binding", "out"):
        pack.add_argument("--"+key, type=Path, required=True)
    pack.add_argument("--skip-negatives", action="store_true")
    service = sub.add_parser("service")
    for key in ("run", "result", "compiled", "numeric-receipt", "packed", "packed-receipt", "calibration", "calibration-receipt", "producer-source", "binding", "out"):
        service.add_argument("--"+key, type=Path, required=True)
    service.add_argument("--skip-negatives", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    binding = load_json(args.binding)
    need(binding.get("receive_service_sha256") == sha(__file__)
         and binding.get("audit_io76_sha256") == sha(Path(__file__).with_name("audit_io76.py")), "independent source binding")
    if args.command == "pack":
        receipt = verify_pack(args.packed, args.compiled, args.producer_source)
        receipt["negative_tests"] = [] if args.skip_negatives else [negative_pack(args.packed, args.compiled, args.producer_source, args.out)]
    else:
        from finite_receive76 import finite_negatives, verify_finite
        for name in ("finite_receive76", "calendar76", "physical76", "rq_decoder76"):
            need(binding.get(name+"_sha256") == sha(Path(__file__).with_name(name+".py")), "independent finite helper binding "+name)
        try:
            receipt = verify_finite(args.run, args.result, args.compiled, args.numeric_receipt, args.packed, args.packed_receipt,
                                    args.calibration, args.calibration_receipt, args.producer_source)
            receipt["negative_tests"] = [] if args.skip_negatives else finite_negatives(args)
        except Exception as error:
            save_json(args.out/"failure.json", {"status": "REJECTED", "type": type(error).__name__, "reason": str(error), "source": binding})
            raise
    receipt["negative_status"] = "NOT_EXECUTED" if args.skip_negatives else "PASS_ACTUAL_SHA_REWRITE"
    receipt["source"] = binding
    save_json(args.out/"receipt.json", receipt)
    layer = receipt["layer"] if args.command == "pack" else receipt["config"]["layer"]
    print(receipt["status"], layer, flush=True)


if __name__ == "__main__":
    main()
