"""Count sealed Algo1 work and bound its serial-KV decode time without a trace."""

import argparse
from collections import Counter
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import sys
from time import perf_counter


DEPLOYMENT = "74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef"
SOURCE_MANIFEST = "1bf5465dc4a4bbb8e4618502e1fe5a591d1c2c9fdc8b20cf84d5ea7d198e2a33"
DEPENDENCY_HASHES = {
    "systemc_benchmark/native_rtl_retirements.py": "601134bdb862045dd3002abe615284c5501deb36c064175fd84eb29bd2ac5837",
    "systemc_benchmark/prepare_native_whole_request.py": "4b763d1dcb22840f70c11e81447591715369b8f37b7febdbdecc353949d870ef",
    "block_local_native/native_program_runtime.py": "7ed0eb23bbba07aabad7c257a4ba1f1e1dca09e8cca15768adfdf78e9e8b613b",
}
CORE_PS = 3334
DDR_PS = 630
BURST_BYTES = 64
BURST_TICKS = 4
READ_TICKS = 22 + BURST_TICKS
P_SCOPE = int.from_bytes(b"\x01PP\x02", "little")
ATT1 = int.from_bytes(b"ATT1", "little")
KVR1 = int.from_bytes(b"KVR1", "little")
OTHER_SCHEMAS = {3, *(int.from_bytes(name, "little") for name in
                     (b"DRL1", b"DRL8", b"DWS1", b"DWS8", b"RPE1", b"FDS8"))}
DECODER_SOURCES = ("export_tlm_mother_program.py", "replay_tlm_mother.py", "native_tlm_local.py")
BOUND_SOURCES = ("native_tlm_projection.py", "native_tlm_attention.py", "native_tlm_timing.py",
                 "native_tlm_dma.py", "run_native_tlm_request.py")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    checksum = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def seal(root, name, expected):
    path = root / name
    require(digest(path) == expected, f"invalid seal for {name}")
    result = {}
    for line in path.read_text(encoding="ascii").splitlines():
        checksum, member = line.split("  ", 1)
        require(member not in result and not Path(member).is_absolute() and ".." not in Path(member).parts,
                f"invalid sealed path {member}")
        result[member] = checksum
    return result


def verify(root, member, expected):
    path = root / member
    require(digest(path) == expected, f"{member} does not match its seal")
    return path


