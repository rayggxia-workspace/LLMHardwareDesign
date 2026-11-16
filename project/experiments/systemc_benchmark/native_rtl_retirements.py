"""Extract cycle and time receipts from native controller handshakes."""

import argparse
from collections import Counter
from hashlib import sha256
from itertools import zip_longest
import json
from pathlib import Path
from struct import pack, unpack


EVENTS = {
    "NATIVE_REQUEST_START": ("job", "cycle", "ps"),
    "NATIVE_PHASE_START": ("job", "step", "input", "cycle", "ps"),
    "NATIVE_PHASE_COMMIT": ("job", "step", "kv", "token", "cycle", "ps"),
    "NATIVE_TOKEN_RETIRE": ("job", "step", "token", "cycle", "ps"),
}
PAGE_EVENTS = {
    "NATIVE_PAGE_LAUNCH": ("step", "page", "generation", "base", "bytes", "crc", "targets", "cycle"),
    "NATIVE_PAGE_COMMIT": ("generation", "status", "cycle"),
    "NATIVE_INPUT_COMMIT": ("step", "page", "generation", "word", "data", "cycle"),
    "NATIVE_REQUEST_DONE": ("outputs", "error", "cycle"),
}


def program_pages(mother, targets):
    count = int(next(mother))
    if count <= 0 or int(next(targets)) != count:
        raise ValueError("inconsistent program table lengths")
    seen = 0
    prior = (-1, 0)
    for image, mask in zip_longest(mother, targets):
        if image is None or mask is None:
            raise ValueError("program and target tables have different lengths")
        step, page, base, size, crc, _, _, _ = image.split()
        mask_step, mask_page, target_mask = mask.split()
        key = int(step, 16), int(page, 16)
        if ((int(mask_step, 16), int(mask_page, 16)) != key or
                key not in ((prior[0], prior[1]+1), (prior[0]+1, 0))):
            raise ValueError("unordered or mismatched program page key")
        seen += 1
        prior = key
        yield (*key, seen, int(base, 16), int(size), int(crc, 16), int(target_mask, 16))
    if seen != count:
        raise ValueError("program page table is incomplete")


def program_binding(root, deployment_sha, phases):
    seal = (root / "proof.sha256").read_bytes()
    if sha256(seal).hexdigest() != deployment_sha:
        raise ValueError("program seal differs from the run deployment")
    expected = dict(reversed(line.split("  ", 1)) for line in seal.decode("ascii").splitlines())
    evidence = {"deployment_sha256": deployment_sha}
    for name in ("mother-pages.tsv", "mother-targets.tsv", "witness.json", "service-signatures.json", "input-index.tsv"):
        digest = sha256((root / name).read_bytes()).hexdigest()
        if expected.get(name) != digest:
            raise ValueError(f"{name} differs from the sealed deployment")
        evidence[Path(name).stem + "_sha256"] = digest
    witness = json.loads((root / "witness.json").read_bytes())
    if (witness.get("schema") != "native-graph-request-pages/1" or
            [(row["step"], row["graph_sha256"]) for row in witness["phases"]] !=
            [(step, row["graph_sha256"]) for step, row in enumerate(phases)]):
        raise ValueError("sealed program targets different phase graphs")
    evidence["expected_pages"] = sum(row["page_count"] for row in witness["phases"])
    return evidence


def request_inputs(table, prompt):
    count = int(next(table))
    if count != 639 or len(prompt) != 512 * 8:
        raise ValueError("expected exact P512/D128 input evidence")
    values = unpack("<512q", prompt)
    rows = {}
    for expected, line in enumerate(table):
        step, page, position, mode, _, word, offset = (int(field, 16) for field in line.split())
        if (position != expected or (step, page) in rows or not 0 <= word <= 1020 or
                (position < 512 and (step != 0 or mode != 1 or offset != 4 * (position % 16))) or
                (position >= 512 and (step, page, mode, offset) != (position - 511, 0, 2, 8))):
            raise ValueError("invalid sealed prompt or retirement input binding")
        if mode == 1:
            start = position - position % 16
            data = pack("<16I", *values[start:start+16])
            rows[step, page] = [(word+i, int.from_bytes(data[16*i:16*i+16], "little")) for i in range(4)]
        else:
            rows[step, page] = [(word, None)]
    if len(rows) != count:
        raise ValueError("sealed native input binding is incomplete")
    return rows


