"""Bind two Qwen native RTL fixtures and replay their observed DDR admissions."""

import argparse
from collections import Counter, deque
from contextlib import ExitStack
import hashlib
from heapq import merge
from itertools import groupby
import json
from pathlib import Path
import re
import struct
import subprocess
import zlib


WINDOWS = {
    "archived_qkv": ("323204441215e5ec179df7c6f8a23803bf4902d2053e11a4b3988b6234f8c2dd", 9),
    "next_rms": ("afa825d6f1d3f549adf5a8cfb021c85e4cb428b00ff06cf46acbd44f2c298ee9", 8),
}
CONFIG_SHA = "748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766"
DDR_PS = 630
EVENTS = (b"admit", b"ddr_accept", b"callback", b"return")
DDR_EVENTS = EVENTS[1:3]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(row, size):
    result = row.split()
    require(len(result) == size, "invalid native table or trace record: {!r}".format(row))
    return result


class Proof:
    def __init__(self, root, proof_sha):
        self.root = root.resolve()
        self.hashes = {}
        proof = (self.root / "proof.sha256").read_bytes()
        require(hashlib.sha256(proof).hexdigest() == proof_sha, "unexpected upstream proof.sha256")
        for line in proof.decode("ascii").splitlines():
            digest, name = fields(line, 2)
            path = Path(name)
            if path.is_absolute():
                require(path.parent.name in ("DDR-0", "DDR-1") and path.name == "transactions.tsv",
                        "unexpected absolute upstream proof entry")
                path = Path(path.parent.name) / path.name
            require(".." not in path.parts and path not in self.hashes, "unsafe or duplicate proof entry")
            self.hashes[path] = digest

    def path(self, name):
        return self.root / name

    def check(self, name, digest):
        require(self.hashes.get(Path(name)) == digest, "upstream digest differs for " + name)

    def read(self, name):
        data = self.path(name).read_bytes()
        self.check(name, hashlib.sha256(data).hexdigest())
        return data


