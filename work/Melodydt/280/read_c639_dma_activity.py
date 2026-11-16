"""Count settled C639 DMA transitions and pre-edge handshakes in an archived VCD."""
import json
from pathlib import Path
import sys


def inspect(wave, parent):
    widths = {"c_rsp_data": 6144, "c_req_valid": 12, "c_req_ready": 12,
              "c_rsp_valid": 12, "c_rsp_ready": 12, "d_req_valid": 4,
              "d_req_ready": 4, "d_rsp_valid": 4, "d_rsp_ready": 4, "clk": 1, "owner": 1}
    signals = {}
    state = {}
    updates = {}
    paths = []
    elapsed_edges = [0, 0]
    responses = [[0] * 12 for _ in elapsed_edges]
    flips = [[0] * 12 for _ in elapsed_edges]
    counts = [dict(client_requests=0, client_responses=0, ddr_requests=0, ddr_responses=0,
                   client_stalled_lane_cycles=0, ddr_stalled_lane_cycles=0,
                   concurrent_ddr_accept_cycles=0) for _ in elapsed_edges]
    period = 5000
    first = last = previous_edge = None

    def settle():
        nonlocal previous_edge
        value = state.get("c_rsp_data")
        if value is not None and "c_rsp_data" in updates:
            delta = updates["c_rsp_data"] ^ value
            dest = flips[updates.get("owner", state["owner"])]
            for lane in range(12):
                dest[lane] += (delta >> (512 * lane) & ((1 << 512) - 1)).bit_count()
        if state.get("clk") != updates.get("clk", state.get("clk")) and state:
            if previous_edge is not None and last - previous_edge != period:
                raise ValueError("C639 half-clock gap differs")
            previous_edge = last
            if updates["clk"] == 1:
                owner = state["owner"]
                elapsed_edges[owner] += 1
                row = counts[owner]
                for prefix, label in (("c", "client"), ("d", "ddr")):
                    valid = state[f"{prefix}_req_valid"]
                    ready = state[f"{prefix}_req_ready"]
                    accepted = (valid & ready).bit_count()
                    returned = state[f"{prefix}_rsp_valid"] & state[f"{prefix}_rsp_ready"]
                    row[f"{label}_requests"] += accepted
                    row[f"{label}_responses"] += returned.bit_count()
                    row[f"{label}_stalled_lane_cycles"] += (valid & ~ready).bit_count()
                    if prefix == "c":
                        for lane in range(12):
                            responses[owner][lane] += (returned >> lane) & 1
                    else:
                        row["concurrent_ddr_accept_cycles"] += accepted > 1
        state.update(updates)
        updates.clear()

    with wave.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ["$scope"]:
                paths.append(fields[2])
            elif fields[:1] == ["$upscope"]:
                paths.pop()
            elif fields[:1] == ["$var"]:
                scope = "/".join(paths)
                name = fields[4]
                if ((scope == parent and name == "owner") or
                        (scope == parent + "/dma" and name in widths and name != "owner")):
                    if int(fields[2]) != widths[name] or name in signals.values():
                        raise ValueError(f"wrong or duplicate DMA signal width: {name}")
                    signals[fields[3]] = name
            elif fields[:1] == ["$enddefinitions"]:
                break
        if set(signals.values()) != widths.keys():
            raise ValueError(f"missing DMA signals: {widths.keys() - set(signals.values())}")
        for line in stream:
            if line.startswith("#"):
                if last is not None:
                    settle()
                last = int(line[1:])
                if first is None:
                    first = last
            elif line[:1] in "01xz":
                name = signals.get(line[1:].strip())
                if name:
                    updates[name] = int(line[0], 2)
            elif line.startswith(("b", "B")):
                value, ident = line.split()
                if ident in signals:
                    updates[signals[ident]] = int(value[1:], 2)
        settle()

    if first is None or last <= first or sum(elapsed_edges) != (last - first) // (2 * period):
        raise ValueError("DMA activity does not span the full C639 sample")
    return {"begin_ps": first, "end_ps": last, "response_bus_bits": widths["c_rsp_data"],
            "local_clients": 12, "source_period_ps": 10000,
            "by_owner": [dict(owner=owner, core_cycles=elapsed_edges[owner],
                              response_events_by_lane=responses[owner],
                              response_bus_toggles_by_lane=flips[owner], **counts[owner])
                         for owner in (0, 1)]}


if __name__ == "__main__":
    print(json.dumps(inspect(Path(sys.argv[1]), sys.argv[2]), indent=2))
