"""Predict the admitted A2 MC/LC + P/S/M fixture from its two binary images."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from a2_images import read_images
from s_arbiter import Request, simulate as simulate_arbiter


class ProgramMemory:
    def __init__(self, kind, stall, trace):
        self.kind, self.stall, self.trace = kind, stall, trace

    def read(self, ready, address, size=16):
        if size <= 0 or size % 16 or address < 0 or address % 16:
            raise ValueError("unaligned PM transaction")
        for offset in range(address, address + size, 16):
            # network_pm registers a single outstanding request and an output.
            accepted = ready + (-ready % 5 if self.stall else 0)
            self.trace(accepted, self.kind, offset)
            response = accepted + self.stall + 3
            ready = response + 1
        return response


def payload(raw):
    a = struct.unpack_from("<8b", raw)
    b0 = struct.unpack_from("<8b", raw, 64)
    b1 = struct.unpack_from("<8b", raw, 72)
    dot = lambda b: sum(x * y for x, y in zip(a, b))
    data = struct.pack("<2q", dot(b0), dot(b1))
    return data[::-1].hex()


def predict(image, seed, job, sequence, start, stall, call_boundary=False):
    """Return pre-edge handshakes. `start` is an accepted host START or historical CALL."""
    if (len(seed) != 144 or type(stall) is not int or stall not in (0, 1, 2)
            or type(start) is not int or start < 0):
        raise ValueError("invalid A2 fixture input")
    if any(seed[8:64]) or any(seed[80:128]):
        raise ValueError("unsupported nonzero padding in A2 source tile")
    events = []

    def emit(cycle, kind, *args):
        events.append((cycle, kind, tuple(map(str, args))))

    mc_pm = ProgramMemory("MCPM", stall, emit)
    lc_pm = ProgramMemory("LCPM", stall, emit)
    size = image["instruction_bytes"]
    wide = image["ports"]["wide"]
    narrow = image["ports"]["narrow"]
    if (wide["read_order"] != ["b", "a"] or wide["banks"] != [0, 1, 2, 3]
            or narrow["write_client"] != 0 or narrow["host_client"] != 3):
        raise ValueError("unsupported A2 resource mapping")
    mc_base = image["mc_instruction_offset"]
    lc_base = image["lc_instruction_offset"]
    mc_token = image["mc_token"]
    lc_token = image["lc_token"]
    epoch = 1
    if call_boundary:
        call = start
    else:
        emit(start, "START", job, epoch, sequence)
        call = mc_pm.read(start + 1, mc_base) + 2
    emit(call, "CALL", job, epoch, sequence, mc_token)
    mc_wait = mc_pm.read(call + 1, mc_base + size) + 1

    task = lc_pm.read(call + 1, image["task_offset"], image["task_bytes"])
    exec_word = lc_pm.read(task + 2, lc_base)
    exec_desc = lc_pm.read(exec_word + 2, image["execution_offset"], image["execution_bytes"])
    execute = exec_desc + 2
    emit(execute, "EXEC", job, epoch, sequence, 0, lc_token)
    lc_wait = lc_pm.read(execute + 1, lc_base + size) + 2

    # The exclusive feeder reads B then A on the shared S wide port. A successor
    # may be accepted on the edge that takes the previous read's response.
    load = execute + 1
    b_read, a_read = load + 1, load + 2
    emit(load, "LOAD", image["a_word"], image["b_word"])
    emit(b_read + 2, "B", seed[64:128][::-1].hex())
    emit(a_read + 2, "A", seed[:16][::-1].hex())
    fed = a_read + 4
    emit(fed, "FED", 0)
    # M START traverses product/reduce/partial, four scale inputs and four
    # commits, then DRAIN. READ_RAW has one registered response edge.
    cmd = fed + 1
    native_done = cmd + 13
    emit(cmd, "CMD", 10, "9284")
    emit(native_done, "NATIVE", 0, 0, "0" * 32)
    raw_cmd = native_done + 1
    emit(raw_cmd, "CMD", 3, "0")
    word = payload(seed)
    emit(raw_cmd + 1, "NATIVE", 0, 0, word)

    write_offer = raw_cmd + 2
    write_accept = write_offer + stall * 3
    destination = narrow["dst_row"] * image["ports"]["banks"] + narrow["dst_bank"]
    if destination != image["dst_word"]:
        raise ValueError("A2 destination bank/row mismatch")
    for edge in range(write_offer, write_accept):
        emit(edge, "WHELD", destination, word)
    # This legacy S registers its narrow response on the SEND edge. The
    # 1-edge peer differs from the later SRAM used by the two-U comparison.
    response_ready = write_accept + 2
    ack_hold = [(response_ready, response_ready + stall * 6 - 1)] if stall else []
    events_s = simulate_arbiter([[Request(write_accept, 0, destination, 1)], [], [], []], [],
                                [ack_hold, [], [], []], response_latency=1)
    write, _, ack = [event["cycle"] for event in events_s]
    emit(write, "WRITE", destination, word)
    for edge in range(response_ready, ack):
        emit(edge, "HELD", word)
    emit(ack, "ACK", word)
    returned = ack + 1
    reads, writes = 128, 16
    emit(returned, "RETURN", job, epoch, sequence, 0, lc_token, 0, reads, writes)

    lc_end = lc_pm.read(max(lc_wait, returned + 1) + 1, lc_base + 2 * size)
    terminal = lc_end + 2 + stall * 5
    emit(terminal, "TERMINAL", job, epoch, sequence, mc_token, 0, reads, writes)
    mc_end = mc_pm.read(max(mc_wait, terminal + 1) + 1, mc_base + 2 * size)
    result = mc_end + 4 + stall
    emit(result, "RESULT", job, epoch, sequence, 0, reads, writes)
    return events, result


def observed_jobs(log, mode):
    summaries = re.findall(r"^PASS A2 jobs=(\d+) status=0 cycles=\d+$", log, re.M)
    if len(summaries) != 1 or "%Fatal" in log or "%Error" in log:
        raise ValueError("RTL log has no successful A2 result")
    groups, active = [], []
    boundary = "CALL" if mode == "call" else "START"
    for line in log.splitlines():
        if not line.startswith("A2 "):
            continue
        _, cycle, kind, *args = line.split()
        cycle = int(cycle)
        if not active and kind in ("READBACK", "MCPM", "LCPM"):
            continue
        if kind == boundary:
            if active:
                raise ValueError("nested job boundary")
            active = [(cycle, kind, tuple(args))]
        elif active:
            if cycle < active[-1][0]:
                raise ValueError("RTL job cycles are out of order")
            active.append((cycle, kind, tuple(args)))
            if kind == "RESULT":
                groups.append(active)
                active = []
        else:
            raise ValueError("event before job boundary: " + kind)
    if active or not groups or len(groups) != int(summaries[0]):
        raise ValueError("empty or incomplete RTL log")
    return groups


def compare(directory, log_path, stall, mode):
    image = read_images(directory)
    seed = (directory / "seed.bin").read_bytes()
    raw_log = log_path.read_bytes()
    observed = observed_jobs(raw_log.decode("ascii"), mode)
    if len(seed) != 144 * len(observed):
        raise ValueError("seed job count disagrees with RTL log")
    results = []
    for index, job in enumerate(observed):
        start, _, identifiers = job[0]
        job_id, epoch, sequence = map(int, identifiers[:3])
        if (job_id, epoch, sequence) != (7 + index, 1, 1 + index):
            raise ValueError("unexpected job context")
        expected, terminal = predict(image, seed[144 * index:144 * (index + 1)], job_id,
                                     sequence, start, stall, call_boundary=mode == "call")
        if mode == "call":
            expected = [row for row in expected if row[1] not in ("MCPM", "LCPM")]
        # Independent interfaces can emit in either order within the same edge.
        differences = (Counter(expected) - Counter(job)) + (Counter(job) - Counter(expected))
        if differences:
            edge = min(row[0] for row in differences)
            raise ValueError("job {} first mismatch at edge {}: predicted {}, RTL {}".format(
                job_id, edge, [row[1:] for row in expected if row[0] == edge],
                [row[1:] for row in job if row[0] == edge]))
        results.append({"job": job_id, "boundary": mode, "start_cycle": start,
                        "result_cycle": terminal, "cycles": terminal - start,
                        "event_count": len(expected), "max_cycle_error": 0})
    return {"stall": stall, "images": image, "seed_sha256": hashlib.sha256(seed).hexdigest(),
            "log_sha256": hashlib.sha256(raw_log).hexdigest(), "jobs": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--stall", type=int, required=True)
    parser.add_argument("--boundary", choices=("start", "call"), default="start")
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.directory, args.log or args.directory / "run.log", args.stall,
                                 args.boundary), indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, "A2 cycle comparison failed: {}\n".format(exc))
