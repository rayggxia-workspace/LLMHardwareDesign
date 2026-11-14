"""Decode the native control and descriptor dependencies of the 105530 fixture.

The deployment produces ordered calls, wait groups and descriptor-backed DDR
addresses. Timing and service-generated requests require a separate model.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

from qwen_native_ddr import Proof, WINDOWS, control_image, fields, require


TOPOLOGY = 25001
ABI = 0x02500002
MC_CAPACITY = 0x02590003
LC_CAPACITY = 0x02510001
CONTROL_BYTES = 8
DESCRIPTOR_BYTES = 128
BURST_BYTES = 64
P_SCOPE = 0x02505001


def words(data):
    count, start = struct.unpack_from("<II", data, 20)
    return [struct.unpack_from("<Q", data, start + CONTROL_BYTES * pc)[0] for pc in range(count)]


def args(word):
    return ((word >> 56) & 255, (word >> 48) & 255, (word >> 40) & 255,
            (word >> 32) & 255, word & 0xffffffff)


def decode_local(data):
    """Check the resident LC wrapper and its native service execution entry."""
    task_count, _, exec_count, _ = struct.unpack_from("<4H", data, 28)
    task_offset, _, exec_offset = struct.unpack_from("<III", data, 36)
    image_id, topology, abi = struct.unpack_from("<III", data, 60)
    capacity, = struct.unpack_from("<I", data, 84)
    require((task_count, exec_count, task_offset, exec_offset) == (1, 1, 160, 224)
            and (image_id, topology, abi, capacity) == (TOPOLOGY, TOPOLOGY, ABI, LC_CAPACITY),
            "unexpected resident LC layout or identity")
    instructions = [args(word) for word in words(data)]
    require(instructions == [(0x41, 0, 0, 0, 0), (0x44, 0, 0, 0, 1), (0x4f, 0, 0, 0, 0)],
            "resident LC is not the expected EXEC, WAIT and END wrapper")
    task = data[task_offset:exec_offset]
    require(struct.unpack_from("<H", task)[0] == 1
            and struct.unpack_from("<4I", task, 16) == (3, 1, image_id, topology)
            and struct.unpack_from("<I", task, 44)[0] == abi,
            "LC task differs from the bound wrapper")
    entry = data[exec_offset:exec_offset + DESCRIPTOR_BYTES]
    require(struct.unpack_from("<HHH", entry) == (1, 0, 0x250)
            and struct.unpack_from("<I", entry, 56)[0] == abi,
            "LC execution entry does not bind the native descriptor service")
    return {"image_id": image_id, "opcodes": ["EXEC", "WAIT", "END"], "native_operation": 0x250}


def decode_routes(data):
    """Decode the generated four-target RTL route parameters."""
    text = data.decode("ascii")
    routes = re.search(r"\.ROUTES\((\d+)\)", text)
    require(routes is not None, "missing route slots per target")
    slots = int(routes.group(1))
    require(slots == 9, "unexpected route slot count")
    widths = {"ENABLE": 1, "SCHEMA": 32, "PROVIDER_ABI": 32, "OP": 16}
    values = {}
    for field, width in widths.items():
        entry = re.search(r"\.ROUTE_" + field + r"\((\d+)'h([0-9a-fA-F]+)\)", text)
        require(entry is not None and int(entry.group(1)) == 4 * slots * width, "invalid route parameter width")
        values[field] = int(entry.group(2), 16)
        require(values[field] < 1 << (4 * slots * width), "oversized route parameter")
    result = [set() for _ in range(4)]
    for index in range(4 * slots):
        if values["ENABLE"] & (1 << index):
            signature = tuple((values[key] >> (index * widths[key])) & ((1 << widths[key]) - 1)
                              for key in ("SCHEMA", "PROVIDER_ABI", "OP"))
            require(signature not in result[index // slots], "duplicate route signature")
            result[index // slots].add(signature)
    require(all(result), "unexpected empty route target")
    return result


def expand_mother(data, descriptor_base, descriptor_count, target_mask):
    """Execute MC's supported static instructions and retain WAIT dependencies."""
    program = words(data)
    start, = struct.unpack_from("<I", data, 16)
    max_steps, = struct.unpack_from("<I", data, 52)
    image, topology, abi = struct.unpack_from("<III", data, 60)
    capacity, = struct.unpack_from("<I", data, 84)
    require((start, image, topology, abi, capacity) == (0, 900, TOPOLOGY, ABI, MC_CAPACITY)
            and 0 < max_steps <= 10000, "unexpected native MC identity or instruction bound")
    registers = [0] * 8
    pending, calls, waves = [], [], []
    pc = start
    for step in range(1, max_steps + 1):
        require(0 <= pc < len(program), "MC PC out of range")
        opcode, a, b, c, imm = args(program[pc])
        next_pc = pc + 1
        if opcode == 0x13 and a < 8 and b == c == 0:
            registers[a] = imm
        elif opcode == 0x16 and (a, b, c, imm) == (0, 0, 0, DESCRIPTOR_BYTES):
            pointer = (registers[1] << 32) | registers[0]
            require(pointer + imm < 1 << 48, "MC descriptor pointer overflow")
            registers[0], registers[1] = (pointer + imm) & 0xffffffff, (pointer + imm) >> 32
        elif opcode == 0x10 and a == b and a < 4 and c == imm == 0:
            address = (registers[1] << 32) | registers[0]
            require(registers[2:7] == [0x00010080, LC_CAPACITY, TOPOLOGY, ABI, 0],
                    "MC CALL changed LC ABI or descriptor length")
            require(target_mask & (1 << a) and all(calls[index]["target"] != a for index in pending),
                    "MC CALL reuses a live or unavailable target")
            require(len(calls) < descriptor_count and address == descriptor_base + DESCRIPTOR_BYTES * len(calls),
                    "MC CALL escaped its descriptor arena")
            pending.append(len(calls))
            calls.append({"target": a, "token": b, "descriptor_address": address, "mc_pc": pc, "wave": len(waves)})
        elif opcode == 0x11 and a == b == c == 0:
            require(pending and imm == sum(1 << calls[index]["token"] for index in pending),
                    "MC WAIT does not cover the open call group")
            waves.append({"calls": pending, "wait_pc": pc, "wait_mask": imm})
            pending = []
        elif opcode == 0x17 and a == 7 and b == c == 0 and imm < pc:
            require(0 < registers[a] <= 65535, "invalid MC loop counter")
            registers[a] -= 1
            if registers[a]:
                next_pc = imm
        elif opcode == 0x1f and a == b == c == imm == 0:
            require(next_pc == len(program) and not pending and len(calls) == descriptor_count
                    and target_mask == sum(1 << target for target in {call["target"] for call in calls}),
                    "MC END disagrees with descriptor or target coverage")
            return calls, waves, step
        else:
            raise ValueError("unsupported MC instruction at PC {}: {:016x}".format(pc, program[pc]))
        pc = next_pc
    raise ValueError("MC exceeded its sealed instruction bound")