def verify_pages(lines, program, evidence, signatures=None, inputs=None):
    """Audit actual accepted page bindings and terminals while extracting tokens."""
    expected = next(program, None)
    active = None
    phase = -1
    last_page_cycle = -1
    retired = 0
    complete = False
    observed_calls = {}
    index_commits = []
    input_token = 0
    observed_inputs = 0
    for line in lines:
        name, _, _ = line.strip().partition(" ")
        if name == "NATIVE_SERVICE_COUNT" and signatures is not None:
            fields = [field.split("=", 1) for field in line.split()[1:]]
            if (complete or active is not None or expected is not None or
                    tuple(key for key, _ in fields) != ("target", "schema", "abi", "opcode", "calls")):
                raise ValueError("unexpected native service count")
            *key, calls = (int(value) for _, value in fields)
            key = tuple(key)
            if key in observed_calls or calls <= 0:
                raise ValueError("invalid native service count")
            observed_calls[key] = calls
        elif name in PAGE_EVENTS:
            fields = line.split()[1:]
            keys = PAGE_EVENTS[name]
            pairs = [field.split("=", 1) for field in fields]
            if tuple(key for key, _ in pairs) != keys:
                raise ValueError(f"malformed {name}")
            row = [int(value, 16 if key == "data" else 10) for key, value in pairs]
            cycle = row[-1]
            if complete or cycle <= last_page_cycle:
                raise ValueError("native page events are out of order")
            last_page_cycle = cycle
            if name == "NATIVE_PAGE_LAUNCH":
                if active is not None or tuple(row[:-1]) != expected or row[0] != phase:
                    raise ValueError(f"launch differs from sealed program at generation {row[2]}")
                if inputs is not None:
                    bindings = inputs.get(tuple(row[:2]), ())
                    expected_index = [(word, input_token << 64 if data is None else data)
                                      for word, data in bindings]
                    if index_commits != expected_index:
                        raise ValueError(f"launch lacks actual SRAM input commit at generation {row[2]}")
                    observed_inputs += bool(bindings)
                    index_commits.clear()
                active = row[2]
            elif name == "NATIVE_INPUT_COMMIT":
                if (inputs is None or active is not None or expected is None or tuple(row[:3]) != expected[:3]
                        or row[0] != phase or not 0 <= row[4] < 1 << 128):
                    raise ValueError("SRAM input commit does not target the offered page")
                index_commits.append(tuple(row[3:5]))
            elif name == "NATIVE_PAGE_COMMIT":
                if active != row[0] or row[1] != 0:
                    raise ValueError("native page has no matching successful terminal")
                evidence["page_count"] = active
                active = None
                expected = next(program, None)
            else:
                if active is not None or expected is not None or row[:2] != [retired, 0]:
                    raise ValueError("native request did not complete its sealed pages")
                complete = True
        elif name in EVENTS:
            _, row = next(execution_events((line,)))
            if row["cycle"] <= last_page_cycle or complete:
                raise ValueError("native phase event is out of order")
            last_page_cycle = row["cycle"]
            if name == "NATIVE_PHASE_START":
                phase = row["step"]
                input_token = row["input"]
                if expected is None or expected[:2] != (phase, 0):
                    raise ValueError("native phase has no matching sealed program")
            elif name == "NATIVE_PHASE_COMMIT":
                if active is not None or (expected is not None and expected[0] <= phase):
                    raise ValueError("native phase committed before all its pages")
            elif name == "NATIVE_TOKEN_RETIRE":
                retired += 1
        yield line
    if not complete or evidence.get("page_count") != evidence.get("expected_pages"):
        raise ValueError("missing successful native request completion")
    if inputs is not None:
        if index_commits or observed_inputs != len(inputs):
            raise ValueError("native request lacks accepted SRAM input writes")
        evidence["input_pages"] = observed_inputs
    if signatures is not None:
        expected_calls = Counter()
        for row in signatures:
            expected_calls[tuple(row[key] for key in ("target", "schema", "abi", "opcode"))] += row["calls"]
        if observed_calls != expected_calls:
            raise ValueError("executed native service counts differ from the sealed descriptors")
        evidence["native_calls"] = sum(observed_calls.values())


def execution_events(lines):
    for line in lines:
        name, *fields = line.split()
        if name not in EVENTS:
            continue
        try:
            pairs = [field.split("=", 1) for field in fields]
            if tuple(key for key, _ in pairs) != EVENTS[name]:
                raise ValueError
            yield name, {key: int(value) for key, value in pairs}
        except ValueError as error:
            raise ValueError(f"malformed native execution event {name}") from error