def control_image(data, length, crc, role):
    require(len(data) >= 128 and length <= len(data), "truncated native control image")
    magic, version, image_role, header, image_bytes, _, count, start = struct.unpack_from("<8sHBBIIII", data)
    width = 8
    require((magic, version, image_role, header, image_bytes, start) ==
            (b"LBCISA01", 3 if role == 0 else 2, role, 8, length, 128)
            and 0 < count <= (length - start) // width, "unexpected native control image header")
    require(zlib.crc32(data[:length]) == crc and not any(data[length:]), "control image CRC or padding differs")
    ops = [data[start + (index + 1) * width - 1] for index in range(count)]
    require(ops[-1] == (0x1f if role == 0 else 0x4f), "control image missing terminal opcode")
    return ["{:02x}".format(op) for op in ops]


def controls(proof, window, count):
    pages = proof.read("generated/mother-pages.tsv").decode("ascii").splitlines()
    targets = proof.read("generated/mother-targets.tsv").decode("ascii").splitlines()
    require(int(pages[0]) == int(targets[0]) == count == len(pages) - 1 == len(targets) - 1,
            "native mother page table count differs")
    result = []
    for index, (row, target) in enumerate(zip(pages[1:], targets[1:])):
        step, page, base, size, crc, padded, enabled, name = fields(row, 8)
        require([int(step), int(page), int(enabled)] == [0, index, 1]
                and [int(x) for x in fields(target, 3)[:2]] == [0, index], "native page table order differs")
        image = proof.read("generated/" + name)
        require(len(image) == int(padded) and int(base, 16) % 64 == 0, "native MC storage range differs")
        result.append({"address": int(base, 16), "bytes": int(size), "crc32": int(crc, 16),
                       "targets": int(target.split()[2]), "opcodes": control_image(image, int(size), int(crc, 16), 0)})
    local_name = "program-184927.ddr.bin" if window == "archived_qkv" else "product-local.bin"
    base, size, crc, padded = fields(proof.read("generated/product-local.tsv"), 4)
    local = proof.read("generated/" + local_name)
    require(len(local) == int(padded) and int(base, 16) % 64 == 0, "native LC storage range differs")
    proof.read("generated/descriptors.bin")
    return {"pages": result, "local": {"address": int(base, 16), "bytes": int(size),
                                         "opcodes": control_image(local, int(size), int(crc, 16), 1)}}


def one(log, pattern):
    matches = re.findall(pattern, log, re.MULTILINE)
    require(len(matches) == 1, "expected one upstream log marker: " + pattern)
    return tuple(int(x) for x in matches[0]) if isinstance(matches[0], tuple) else int(matches[0])


def rtl_summary(log, mode, control, window, program):
    passed, logged_mode = one(log, r"^PASS q projection .* cycles=(\d+) mode=(\d+)$")
    read, accepted, callbacks, retired, stalls, cycles, ch0, ch1 = one(
        log, r"^DDR_READ_PROOF rtl_accepted=(\d+) ddr_accepted=(\d+) ddr_callbacks=(\d+) rtl_retired=(\d+) "
             r"ddr_admission_waits=(\d+) core_cycles=(\d+) channel_ticks=(\d+),(\d+)$")
    write, write_bytes = one(log, r"^DDR_WRITE_PROOF committed_bursts=(\d+) bytes=(\d+)$")
    require(mode == logged_mode and passed == cycles and read == accepted == callbacks == retired
            and write * 64 == write_bytes, "RTL lifecycle totals differ")
    page_rows = re.findall(r"^PRODUCT_PAGE_TERMINAL generation=(\d+) calls=(\d+) read=(\d+) write=(\d+)$",
                           log, re.MULTILINE)
    pages = [{"generation": int(generation), "calls": int(calls), "read_bytes": int(read_bytes),
              "write_bytes": int(write_bytes)} for generation, calls, read_bytes, write_bytes in page_rows]
    require([page["generation"] for page in pages] == list(range(1, len(control["pages"]) + 1)),
            "RTL terminal sequence differs from mother pages")
    calls = sum(page["calls"] for page in pages)
    service_bytes = sum(page["read_bytes"] for page in pages)
    terminal_writes = sum(page["write_bytes"] for page in pages)
    mc_bursts = sum((page["bytes"] + 63) // 64 for page in control["pages"])
    lc_bursts = ((control["local"]["bytes"] + 63) // 64) * (2 if window == "archived_qkv" else 4)
    require(read == program["expected_ddr_reads"] + mc_bursts + lc_bursts
            and program["expected_terminal_writes"] == terminal_writes, "program and runtime transfer totals differ")
    extra = {}
    if window == "archived_qkv":
        first, positions, rows = one(log, r"^HISTORY_KV_COMPLETE first=(\d+) positions=(\d+) rows=(\d+)$")
        require((first, positions, rows) == (497, 3, 12), "unexpected QKV fixture positions")
        starts = re.findall(r"^NATIVE_PAGE_LAUNCH step=0 page=(\d+) generation=(\d+) base=(\d+) bytes=(\d+) "
                            r"crc=(\d+) targets=(\d+) cycle=(\d+)$", log, re.MULTILINE)
        ends = re.findall(r"^NATIVE_PAGE_COMMIT generation=(\d+) status=0 cycle=(\d+)$", log, re.MULTILINE)
        require(len(starts) == len(ends) == len(pages), "missing native MC page interval")
        previous = -1
        for index, (start, end, page, spec) in enumerate(zip(starts, ends, pages, control["pages"])):
            idx, generation, base, size, crc, targets, issue = map(int, start)
            terminal, done = map(int, end)
            require((idx, generation, terminal) == (index, index + 1, index + 1) and previous < issue < done < cycles
                    and (base, size, crc, targets) == tuple(spec[k] for k in ("address", "bytes", "crc32", "targets")),
                    "RTL MC launch differs from binary-backed page or interval")
            page.update(launch_cycle=issue, commit_cycle=done, elapsed_cycles=done - issue)
            previous = done
        period_num, period_den, activation = 10000, 3, 0
        extra.update(prompt_positions=[497, 498, 499], kv_rows=rows, clock_mapping="legacy_ddr_step")
    else:
        period_num, first, last, steps = one(
            log, r"^DDR_CLOCK_PROOF period_ps=(\d+) first_edge_ps=(\d+) last_edge_ps=(\d+) steps=(\d+)$")
        require(steps == cycles and last - first == (steps - 1) * period_num, "DDR and RTL edges differ")
        activation, activation_bytes = one(log, r"^DDR_ACTIVATION_PROOF read_bursts=(\d+) bytes=(\d+)$")
        words, writes, reads = one(log, r"^NEXT_LAYER_RMS_COMMITTED words=(\d+) scratch_write_acks=(\d+) "
                                       r"scratch_read_acks=(\d+)$")
        require((words, writes, reads) == (512, 11264, 11264) and activation * 64 == activation_bytes,
                "unexpected next-layer commit")
        require(program["expected_terminal_reads"] == service_bytes + 128 * calls,
                "next-RMS terminal totals differ after descriptor accounting")
        tokens = [(int(position), int(token)) for position, token in
                  re.findall(r"^HISTORY_ROW_READY position=(\d+) token=(\d+)$", log, re.MULTILINE)]
        require(len(tokens) == program["positions"] == program["attention"]["context"]
                and [position for position, _ in tokens] == list(range(program["position"], 639))
                and tokens[-1] == (638, program["input_token"]), "decode suffix position/token identity differs")
        period_den = 1
        extra.update(clock_mapping="synchronized_rtl_edge", next_layer_rms_words=words,
                     scratch_write_acks=writes, scratch_read_acks=reads, position_tokens=tokens)
    require(ch0 == ch1 == cycles * period_num // (period_den * DDR_PS), "DDR tick count differs from edge map")
    return {"mode": mode, "rtl_cycles": cycles, "ddr_ticks_per_channel": ch0, "ddr_admission_waits": stalls,
            "ddr_host_period_ps_ratio": [period_num, period_den], "counts": {"read": read, "write": write,
                                                                           "activation": activation},
            "pages": pages, "terminal_calls": calls, "service_terminal_read_bytes": service_bytes,
            "mc_ddr_fetch_bursts": mc_bursts, "lc_ddr_fetch_bursts": lc_bursts, **extra}


def write_addresses(proof):
    result = {}
    for row in proof.read("generated/kv-stores.tsv").splitlines():
        start, length, first_tag = map(int, fields(row, 3))
        require(start % 64 == length % 64 == 0 and length > 0, "unaligned KV store range")
        for offset in range(0, length, 64):
            address = start + offset
            require(address not in result, "overlapping KV store ranges")
            result[address] = first_tag + offset // 64
    return result


def lifecycle(proof, name, kind, root, summary, expected_writes):
    """Audit finite port ownership while spooling one monotone stream per channel/event."""
    digest = hashlib.sha256()
    pending, returned, delays = {}, Counter(), Counter()
    read = kind == "read"
    lanes = [deque() for _ in range(4 if read else 1)]
    depths = [0] * len(lanes)
    last_tick = {}
    num, den = summary["ddr_host_period_ps_ratio"]
    with ExitStack() as stack:
        source = stack.enter_context(proof.path(name).open("rb"))
        outputs = {(channel, event): stack.enter_context((root / stream_name(kind, channel, event)).open("wb"))
                   for channel in range(2) for event in DDR_EVENTS}
        for line in source:
            digest.update(line)
            event, tick, port, tag, address = fields(line, 5)
            tick, port, tag, address = map(int, (tick, port, tag, address))
            require(event in EVENTS and 0 <= port < (4 if read else 2) and 0 <= tick and 0 <= tag
                    and 0 <= address < 1 << 34 and address % 64 == 0, "invalid native DDR trace field")
            channel = port // 2 if read else port
            require(read or channel == (address >> 6) & 1, "non-read lane differs from address interleave")
            queue = lanes[port if read else 0]
            key = (port, tag)
            if event == b"admit":
                require(key not in pending and len(queue) < (16 if read else 1), "native DDR port exceeds ownership bound")
                pending[key] = [address, tick, None, None]
                queue.append(key)
                lane = port if read else 0
                depths[lane] = max(depths[lane], len(queue))
            else:
                entry = pending.get(key)
                require(entry is not None and entry[0] == address, "native DDR event lacks admitted identity")
                if event == b"ddr_accept":
                    require(entry[2] is None and tick >= entry[1] * num // (den * DDR_PS), "DDR accepted before admit")
                    entry[2] = tick
                elif event == b"callback":
                    require(entry[2] is not None and entry[3] is None and entry[2] < tick, "DDR callback order differs")
                    entry[3] = tick
                    delays[tick - entry[2]] += 1
                else:
                    require(entry[3] is not None and entry[3] <= tick * num // (den * DDR_PS)
                            and queue[0] == key and tick <= summary["rtl_cycles"], "RTL DDR return order differs")
                    if kind == "write":
                        require(expected_writes.pop(address, None) == tag, "committed KV address/tag differs from store table")
                    queue.popleft()
                    del pending[key]
                    returned[channel] += 1
            if event in DDR_EVENTS:
                stream = (channel, event)
                require(last_tick.get(stream, 0) <= tick <= summary["ddr_ticks_per_channel"], "DDR channel tick order differs")
                last_tick[stream] = tick
                outputs[stream].write(b"%d\t%d\n" % (tick, address))
    proof.check(name, digest.hexdigest())
    total = sum(returned.values())
    require(not pending and total == summary["counts"][kind], "native DDR trace did not drain or differs from RTL total")
    if kind == "write":
        require(not expected_writes, "KV store table has uncommitted bursts")
    return {"trace_sha256": digest.hexdigest(), "retired_per_channel": [returned[0], returned[1]],
            "max_outstanding_per_port": depths, "ddr_ticks_p50": percentile(delays, total, 50),
            "ddr_ticks_p95": percentile(delays, total, 95), "ddr_ticks_max": max(delays)}


def percentile(histogram, total, quantile):
    rank = (total * quantile + 99) // 100
    for delay, count in sorted(histogram.items()):
        rank -= count
        if rank <= 0:
            return delay
    raise ValueError("empty native DDR latency distribution")


def stream_name(kind, channel, event):
    return "{}-{}-{}.tsv".format(kind, channel, event.decode("ascii"))


def replay_rows(root, kinds, event):
    def rows(source, priority, op):
        for line in source:
            tick, address = map(int, line.split())
            yield tick, priority, op, address

    for channel in range(2):
        with ExitStack() as stack:
            inputs = [rows(stack.enter_context((root / stream_name(kind, channel, event)).open("rb")), index,
                           b"W" if kind == "write" else b"R") for index, kind in enumerate(kinds)]
            for tick, _, op, address in merge(*inputs, key=lambda row: row[:2]):
                yield channel, tick, op, address


def compare_callbacks(observed, simulated):
    def groups(rows):
        for key, group in groupby(rows, key=lambda row: row[:2]):
            yield key, Counter(row[2:] for row in group)

    expected, actual = iter(groups(observed)), iter(groups(simulated))
    count = 0
    for key, group in expected:
        require(next(actual, None) == (key, group), "simulated DDR callback differs at channel/tick {}".format(key))
        count += sum(group.values())
    require(next(actual, None) is None, "unexpected simulated DDR callbacks after archive drain")
    return count


def simulated_rows(path):
    with path.open("rb") as source:
        for line in source:
            channel, tick, op, address = fields(line, 4)
            yield int(channel), int(tick), op, int(address)


def mode_audit(proof, window, control, program, mode, binary, config, output):
    output.mkdir()
    log = proof.read("replay-{}.log".format(mode)).decode("ascii")
    result = rtl_summary(log, mode, control, window, program)
    names = {"read": "transactions.tsv", "activation": "activation-transactions.tsv", "write": "write-transactions.tsv"}
    kinds = [kind for kind in names if result["counts"][kind]]
    prefix = "DDR-{}/".format(mode)
    result["lifecycle"] = {kind: lifecycle(proof, prefix + names[kind], kind, output, result, write_addresses(proof))
                           for kind in kinds}
    reference = proof.read("generated/kv-reference.bin")
    committed = proof.read(prefix + "committed-kv.bin")
    require(committed == reference and len(committed) == result["counts"]["write"] * 64, "committed KV payload differs")
    result["committed_kv_sha256"] = hashlib.sha256(committed).hexdigest()
    schedule, callbacks = output / "schedule.tsv", output / "callbacks.tsv"
    with schedule.open("wb") as stream:
        for row in replay_rows(output, kinds, b"ddr_accept"):
            stream.write(b"%d\t%d\t%s\t%d\n" % row)
    with callbacks.open("wb") as stream, (output / "simulator.log").open("wb") as err:
        subprocess.run([str(binary), str(config), str(output / "dramsim"), str(schedule)], stdout=stream,
                       stderr=err, check=True)
    result["exact_ddr_callbacks"] = compare_callbacks(replay_rows(output, kinds, b"callback"), simulated_rows(callbacks))
    require(result["exact_ddr_callbacks"] == sum(result["counts"].values()), "DDR callback total differs")
    result["replay_schedule_sha256"] = file_digest(schedule)
    result["replay_callbacks_sha256"] = file_digest(callbacks)
    return result


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window", choices=WINDOWS)
    parser.add_argument("archive", type=Path)
    parser.add_argument("binary", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path, help="new directory for replay artifacts")
    args = parser.parse_args()
    config = args.config.resolve()
    require(hashlib.sha256(config.read_bytes()).hexdigest() == CONFIG_SHA, "DDR config differs from upstream")
    proof_sha, count = WINDOWS[args.window]
    proof = Proof(args.archive, proof_sha)
    control = controls(proof, args.window, count)
    program = json.loads(proof.read("generated/program.json"))
    lineage = {key: program[key] for key in ("source_graph_sha256", "selected_descriptor_sha256", "tokens_sha256",
                                            "linked_bundle_proof_sha256", "layout_sha256")}
    if args.window == "next_rms":
        words = proof.read("generated/next-rms-reference.hex").splitlines()
        payload = b"".join(int(word, 16).to_bytes(16, "little") for word in words)
        lineage["next_rms_reference_sha256"] = hashlib.sha256(payload).hexdigest()
        require(len(words) == 512 and lineage["next_rms_reference_sha256"] == program["next_layer_rms"]["output_sha256"],
                "next-layer RMS reference differs from linked program")
    output = args.output.resolve()
    output.mkdir()
    modes = [mode_audit(proof, args.window, control, program, mode, args.binary.resolve(), config, output / str(mode))
             for mode in range(2)]
    print(json.dumps({"window": args.window, "proof_sha256": proof_sha, "ddr_config_sha256": CONFIG_SHA,
                      "ddr_tick_ps": DDR_PS, "control": control, "lineage": lineage, "modes": modes,
                      "timing_input": "observed_ddr_accept", "whole_system_timing_qualified": False}, indent=2))


if __name__ == "__main__":
    main()