def span(address, size, write, first_tag=None):
    require(size > 0 and address % BURST_BYTES == size % BURST_BYTES == 0
            and address + size <= 1 << 64, "unaligned or overflowing native DDR span")
    result = {"address": address, "bytes": size, "write": write}
    if first_tag is not None:
        result["first_tag"] = first_tag
    return result


def service_spans(schema, operation, data):
    """Expose the addresses owned directly by DMA/Attention descriptor formats."""
    if schema == P_SCOPE.to_bytes(4, "little"):
        bases = struct.unpack_from("<QQ", data, 48)
        columns, first, stride, groups, context, full_k, k_begin, k_end, ways, head = struct.unpack_from(
            "<IIHBBHHHBB", data, 64)
        require(operation == 2 and ways in (1, 2) and head in (0, 1)
                and 0 < groups <= 16 and context + groups * ways <= 16
                and 0 <= k_begin < k_end <= full_k and full_k % 128 == k_begin % 128 == k_end % 128 == 0
                and first % 8 == stride % 8 == 0 and stride >= 8 and first + (groups - 1) * stride < columns
                and not any(struct.unpack_from("<QQ", data, 96)), "unsupported stream weight descriptor")
        size = 1152 if head else 1088
        # record_range_iterator visits K, then way, then output column group.
        return [span(base + ((first + group * stride) // 8 * (full_k // 128) + k // 128) * size, size, False)
                for k in range(k_begin, k_end, 128) for base in bases[:ways] for group in range(groups)]
    if schema in (b"DRL1", b"DRL8"):
        return [span(struct.unpack_from("<Q", data, 24)[0], 512 if schema == b"DRL1" else 8192, False)]
    if schema in (b"DWS1", b"DWS8", b"FDS8", b"KVR1"):
        address, first_tag = struct.unpack_from("<QQ", data, 24)
        return [span(address, 512 if schema in (b"DWS1", b"KVR1") else 8192, True, first_tag)]
    if schema == b"ATT1":
        context, position = struct.unpack_from("<HH", data, 16)
        key, value = struct.unpack_from("<QQ", data, 32)
        require(1 <= context <= 639 and position == context - 1 and abs(key - value) >= context * 512,
                "invalid Attention causal prefix")
        # K streams rows once. V streams a pair per row for each of the 16
        # output groups, with four groups using each 128-byte pair.
        return [span(key, context * 512, False)] + [
            span(value + position * 512 + group // 4 * 128, 128, False)
            for group in range(16) for position in range(context)]
    # The U RMS gamma is staged by its preceding DRL8 command. The RMS,
    # ADD and RoPE operations themselves use resident SRAM.
    if schema == b"RPE1" or (schema == b"\x03\x00\x00\x00" and operation in (2, 3)):
        return []
    raise ValueError("unsupported descriptor service schema " + schema.hex())


def descriptor(call, data, routes):
    schema, size, operation, abi, topology = struct.unpack_from("<IHHII", data)
    crc, = struct.unpack_from("<I", data, 124)
    require((size, topology, zlib.crc32(data[:124])) == (DESCRIPTOR_BYTES, TOPOLOGY, crc)
            and (schema, abi, operation) in routes[call["target"]],
            "descriptor length, topology, CRC or target route differs")
    dma = service_spans(data[:4], operation, data)
    call.update(schema=schema, operation=operation, provider_abi=abi, descriptor_hex=data.hex(),
                descriptor_ddr_spans=[span(call["descriptor_address"], DESCRIPTOR_BYTES, False)],
                service_ddr_spans=dma)


def parse_table(proof, filename, columns, count):
    lines = proof.read("generated/" + filename).decode("ascii").splitlines()
    require(len(lines) == count + 1 and int(lines[0]) == count, filename + " count differs")
    return [fields(line, columns) for line in lines[1:]]


def ingress_reads(proof):
    """Recover the three-row RTL prompt ingress and serial RMS source reads."""
    ingress = json.loads(proof.read("generated/program.json"))["prompt_ingress"]
    token_image = proof.read("generated/token.bin")
    tokens = struct.unpack_from("<3I", token_image)
    require(len(token_image) == 64 and not any(token_image[12:]) and tuple(ingress["tokens"]) == tokens
            and ingress["serial_rms"] is True and all(0 <= token < 151936 for token in tokens),
            "invalid archived prompt ingress")
    return [span(ingress["prompt_address"], 64, False)] + [
        item for token in tokens for item in
        (span(ingress["embedding_address"] + 8192 * token, 8192, False),
         span(ingress["gamma_address"], 8192, False))]


def activation_read(proof, pages):
    """Bind the separate FFN activation path to its producing store."""
    base, down = (int(value, 16) for value in fields(
        proof.read("generated/ffn-runtime.tsv").splitlines()[0], 2))
    stores = [item for call in pages[3]["calls"] for item in call["service_ddr_spans"]
              if item["write"] and item["address"] == base]
    require(len(stores) == 1 and stores[0]["bytes"] == 8192 and base + 8192 == down,
            "activation read does not match its preceding DDR producer")
    return span(base, stores[0]["bytes"], False)


def decode_archive(root):
    """Recover deployment calls without reading or importing timing outputs."""
    proof_sha, count = WINDOWS["next_rms"]
    proof = Proof(Path(root), proof_sha)
    mother = parse_table(proof, "mother-pages.tsv", 8, count)
    targets = parse_table(proof, "mother-targets.tsv", 3, count)
    ranges = parse_table(proof, "mother-descriptors.tsv", 4, count)
    all_descriptors = proof.read("generated/descriptors.bin")
    routes = decode_routes(proof.read("generated/decode638_product_routes.svh"))
    base, size, crc, padded = fields(proof.read("generated/product-local.tsv"), 4)
    local_image = proof.read("generated/product-local.bin")
    require(len(local_image) == int(padded), "resident LC padding size differs")
    control_image(local_image, int(size), int(crc, 16), 1)
    local = decode_local(local_image)
    local.update(address=int(base, 16), bytes=int(size), padded_bytes=int(padded))

    pages, offset, installed = [], 0, set()
    tickets = [0] * len(routes)
    bound_routes = [set() for _ in routes]
    for index, (image_row, target_row, range_row) in enumerate(zip(mother, targets, ranges)):
        require(all(tuple(int(field, 16) for field in row[:2]) == (0, index)
                    for row in (image_row, target_row, range_row)), "native page table identity differs")
        base, size, crc, padded, enabled, name = image_row[2:]
        descriptor_base, descriptor_size = int(range_row[2], 16), int(range_row[3])
        image = proof.read("generated/" + name)
        size, padded = int(size), int(padded)
        require(int(enabled) == 1 and len(image) == padded and padded == (size + 63) // 64 * 64,
                "native MC image install differs")
        control_image(image, size, int(crc, 16), 0)
        data = proof.read("generated/phase-{}/descriptors.bin".format(index))
        require(descriptor_base % DESCRIPTOR_BYTES == descriptor_size % DESCRIPTOR_BYTES == 0
                and len(data) == descriptor_size and data == all_descriptors[offset:offset + descriptor_size],
                "page descriptor aperture differs from concatenated image")
        if pages:
            require(descriptor_base == pages[-1]["descriptor_base"] + pages[-1]["descriptor_bytes"],
                    "native descriptor apertures are not contiguous")
        target_mask = int(target_row[2], 16)
        calls, waves, steps = expand_mother(image, descriptor_base, descriptor_size // DESCRIPTOR_BYTES, target_mask)
        for ordinal, call in enumerate(calls):
            target = call["target"]
            tickets[target] += 1
            call["ticket"] = tickets[target]
            descriptor(call, data[ordinal * DESCRIPTOR_BYTES:(ordinal + 1) * DESCRIPTOR_BYTES], routes)
            bound_routes[target].add((call["schema"], call["provider_abi"], call["operation"]))
        first_install = sorted({call["target"] for call in calls} - installed)
        installed.update(first_install)
        pm_fetches = [dict(span(local["address"], local["padded_bytes"], False), domain=domain)
                      for domain in first_install]
        pm_fetches.append(dict(span(int(base, 16), padded, False), domain=4))
        pages.append({"generation": index + 1, "address": int(base, 16), "bytes": size,
                      "descriptor_base": descriptor_base, "descriptor_bytes": descriptor_size,
                      "target_mask": target_mask, "calls": calls, "waves": waves, "mc_dynamic_instructions": steps,
                      "pm_fetches": pm_fetches})
        offset += descriptor_size
    require(offset == len(all_descriptors) and bound_routes == routes,
            "native descriptor or route registry did not fully bind")
    return {"job_id": 105530, "proof_sha256": proof_sha, "topology": TOPOLOGY, "local": local,
            "ingress_ddr_spans": ingress_reads(proof), "ffn_activation_read": activation_read(proof, pages),
            "pages": pages}


def terminal_key(call, generation):
    if generation == 5:
        return "ffn", call["target"], call["ticket"]
    if call["schema"] == int.from_bytes(b"FDS8", "little"):
        return "fds", call["ticket"]
    routes = {P_SCOPE: 1, 3: 3}
    routes.update({int.from_bytes(schema, "little"): route for schema, route in
                   ((b"DRL1", 2), (b"RPE1", 4), (b"KVR1", 5), (b"DWS1", 5),
                    (b"ATT1", 6), (b"DRL8", 7), (b"DWS8", 8))})
    route = 9 if (call["schema"], call["target"], call["operation"]) == (3, 3, 3) else routes[call["schema"]]
    return "service", route, call["ticket"]


def compare_terminals(schedule, root):
    """Compare PM addresses and per-wave terminal identities, without fitting cycles."""
    proof = Proof(Path(root), schedule["proof_sha256"])
    patterns = (
        ("service", re.compile(r"DECODE_QKV_TERMINAL route=(\d+) ticket=(\d+) read=\d+ write=\d+")),
        ("ffn", re.compile(r"PRODUCT_FFN_TERMINAL target=(\d+) ticket=(\d+) read=\d+ write=\d+")),
        ("fds", re.compile(r"PRODUCT_FDS_TERMINAL ticket=(\d+) read=\d+ write=\d+")),
    )
    page_end = re.compile(r"PRODUCT_PAGE_TERMINAL generation=(\d+) calls=(\d+) read=\d+ write=\d+")
    pm_read = re.compile(r"PRODUCT_PM generation=(\d+) domain=(\d+) address=(\d+)")
    receipts = []
    for mode in range(2):
        page_index, terminals, pm = 0, [], []
        log = proof.read("replay-{}.log".format(mode))
        for line in log.decode("ascii").splitlines():
            match = pm_read.fullmatch(line)
            if match:
                pm.append(tuple(map(int, match.groups())))
            for kind, pattern in patterns:
                match = pattern.fullmatch(line)
                if match:
                    terminals.append((kind,) + tuple(map(int, match.groups())))
            match = page_end.fullmatch(line)
            if not match:
                continue
            require(page_index < len(schedule["pages"]), "unexpected additional RTL page")
            page = schedule["pages"][page_index]
            generation = page["generation"]
            require(tuple(map(int, match.groups())) == (generation, len(page["calls"])) and
                    len(terminals) == len(page["calls"]), "page terminal disagrees with decoded call count")
            for wave in page["waves"]:
                calls = wave["calls"]
                expected = Counter(terminal_key(page["calls"][index], generation) for index in calls)
                require(Counter(terminals[calls[0]:calls[-1] + 1]) == expected,
                        "RTL completion violates decoded WAIT group at generation {}, call {}".format(generation, calls[0]))
            expected_pm = [(generation, item["domain"], address) for item in page["pm_fetches"]
                           for address in range(item["address"], item["address"] + item["bytes"], BURST_BYTES)]
            require(pm == expected_pm, "RTL program fetch differs from decoded page or residency")
            page_index += 1
            terminals, pm = [], []
        require(page_index == len(schedule["pages"]) and not terminals and not pm, "incomplete RTL page evidence")
        receipts.append({"mode": mode, "page_count": page_index,
                         "terminal_count": sum(len(page["calls"]) for page in schedule["pages"]),
                         "log_sha256": hashlib.sha256(log).hexdigest()})
    return receipts


def compare_writes(schedule, root):
    """Check the complete write address and tag multiset in each frozen RTL mode."""
    proof = Proof(Path(root), schedule["proof_sha256"])
    expected = Counter()
    known_reads = 0
    for page in schedule["pages"]:
        for call in page["calls"]:
            for item in call["service_ddr_spans"]:
                if item["write"]:
                    expected.update((item["address"] + offset, item["first_tag"] + offset // BURST_BYTES)
                                    for offset in range(0, item["bytes"], BURST_BYTES))
                else:
                    known_reads += item["bytes"] // BURST_BYTES
    result = []
    activation = schedule["ffn_activation_read"]
    activation_bursts = range(activation["address"], activation["address"] + activation["bytes"], BURST_BYTES)
    for mode in range(2):
        name = "DDR-{}/write-transactions.tsv".format(mode)
        observed = Counter()
        commits = {}
        for row in proof.read(name).splitlines():
            event, cycle, port, tag, address = fields(row, 5)
            if event == b"admit":
                address = int(address)
                require(int(port) == (address >> 6) & 1, "RTL write trace uses unexpected channel")
                observed[(address, int(tag))] += 1
            elif event == b"return":
                commits[int(address)] = int(cycle)
        require(observed == expected, "descriptor-derived write addresses or tags differ from mode {}".format(mode))
        activations = []
        for row in proof.read("DDR-{}/activation-transactions.tsv".format(mode)).splitlines():
            event, cycle, port, tag, address = fields(row, 5)
            if event == b"admit":
                address = int(address)
                require(int(port) == (address >> 6) & 1 and address in commits and commits[address] < int(cycle),
                        "FFN activation address/channel or committed producer dependency differs")
                activations.append((address, int(tag)))
        require(activations == [(address, tag) for tag, address in enumerate(activation_bursts)],
                "FFN activation burst addresses or tags differ from bound runtime")
        result.append({"mode": mode, "matched_write_bursts": sum(expected.values()),
                       "matched_ffn_activation_bursts": len(activations)})
    return {"modes": result, "descriptor_derived_service_read_bursts": known_reads}


def compare_reads(schedule, root):
    """Check physical read addresses as a multiset across the four DDR lanes."""
    proof = Proof(Path(root), schedule["proof_sha256"])
    expected = Counter()

    def add(item):
        expected.update(range(item["address"], item["address"] + item["bytes"], BURST_BYTES))

    for item in schedule["ingress_ddr_spans"]:
        add(item)
    for page in schedule["pages"]:
        for item in page["pm_fetches"]:
            add(item)
        for call in page["calls"]:
            for item in call["descriptor_ddr_spans"] + call["service_ddr_spans"]:
                if not item["write"]:
                    add(item)
    results = []
    for mode in range(2):
        name = "DDR-{}/transactions.tsv".format(mode)
        digest = hashlib.sha256()
        remaining, excess = expected.copy(), Counter()
        with proof.path(name).open("rb") as source:
            for line in source:
                digest.update(line)
                if not line.startswith(b"admit\t"):
                    continue
                address = int(fields(line, 5)[-1])
                if remaining[address]:
                    remaining[address] -= 1
                else:
                    excess[address] += 1
        proof.check(name, digest.hexdigest())
        missing = +remaining
        require(not missing and not excess, "mode {} address count differs: missing {} first {}; excess {} first {}".format(
            mode, sum(missing.values()), list(missing.items())[:8], sum(excess.values()), list(excess.items())[:8]))
        results.append({"mode": mode, "matched_read_bursts": sum(expected.values())})
    return results


def compare_edge_log(schedule, path):
    """Check markers using the independently decoded control and descriptor schedule."""
    by_generation = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        prefix, kind, *pairs = line.split()
        require(prefix == "QWEN_EDGE", "invalid edge log row")
        values = dict((key, int(value)) for key, value in (pair.split("=") for pair in pairs))
        require(len(values) == len(pairs), "duplicate marker field")
        if values["generation"]:
            page = by_generation.setdefault(values["generation"], {})
            page.setdefault(kind, []).append(values)
    require(set(by_generation) == {page["generation"] for page in schedule["pages"]},
            "marker generations do not match the deployment")

    def rows(events, kind, fields_):
        return [tuple(event[field] for field in fields_) for event in events.get(kind, ())]

    results = []
    for index, page in enumerate(schedule["pages"]):
        generation = page["generation"]
        events = by_generation[generation]
        require(rows(events, "page_launch", ("step", "page", "targets")) == [(0, index, page["target_mask"])]
                and rows(events, "page_commit", ("status", "calls")) == [(0, len(page["calls"]))],
                "marker page launch or commit differs at generation {}".format(generation))
        expected_pm = [(item["domain"], address) for item in page["pm_fetches"]
                       for address in range(item["address"], item["address"] + item["bytes"], BURST_BYTES)]
        require(rows(events, "pm_admit", ("domain", "address")) == expected_pm,
                "marker PM request differs at generation {}".format(generation))
        admits, accepts, retires = (events.get(kind, ()) for kind in
                                    ("descriptor_admit", "service_accept", "service_retire"))
        calls = page["calls"]
        require(len(admits) == len(calls) * 2 and len(accepts) == len(retires) == len(calls),
                "marker descriptor or service count differs at generation {}".format(generation))
        admissions = {(item["target"], item["address"]): item["cycle"] for item in admits}
        issue = {(item["target"], item["ticket"]): item for item in accepts}
        done = {(item["target"], item["ticket"]): item for item in retires}
        require(len(admissions) == len(admits) and len(issue) == len(accepts) and len(done) == len(retires),
                "duplicate descriptor or service marker")
        launch_cycle = events["page_launch"][0]["cycle"]
        commit_cycle = events["page_commit"][0]["cycle"]
        previous = launch_cycle - 1
        for wave in page["waves"]:
            retirement_cycles = []
            for call_index in wave["calls"]:
                call = calls[call_index]
                key = (call["target"], call["ticket"])
                address = call["descriptor_address"]
                first = admissions.get((key[0], address), -1)
                second = admissions.get((key[0], address + BURST_BYTES), -1)
                accepted, retired = issue.get(key), done.get(key)
                require(accepted is not None and retired is not None
                        and (accepted["schema"], accepted["op"]) == (call["schema"], call["operation"])
                        and retired["status"] == 0
                        and previous < first < second < accepted["cycle"] < retired["cycle"] <= commit_cycle,
                        "descriptor/WAIT/terminal markers diverge at generation {}, call {}".format(generation, call_index))
                retirement_cycles.append(retired["cycle"])
            previous = max(retirement_cycles)
        results.append({"generation": generation, "descriptor_requests": len(admits),
                        "pm_requests": len(expected_pm), "services": len(calls)})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--compare", action="store_true", help="also compare RTL terminals and write addresses")
    parser.add_argument("--read-traces", action="store_true", help="also stream the full RTL DDR read traces")
    parser.add_argument("--edge-log", action="append", type=Path, default=[], help="compare instrumented markers")
    options = parser.parse_args()
    schedule = decode_archive(options.archive)
    if options.compare:
        schedule["observed_terminals"] = compare_terminals(schedule, options.archive)
        schedule["observed_writes"] = compare_writes(schedule, options.archive)
    if options.read_traces:
        schedule["observed_reads"] = compare_reads(schedule, options.archive)
    if options.edge_log:
        schedule["observed_edges"] = [compare_edge_log(schedule, path) for path in options.edge_log]
    print(json.dumps(schedule, indent=2))


if __name__ == "__main__":
    main()
