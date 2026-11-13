"""Audit clock crossings and DMA visibility against DRAMsim3's physical command trace."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


# Frozen DDR4 configuration: tCK=630 ps, AL=0, CL=22, CWL=16, BL=8.
# The trace uses controller clk_ before ClockTick; the bridge numbers ticks
# after ClockTick. A data tail is therefore trace edge + 1 + (CL/CWL + BL/2).
READ_DELAY = 26
WRITE_DELAY = 20
COMMANDS = {"read": False, "read_p": False, "write": True, "write_p": True}
BEAT_BYTES = 64


def require(condition, message):
    if not condition:
        raise ValueError(message)


def next_sample(time, period, phase, stages):
    """Return the edge of the final sync stage after the source transition."""
    # Times use a common exact integer unit of one third of a picosecond.
    return max(0, (time - phase) // period + 1) + stages - 1


def dram_commands(path):
    rows = Counter()
    for line in path.read_text(encoding="ascii").splitlines():
        edge, op, channel, rank, group, bank, row, column = line.split()
        if op not in COMMANDS:
            continue
        require(int(channel) == 0, "unexpected channel in the pinned command trace")
        rank, group, bank, row, column = int(rank), int(group), int(bank), int(row, 16), int(column, 16)
        require(0 <= rank < 2 and 0 <= group < 4 and 0 <= bank < 4 and
                0 <= row < 65536 and 0 <= column < 128, "out-of-range DDR trace address")
        # ro|ch|ra|ba|bg|co, with 16|0|1|2|2|7 bits after the 64B burst shift.
        burst_address = (row << 12) | (rank << 11) | (bank << 9) | (group << 7) | column
        rows[(COMMANDS[op], burst_address * BEAT_BYTES, int(edge) + 1)] += 1
    return rows


def expected_reads(beats):
    old = b"".join(bytes([0x11 + index]) * BEAT_BYTES for index in range(beats))
    new = b"".join(bytes([0x80 + index]) * BEAT_BYTES for index in range(beats))
    values = {"before": old, "after": new, "side": bytes([0x33]) * BEAT_BYTES}
    return {tag: hashlib.sha256(value).hexdigest() for tag, value in values.items()}


def check_cdc(events, phase, beats, issued):
    host, ddr, offset, stages = 10000, 630 * 3, phase * 3, 2
    # The addresses are part of the controlled stimulus. Read/write identity
    # must survive all four observed phases, including repeated addresses.
    tags = {("side", 0): (0x4000, False)}
    for tag in ("before", "store", "after"):
        tags.update({(tag, beat): (beat * BEAT_BYTES, tag == "store") for beat in range(beats)})
    progress = {tag: [] for tag in tags}
    order = ("host_accept", "ddr_accept", "ddr_complete", "host_complete")
    for event in events:
        identity = tuple(event["identifier"])
        require(identity in tags and (event["address"], event["write"]) == tags[identity]
                and type(event["write"]) is bool, "wrong identity, address or direction in CDC trace")
        seen = progress[identity]
        require(len(seen) < len(order) and event["event"] == order[len(seen)], "CDC phase skipped or repeated")
        seen.append(event)

    matches = Counter()
    crossings = {stage: [] for stage in order}
    addresses = {}
    for identity, stages_seen in progress.items():
        require(len(stages_seen) == len(order), "accepted transaction did not complete")
        offer, send, complete, retire = stages_seen
        address, write = tags[identity]
        offered, sent, done, retired = offer["cycle"], send["tick"], complete["tick"], retire["cycle"]
        require(all(type(value) is int and value >= 0 for value in (offered, sent, done, retired)),
                "invalid time coordinate")
        req_edge = next_sample(offered * host, ddr, offset, stages)
        rsp_edge = next_sample(offset + done * ddr, host, 0, stages)
        require(offer["request_ready_tick"] == req_edge and sent >= req_edge and done > sent
                and complete["host_ready_cycle"] == rsp_edge and retired >= rsp_edge,
                "CDC sampled too early or used an incorrect sync edge")
        command = done - (WRITE_DELAY if write else READ_DELAY)
        require(command > sent and (complete["command_tick"] == command if write
                                    else complete["command_tick"] is None),
                "data tail is not tied to the issued DDR command")
        matches[(write, address, command)] += 1
        crossings["host_accept"].append((offered, identity))
        crossings["ddr_accept"].append((sent, identity))
        crossings["ddr_complete"].append((done, identity))
        crossings["host_complete"].append((retired, identity))
        addresses.setdefault(address, []).append((offered, retired))
    require(matches == issued, "physical command trace differs from transaction completion projection")
    for name in ("host_accept", "ddr_accept", "host_complete"):
        require(len({edge for edge, _ in crossings[name]}) == len(tags), "CDC exceeds one handshake per edge")
    host_order = [identity for _, identity in sorted(crossings["host_accept"])]
    ddr_order = [identity for _, identity in sorted(crossings["ddr_accept"])]
    require(host_order == ddr_order, "request FIFO changed admission order")
    for windows in addresses.values():
        ordered = sorted(windows)
        require(all(left[1] < right[0] for left, right in zip(ordered, ordered[1:])),
                "same-address live requests overlap")

    # Every used slot survives its pop until the reverse credit is visible.
    request_slots, response_slots = [], []
    for offer, send, complete, retire in progress.values():
        req_end = next_sample(offset + send["tick"] * ddr, host, 0, stages)
        rsp_end = next_sample(retire["cycle"] * host, ddr, offset, stages)
        request_slots.append((offer["cycle"], req_end))
        response_slots.append((send["tick"], rsp_end))
    for slots in (request_slots, response_slots):
        require(all(sum(begin <= edge < end for begin, end in slots) <= 2 for edge, _ in slots),
                "CDC exceeded two reserved slots")
    return progress


def audit_case(case, directory, phase, beats):
    expected_config = {"phase_ps": phase, "host_period_ps": [10000, 3], "dram_period_ps": 630,
                       "request_depth": 2, "response_depth": 2, "request_sync_stages": 2,
                       "response_sync_stages": 2, "write_beats": beats}
    require(all(case[key] == value for key, value in expected_config.items()), "wrong declared clocks or FIFO fixture")
    require(case["commands"] == {"read_commands": 2 * beats + 1, "write_commands": beats},
            "wrong command statistics")
    require(case["data_checked"] == {"before": beats * BEAT_BYTES, "after": beats * BEAT_BYTES}
            and case["data_sha256"] == expected_reads(beats), "read payload does not distinguish old and new data")
    trace = directory / "dramsim3ch_0cmd.trace"
    issued = dram_commands(trace)
    progress = check_cdc(case["cdc_events"], phase, beats, issued)

    def edges(event, tag):
        return [row["cycle"] for row in case["model_events"] if row["event"] == event
                and row.get("tag", row.get("op")) == tag]

    def edge(event, tag):
        values = edges(event, tag)
        require(len(values) == 1, "missing or duplicate {} for {}".format(event, tag))
        return values[0]

    for tag in ("before", "store", "side", "after"):
        selected = [stages_seen for identity, stages_seen in progress.items() if identity[0] == tag]
        require(sorted(stages_seen[0]["cycle"] for stages_seen in selected) == edges("backend_accept", tag),
                "host DMA acceptance differs from the CDC trace")
        complete_kind = "write_visible" if tag == "store" else "read_return"
        expected = [stages_seen[-1]["cycle"] for stages_seen in selected]
        require(sorted(expected) == edges(complete_kind, tag) and max(expected) < edge("retire", tag),
                "host completion or descriptor retirement disagrees with CDC")
    fence_ready, fence_retire = edge("fence_ready", "fence"), edge("retire", "fence")
    latest_visible = max(edges("write_visible", "store"))
    first_read_after = min(edges("backend_accept", "after"))
    require(latest_visible < edge("retire", "store") < fence_ready < fence_retire < first_read_after,
            "FENCE did not drain older writes or gate younger same-address reads")
    require(edge("retire", "side") < fence_ready, "FENCE bypassed an older read")
    require(edge("retire", "after") < edge("issue", "dependent") < edge("complete", "dependent")
            == case["completion_cycle"], "read-dependent operation finished before data was visible")
    first_wr = min(command for (write, _, command) in issued if write)
    return {"command_trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest(),
            "checked_read_commands": 2 * beats + 1, "checked_write_commands": beats,
            "first_wr_controller_edge": first_wr - 1, "first_wr_bridge_tick": first_wr,
            "last_write_visible_host_cycle": latest_visible, "fence_ready_host_cycle": fence_ready,
            "fence_retire_host_cycle": fence_retire, "first_read_after_host_cycle": first_read_after,
            "last_host_cycle": case["completion_cycle"]}


def audit(result, directory):
    require(result["stock_read_reference"] == {"accepted": [[0, "first"], [50, "second"]],
             "returned": [[50, "first"], [78, "second"]], "write_rejected": True}
            and result["stock_coupled_cycle"] == 105, "stock read control changed")
    return {"schema": "issue265-dram-write-cdc-audit/1",
            **{name: audit_case(result[name], directory / name, phase, beats)
               for name, phase, beats in (("mixed", 0, 1), ("heldout", 173, 9))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("results_directory", type=Path)
    args = parser.parse_args()
    try:
        result = json.loads(args.result.read_text(encoding="utf-8"))
        print(json.dumps(audit(result, args.results_directory), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, "DDR command/CDC audit failed: {}\n".format(error))


if __name__ == "__main__":
    main()