def extract(lines, state, identity):
    """Require every sealed phase to commit and retire a live dependent token."""
    if state.get("schema") != "native-state-rows/1" or not state["phases"]:
        raise ValueError("native execution requires a sealed persistent state contract")
    ddr_clock = None

    def native_lines():
        nonlocal ddr_clock
        for line in lines:
            if not line.strip():
                continue
            name, *fields = line.split()
            if name != "DDR_CLOCK_PROOF":
                yield line
                continue
            pairs = [field.split("=", 1) for field in fields]
            if ddr_clock is not None or tuple(key for key, _ in pairs) != (
                    "period_ps", "first_edge_ps", "last_edge_ps", "steps"):
                raise ValueError("missing or duplicate synchronized DDR clock proof fields")
            ddr_clock = {key: int(value) for key, value in pairs}

    events = iter(execution_events(native_lines()))
    last_cycle = last_ps = -1
    core_period_ps = None

    def take(expected):
        nonlocal last_cycle, last_ps, core_period_ps
        entry = next(events, None)
        if entry is None:
            raise ValueError(f"incomplete native execution before {expected}")
        kind, row = entry
        if kind != expected or row["cycle"] <= last_cycle or row["ps"] <= last_ps:
            raise ValueError(f"native execution order differs at {expected}")
        if last_cycle >= 0:
            period, remainder = divmod(row["ps"] - last_ps, row["cycle"] - last_cycle)
            if remainder or period <= 0 or core_period_ps not in (None, period):
                raise ValueError("native events use inconsistent simulation clock timestamps")
            core_period_ps = period
        last_cycle, last_ps = row["cycle"], row["ps"]
        return row

    request = take("NATIVE_REQUEST_START")
    job, phases, retirements = request["job"], [], []
    for step, declared in enumerate(state["phases"]):
        start = take("NATIVE_PHASE_START")
        commit = take("NATIVE_PHASE_COMMIT")
        retire = take("NATIVE_TOKEN_RETIRE")
        phase = "decode" if step else "prefill"
        previous_token = retirements[-1]["token"] if step else None
        kv = {row["first_position"] + row["positions"] for row in declared["appends"]}
        if (job <= 0 or declared["phase"] != phase
                or any((row["job"], row["step"]) != (job, step) for row in (start, commit, retire))
                or (step and start["input"] != previous_token)
                or kv != {commit["kv"]} or retire["token"] != commit["token"]):
            raise ValueError(f"native phase {step} differs from the live token or KV contract")
        if not step:
            prefill_complete_ps = commit["ps"]
        phases.append(dict(step=step, graph_sha256=declared["graph_sha256"],
                           start_cycle=start["cycle"], start_ps=start["ps"],
                           terminal_cycle=commit["cycle"], terminal_ps=commit["ps"],
                           retired_cycle=retire["cycle"], retired_ps=retire["ps"]))
        retirements.append(dict(run_id=identity["run_id"], step=step, phase=phase, input_token=previous_token,
                                token=retire["token"], kv_length=commit["kv"], core_cycle=retire["cycle"],
                                time_ps=retire["ps"]))
    if next(events, None) is not None:
        raise ValueError("extra native events after the sealed request")
    timing = dict(phases=phases, start_ps=request["ps"], start_cycle=request["cycle"],
                  core_period_ps=core_period_ps, prefill_complete_ps=prefill_complete_ps)
    if ddr_clock is not None:
        timing["ddr_clock"] = ddr_clock
    return retirements, timing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("rtl_log", "state_inputs", "identity", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--program-dir", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    args = parser.parse_args()
    state = args.state_inputs.read_bytes()
    state_contract = json.loads(state)
    identity = json.loads(args.identity.read_bytes())
    binding = {key: identity[key] for key in ("run_id", "deployment_sha256", "checkpoint_sha256")}
    mother = args.program_dir / "mother-pages.tsv"
    targets = args.program_dir / "mother-targets.tsv"
    program_evidence = program_binding(args.program_dir, binding["deployment_sha256"], state_contract["phases"])
    signatures = json.loads((args.program_dir / "service-signatures.json").read_bytes())
    with (args.program_dir / "input-index.tsv").open(encoding="ascii") as table:
        inputs = request_inputs(table, args.prompt.read_bytes())
    with args.rtl_log.open(encoding="utf-8") as stream, \
            mother.open(encoding="utf-8") as images, targets.open(encoding="utf-8") as masks:
        retirements, timing = extract(
            verify_pages(stream, program_pages(images, masks), program_evidence, signatures, inputs), state_contract, binding)
    timing["program_execution"] = program_evidence
    rows = b"".join(json.dumps(row, sort_keys=True).encode() + b"\n" for row in retirements)
    binding["retirements_sha256"] = sha256(rows).hexdigest()
    timing.update(binding=binding, state_inputs_sha256=sha256(state).hexdigest())
    args.output.mkdir()
    (args.output / "retirements.jsonl").write_bytes(rows)
    (args.output / "phase-cycles.json").write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