@lru_cache(maxsize=None)
def weight_geometry(weight0, weight1, columns, first, stride, groups, context, full_k, k0, k1, ways, head):
    require(ways in (1, 2) and head in (0, 1) and first % 8 == 0 and stride % 8 == 0 and stride >= 8 and
            1 <= groups <= 16 and context + groups * ways <= 16 and first + (groups - 1) * stride < columns and
            full_k > 0 and full_k % 128 == 0 and k0 == 0 and k1 == full_k and (ways == 2 or not weight1),
            "unsupported sealed projection geometry")
    tiles = full_k // 128
    record_bytes = 1152 if head else 1088
    count = [0, 0]
    for base in (weight0, weight1)[:ways]:
        require(base % BURST_BYTES == 0, "unaligned weight base")
        for group in range(groups):
            index = ((first + group * stride) // 8) * tiles
            for tile in range(tiles):
                address = base + (index + tile) * record_bytes
                count[(address >> 11) & 1] += record_bytes // BURST_BYTES
    return count, full_k * groups * ways * 8


def phase_inventory(phases, descriptors, ingress_file):
    require(len(phases) == 128 and [x["step"] for x in phases] == list(range(128)), "unexpected phase sequence")
    ingress_count, *rows = ingress_file.read_text(encoding="ascii").splitlines()
    ingress = [tuple(int(word, 16) for word in row.split()) for row in rows]
    require(int(ingress_count) == len(ingress) == 639, "bad ingress row count")
    require([(step, page, token, mode) for step, page, token, mode, *_ in ingress] ==
            [(0, i * 289, i, 1) for i in range(512)] + [(i, 0, 511+i, 2) for i in range(1, 128)],
            "unexpected prefill or feedback ingress schedule")
    require([p["page_count"] for p in phases] == [512 * 289 + 2] + [291] * 127, "unexpected page geometry")
    expected = []
    with descriptors.open(encoding="ascii") as stream:
        require(int(next(stream)) == sum(p["page_count"] for p in phases), "incorrect descriptor table header")
        for p in phases:
            step = p["step"]
            address = p["descriptor_base"]
            rows = []
            for i in range(p["page_count"]):
                ds, dp, base, size = next(stream).split()
                size = int(size)
                require((int(ds, 16), int(dp, 16), int(base, 16)) == (step, i, address) and size > 0 and size % 128 == 0,
                        "descriptor table is noncontiguous")
                rows.append((address, size))
                address += size
            require(address - p["descriptor_base"] == p["descriptor_bytes"], "phase descriptor extent mismatch")
            expected.append(rows if step else [])
        require(next(stream, None) is None, "extra descriptor extents")
    return expected


def geometry(program, archive, dependencies):
    started = perf_counter()
    source = seal(archive, "source.sha256", SOURCE_MANIFEST)
    for member in DECODER_SOURCES + BOUND_SOURCES:
        verify(archive, member, source[member])
    for member, checksum in DEPENDENCY_HASHES.items():
        verify(dependencies, member, checksum)
    sys.path[:0] = [str(archive.resolve()), str(dependencies.resolve() / "systemc_benchmark"),
                    str(dependencies.resolve() / "block_local_native")]
    from export_tlm_mother_program import export
    from native_tlm_local import descriptor_key
    from replay_tlm_mother import execute

    proof = seal(program, "proof.sha256", DEPLOYMENT)
    witness = json.loads(verify(program, "witness.json", proof["witness.json"]).read_bytes())
    phases = witness["phases"]
    topology = witness["topology"]
    require(topology == 25001 and witness["schema"] == "native-graph-request-pages/1", "unsupported sealed topology")
    extents = phase_inventory(phases, verify(program, "mother-descriptors.tsv", proof["mother-descriptors.tsv"]),
                              verify(program, "input-index.tsv", proof["input-index.tsv"]))
    regions = []
    for phase in phases:
        member = f"phase-{phase['step']}/descriptors.bin"
        path = verify(program, member, proof[member])
        require(path.stat().st_size == phase["descriptor_bytes"], "phase binary length differs from descriptor table")
        regions.append(path)

    totals = [Counter() for _ in phases]
    current_step, raw = 0, b""
    all_stores, all_streams = set(), set()
    for page in export(program, DEPLOYMENT, 0, first_step=1):
        step, index = page["step"], page["page"]
        if step != current_step:
            if current_step:
                require(all_streams == all_stores and len(all_streams) == 144,
                        "prior phase KV streams do not close over ordered stores")
            raw = regions[step].read_bytes()
            current_step = step
            all_stores.clear()
            all_streams.clear()
        base, size = extents[step][index]
        relative = base - phases[step]["descriptor_base"]
        calls = set()
        counts = Counter()
        weights_by_target = Counter()

        def issue(target, slot, registers):
            address = registers[0] | registers[1] << 32
            offset = address - base
            require(registers[2:7] == (0x00010080, 0x02510001, topology, 0x02500002, 0) and
                    page["targets"] & (1 << target) and 0 <= offset <= size - 128 and offset % 128 == 0 and
                    offset not in calls, "CALL disagrees with sealed local binding")
            calls.add(offset)
            record = raw[relative+offset:relative+offset+128]
            schema, abi, op = descriptor_key(record, topology)
            if schema == P_SCOPE:
                require((abi, op) == (0x02504d02, 2) and target < 3, "unsupported W provider")
                spec = unpack_from("<QQIIHBBHHHBB", record, 48)
                bursts, macs = weight_geometry(*spec)
                weights_by_target[target] += sum(bursts)
                counts["weight_channel0_bursts"] += bursts[0]
                counts["weight_channel1_bursts"] += bursts[1]
                counts["weight_macs"] += macs
                counts["head_weight_bursts"] += sum(bursts) if spec[-1] else 0
            elif schema == ATT1:
                context, position = unpack_from("<HH", record, 16)
                require((target, abi, op, context, position) == (0, 0x02500002, 1, 512+step, 511+step),
                        "unexpected ATT1 route or history")
                key_base, value_base = unpack_from("<QQ", record, 32)
                require(key_base != value_base and {key_base, value_base} <= all_stores,
                        "ATT1 depends on KV writes outside committed earlier pages")
                all_streams.update((key_base, value_base))
                qk_tiles = (context + 7) // 8
                score_words = (context + 3) // 4
                counts["attention_calls"] += 1
                counts["attention_beats"] += 40 * context
                counts["attention_sram_words"] += 128 * context + 32 * qk_tiles + 16 * score_words
            elif schema == KVR1:
                require(target == 0 and abi == 0x02500002 and op in (1, 2), "unsupported KV store provider")
                address, = unpack_from("<Q", record, 24)
                stream = address - (511+step) * 512
                require(stream > 0 and stream % BURST_BYTES == 0 and stream not in all_stores,
                        "duplicated or malformed current-position KV store")
                all_stores.add(stream)
                counts["kv_store_calls"] += 1
            else:
                require(schema in OTHER_SCHEMAS, "unknown sealed provider")
            return slot

        execute(page["instructions"], issue=issue, wait=lambda _: None,
                max_steps=page["max_steps"], entry_pc=page["entry_pc"])
        require(len(calls) * 128 == size, "CALLs did not exhaust descriptor extent")
        require(not (weights_by_target and counts["attention_calls"]), "bound requires separate W and ATT1 pages")
        require(not (counts["kv_store_calls"] and counts["attention_calls"]), "bound requires separate KV writes")
        counts["pages"] = 1
        counts["calls"] = len(calls)
        if index + 1 == phases[step]["page_count"]:
            require(counts["head_weight_bursts"] and counts["head_weight_bursts"] == sum(weights_by_target.values()),
                    "terminal page lacks its vocabulary projections")
        # Archived ATT1 sends one burst at a time. K stores four SRAM words
        # per returned beat. V stores two words per selected half and later
        # reads them back. QK rereads the query and AV reads the probabilities.
        # These counted spans are dependency ordered and wait for each ACK.
        att_ps = (counts["attention_beats"] * READ_TICKS * DDR_PS +
                  counts["attention_sram_words"] * 3 * CORE_PS)
        m_ps = max(weights_by_target.values(), default=0) * CORE_PS
        dram_ps = max(counts["weight_channel0_bursts"], counts["weight_channel1_bursts"]) * BURST_TICKS * DDR_PS
        counts["duration_floor_ps"] = max(att_ps, m_ps)
        counts["duration_floor_if_no_coalescing_ps"] = max(att_ps, m_ps, dram_ps)
        totals[step].update(counts)

    require(all_streams == all_stores and len(all_streams) == 144, "last phase KV streams lack ordered stores")
    for p, totals_here in zip(phases[1:], totals[1:]):
        require((totals_here["pages"], totals_here["calls"] * 128, totals_here["attention_calls"],
                 totals_here["kv_store_calls"]) == (p["page_count"], p["descriptor_bytes"], 36 * 16, 36 * 4),
                "decode phase lacks complete CALL, Attention, or KV counts")
    all_decode = sum(totals[1:], Counter())
    return {"deployment_sha256": DEPLOYMENT, "topology": topology, "source_manifest_sha256": SOURCE_MANIFEST,
            "scope": "sealed workload geometry and optimistic lower bounds for the fixed 107361 TLM service rules",
            "prefill": {"input_tokens": 512, "pages": phases[0]["page_count"],
                        "descriptor_bytes": phases[0]["descriptor_bytes"], "time_estimated": False},
            "decode": {"retired_token_design": 128, "intervals": 127, "core_ps": CORE_PS, "ddr_ps": DDR_PS,
                       "ddr_burst_bytes": BURST_BYTES, "attention_ddr_read_window": 1, "sram_port_bits": 128,
                       "assumed_weight_ingress_bytes_per_p_core_edge": 64,
                       "total": dict(all_decode), "phases": [dict(step=i, **totals[i]) for i in range(1, 128)],
                       "aggregate_toks_per_second_ceiling": 127e12 / all_decode["duration_floor_ps"],
                       "matched_two_step_phase2_toks_per_second_ceiling": 1e12 / totals[2]["duration_floor_ps"],
                       "aggregate_if_no_weight_coalescing_toks_per_second_ceiling":
                           127e12 / all_decode["duration_floor_if_no_coalescing_ps"]},
            "bound_omissions": ["compute, PM, descriptors, most SRAM traffic, writes, row and refresh losses",
                                "whole-request prefill execution and terminal timing"],
            "elapsed_host_seconds": perf_counter() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("program", "archive", "dependencies"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    print(json.dumps(geometry(args.program, args.archive, args.dependencies), indent=2))


if __name__ == "__main__":
    main()
