"""Emit actual P scope128 descriptors for a fixed 2048×11008×2048 three-P FFN.

Inputs bind the real packed weight images and externally assigned task/RF
identity. This emitter does not enable an unsupported FFN opcode or produce a
standalone executable: the manifest names the join, scatter and K-window
events the outer controller must drive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

SCHEMA = Path(__file__).with_name("p_scope128.json")
RECORD_BYTES = 1088
K_TILE = 128
HIDDEN = 2048
MID = 11008
PS = 3
WORD_BYTES = 16
DESC_BYTES = 128


def require(condition, message):
    if not condition:
        raise ValueError(message)


def layout(k, n):
    return (k // K_TILE) * (n // 8) * RECORD_BYTES


def group_count(width, p):
    return (width // 8 + PS - 1 - p) // PS


def descriptors(spec):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    require(schema["length"] == DESC_BYTES and schema["byte_order"] == "little", "scope128 ABI")
    fields = {f["name"]: (f["offset"], f["bytes"]) for f in schema["fields"]}
    binary, rows, barriers = bytearray(), [], []
    weights = spec["packed_weights"]
    topology = spec["topology"]
    require(0 < topology < 2**32, "nonzero uint32 topology")
    generation, job, epoch = spec["scope_generation_job_epoch"]
    task_first = spec["first_local_sequence_by_p"]
    require(len(task_first) == PS and all(type(i) is int and 0 <= i < 2**32
                for i in [generation, job, epoch, *task_first]),
            "uint32 scope identity")
    require(generation != 0 and job != 0 and all(0 < s <= 2**32-64 for s in task_first),
            "scope identity range")
    next_sequence = list(task_first)
    x_id, x_version = spec["x_tensor_version"]
    mid_id, mid_version = spec["mid_tensor_version"]
    require(all(type(i) is int and 0 <= i < 2**32 for i in [x_id, x_version, mid_id, mid_version]),
            "uint32 tensor identity")
    require((x_id, x_version) != (mid_id, mid_version), "X and Mid require distinct identities")
    rf_bases = spec["rf_object_bases"]
    out_version = spec["output_version"]
    sequence = spec["record_sequence_base"]
    require(type(out_version) is int and 0 <= out_version < 2**32, "uint32 result version")
    require(type(sequence) is int and 0 <= sequence and sequence+66048 <= 2**32, "record sequence wrap")
    regions = []
    for name, k, n in (("gate", HIDDEN, MID), ("up", HIDDEN, MID), ("down", MID, HIDDEN)):
        w = weights[name]
        require(w["format"] == "W8A16_n8_k128_ordinary_1088_v1", "wrong packed format for "+name)
        require(w["bytes"] == layout(k, n), "wrong packed length for "+name)
        require(re.fullmatch("[0-9a-f]{64}", w["sha256"]) is not None, "missing packed image hash for "+name)
        base = w["base"]
        require(type(base) is int and 0 <= base and base % 64 == 0 and base+w["bytes"] < 2**48,
                "invalid 48-bit weight aperture for "+name)
        regions.append((base, base+w["bytes"], name))
        rfb = rf_bases[name]
        require(type(rfb) is int and 0 <= rfb <= 2**32-n//8, "RF object wrap for "+name)
    require(all(rf_bases[a]+n_a//8 <= rf_bases[b] or rf_bases[b]+n_b//8 <= rf_bases[a]
                for a, n_a, b, n_b in [("gate", MID, "up", MID), ("gate", MID, "down", HIDDEN),
                                         ("up", MID, "down", HIDDEN)]), "RF object ranges alias")
    desc_base = spec["descriptor_base"]
    require(type(desc_base) is int and 0 <= desc_base and desc_base % DESC_BYTES == 0 and
            desc_base+192*DESC_BYTES < 2**48, "invalid aligned descriptor region")
    regions.append((desc_base, desc_base+192*DESC_BYTES, "scope128"))
    ordered = sorted(regions)
    require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), "DDR regions overlap")

    def emit(p, phase, stripe, width, k, n, ops, input_id, outs):
        nonlocal sequence
        first = stripe + 8*p
        groups = group_count(width, p)
        ways = len(ops)
        count = groups*ways*(k//K_TILE)
        require(0 < groups*ways <= 16 and first+24*(groups-1) < n, "context or column bounds")
        require(all(b+groups*2 <= 256 or 896 <= b < b+groups*2 <= 928 for b in outs),
                "output outside its S lease")
        key = (((job << 32 | epoch) << 32 | input_id[0]) << 32) | input_id[1]
        d = bytearray(DESC_BYTES)

        def set_field(name, value):
            offset, size = fields[name]
            d[offset:offset+size] = int(value).to_bytes(size, "little")

        set_field("schema_abi", int(schema["schema_abi"], 16))
        set_field("provider_abi", int(schema["provider_abi"], 16))
        for name, value in {
            "length": DESC_BYTES, "service": 2, "topology": topology, "input_key": key,
            "output_version": out_version, "record_sequence_base": sequence, "columns": n,
            "first_column": first, "column_stride": 24, "groups": groups, "full_k": k, "k_end": k,
            "ways": ways, "input_s_base": 880, "scratch_s_base": 928, "snapshot_s_base": 960,
        }.items():
            set_field(name, value)
        for way, op in enumerate(ops):
            set_field("rf_object_base"+str(way), rf_bases[op])
            set_field("weight_base"+str(way), weights[op]["base"])
            set_field("output_s_base"+str(way), outs[way])
        set_field("crc32", zlib.crc32(d[:124]))
        index = len(rows)
        rows.append(dict(index=index, address=desc_base+index*DESC_BYTES, p=p, phase=phase,
            scope_owner=[generation, job, epoch, next_sequence[p]], input_key=[job, epoch, *input_id],
            stripe_first=stripe, stripe_width=width, first_column=first, column_stride=24,
            groups=groups, ways=ways, k=k, record_sequence=sequence, records=count,
            committed_words_per_way=groups*2, output_s_word_by_way=list(outs), sha256=hashlib.sha256(d).hexdigest()))
        binary.extend(d)
        sequence += count
        next_sequence[p] += 1
        return index

    for stripe in range(0, MID, 192):
        width = min(192, MID-stripe)
        indices = [emit(p, "gate_up", stripe, width, HIDDEN, MID, ("gate", "up"), (x_id, x_version),
                        (896, 912)) for p in range(PS)]
        barriers.append(dict(phase="gate_up", scope_indices=indices, stripe_first=stripe, stripe_width=width,
            on_success=["all_three_final_SACK", "six_fragment_COPY_SACK", "G32_SILU", "Mid_quantize_SACK"]))
    out_cursor = [0]*PS
    for stripe in range(0, HIDDEN, 384):
        width = min(384, HIDDEN-stripe)
        indices = [emit(p, "down", stripe, width, MID, HIDDEN, ("down",), (mid_id, mid_version),
                        (out_cursor[p],)) for p in range(PS)]
        barriers.append(dict(phase="down", scope_indices=indices, stripe_first=stripe, stripe_width=width,
            on_success=["all_three_final_SACK", "down_columns_ready_for_scatter"]))
        for p in range(PS):
            out_cursor[p] += group_count(width,p)*2
    require(len(rows) == 192 and sequence-spec["record_sequence_base"] == 66048 and
            next_sequence == [s+64 for s in task_first] and
            out_cursor == [172, 170, 170], "incomplete schedule")
    manifest = dict(schema="issue250-three-P-ffn-scope-bundle/1", topology=topology,
        descriptor_base=desc_base, descriptor_count=len(rows), descriptor_bytes=len(binary),
        descriptor_sha256=hashlib.sha256(binary).hexdigest(), packed_weights=weights,
        packed_weights_verified=False, scopes=rows, barriers=barriers, dataflow=dict(
            X="Existing U.S 256-word A16 window, with real per-K128 shift or quant/COPY on demand",
            gate_up="P scratch896/912; P0 gather to existing ring720/784",
            mid_tiles=[dict(k_begin=k*K_TILE, p=k%PS, s_word=256+16*(k//PS)) for k in range(MID//K_TILE)],
            down="Each P uses one active 16-word A16 window at880, loaded from the Mid owner with real shift/ACK",
            down_result_words_per_p=out_cursor, active_S_bytes_per_P=16384, added_SRAM_bytes=0),
        requires="Bound actual packed DDR, all three scope terminals, explicit per-tile S and shift leases, and outer controller",
        standalone_program=False, production_qualified=False)
    return bytes(binary), manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    binary, manifest = descriptors(json.loads(args.binding.read_text(encoding="utf-8")))
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/"scopes.bin").write_bytes(binary)
    (args.out/"scopes.mem").write_text("".join(f"{int.from_bytes(binary[i:i+DESC_BYTES], 'little'):0256x}\n"
        for i in range(0,len(binary),DESC_BYTES)), encoding="ascii")
    (args.out/"scopes.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("scopes","barriers","dataflow")}))


if __name__ == "__main__":
    main()
