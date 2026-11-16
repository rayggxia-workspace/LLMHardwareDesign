"""Instrument and audit DMA/DDR transport events in the frozen Qwen3 TLM."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


FIELDS = ("submitted", "accepted", "completed", "queued", "inflight",
          "queue_beat_ps", "inflight_beat_ps")
REPLAY_NAMES = {
    "prefill": "prefill-w4-tile128-pr272-combined",
    "decode": "decode-live-w4-tile128-pr272-combined",
}


def instrument(source, destination):
    text = source.read_text(encoding="utf-8")

    def patch(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError(f"frozen bridge anchor mismatch: {old[:100]}")
        text = text.replace(old, new)

    patch("    unsigned history_count = 0;\n", """    unsigned history_count = 0;
    std::array<uint64_t, 2> submitted{}, accepted{}, completed{};
    std::array<uint64_t, 2> queue_ps{}, inflight_ps{};
""")
    patch("        queue.push_back({id, address, queued_ps, write != 0});",
          """        queue.push_back({id, address, queued_ps, write != 0});
        ++channels_[channel].submitted[write];""")
    patch("            // Never allow a Python callback",
          """            const unsigned active_mask = unsigned(!channels_[0].pending.empty()) |
                                         (unsigned(!channels_[1].pending.empty()) << 1);
            ++active_masks_[active_mask];
            // Never allow a Python callback""")
    patch("""            << channels_[1].device->EnergySnapshot() << "]}\\n";""",
          r"""            << channels_[1].device->EnergySnapshot() << "],\"dma_observation\":{\"active_mask_ticks\":["
            << active_masks_[0] << "," << active_masks_[1] << "," << active_masks_[2] << "," << active_masks_[3]
            << "],\"issue_throttle_ticks\":" << stats_[issue_throttle]
            << ",\"credit_wait_ticks\":" << stats_[credit_wait]
            << ",\"dram_backpressure_ticks\":" << stats_[dram_backpressure] << ",\"channels\":[";
        for (unsigned index = 0; index < channels_.size(); ++index) {
            if (index) out << ",";
            const auto& channel = channels_[index];
            auto queue_integral = channel.queue_ps;
            auto inflight_integral = channel.inflight_ps;
            std::array<uint64_t, 2> queued{}, inflight{};
            for (const auto& request : channel.offered) {
                ++queued[request.write];
                if (request.queued_ps < now_) queue_integral[request.write] += now_ - request.queued_ps;
            }
            for (const auto& pending : channel.pending) {
                ++inflight[pending.key & 1];
                inflight_integral[pending.key & 1] += now_ - pending.admitted_ps;
            }
            out << "[";
            for (unsigned direction = 0; direction < 2; ++direction) {
                if (direction) out << ",";
                out << "{\"submitted\":" << channel.submitted[direction]
                    << ",\"accepted\":" << channel.accepted[direction]
                    << ",\"completed\":" << channel.completed[direction]
                    << ",\"queued\":" << queued[direction]
                    << ",\"inflight\":" << inflight[direction]
                    << ",\"queue_beat_ps\":" << queue_integral[direction]
                    << ",\"inflight_beat_ps\":" << inflight_integral[direction] << "}";
            }
            out << "]";
        }
        out << "]}}\n";""")
    patch("        ++stats_[request.write ? writes : reads];",
          """        ++stats_[request.write ? writes : reads];
        ++channel.accepted[request.write];
        channel.queue_ps[request.write] += now_ - request.queued_ps;""")
    patch("        ++stats_[callbacks];",
          """        ++stats_[callbacks];
        ++channel.completed[write];
        channel.inflight_ps[write] += now_ - found->admitted_ps;""")
    patch("    std::array<Channel, 2> channels_{};", """    std::array<Channel, 2> channels_{};
    std::array<uint64_t, 4> active_masks_{};""")
    destination.write_text(text, encoding="utf-8")


def get_json(path):
    return json.loads(path.read_bytes())


def file_sha256(path):
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_plan_equivalence(old, new, reference, observed):
    assets = [(root / "assets").resolve() for root in (old, new)]
    plans = []
    for directory, result in zip(assets, (reference, observed)):
        plan = directory / "plan.json"
        if file_sha256(plan) != result["plan_sha256"]:
            raise ValueError(f"plan hash differs from replay result: {plan}")
        plans.append(get_json(plan))

    before, after = plans
    if len(before["images"]) != len(after["images"]):
        raise ValueError("compiled plan image count differs")
    for old_image, new_image in zip(before["images"], after["images"]):
        if old_image["path"] == new_image["path"]:
            continue
        relative = []
        for image, directory in zip((old_image, new_image), assets):
            path = Path(image["path"]).resolve()
            relative.append(path.relative_to(directory))
            if path.stat().st_size != image["bytes"] or file_sha256(path) != image["sha256"]:
                raise ValueError(f"relocated plan asset changed: {path}")
            image["path"] = str(relative[-1])
        if relative[0] != relative[1]:
            raise ValueError("compiled plan asset was relocated to a different relative path")

    if before != after:
        raise ValueError("compiled plans differ after checking relocated asset contents")


def compare_replay(old, new, mode):
    reference = get_json(old / "result.json")
    observed = get_json(new / "result.json")
    check_plan_equivalence(old, new, reference, observed)
    changed = sorted(key for key in (reference.keys() | observed.keys()) - {"plan_sha256"}
                     if key not in reference or key not in observed or reference[key] != observed[key])
    if changed or get_json(old / "layer-trace.json") != get_json(new / "layer-trace.json"):
        raise ValueError(f"instrumentation changed the {mode} replay or layer trace: {changed}")
    expected = ("start", "prefill_end", "end") if mode == "prefill" else ("start", "retire_1", "retire_2", "end")
    snapshots = {}
    for name in expected:
        file = "energy-" + name + ".json"
        baseline = get_json(old / file)
        state = get_json(new / file)
        probe = state.pop("dma_observation")
        if baseline != state:
            raise ValueError(f"instrumentation changed the DDR snapshot: {mode}/{name}")
        if len(probe["channels"]) != 2 or any(len(channel) != 2 for channel in probe["channels"]):
            raise ValueError("expected read/write counters for each channel")
        for rows in probe["channels"]:
            for row in rows:
                if set(row) != set(FIELDS) or min(row.values()) < 0:
                    raise ValueError(f"bad counters: {row}")
                if (row["submitted"] != row["queued"] + row["accepted"]
                        or row["accepted"] != row["inflight"] + row["completed"]):
                    raise ValueError(f"flow accounting does not close: {row}")
        if sum(probe["active_mask_ticks"]) * state["tick_ps"] != state["device_ps"]:
            raise ValueError("channel occupancy does not cover elapsed DDR time")
        snapshots[name] = dict(state, dma_observation=probe)

    start, end = snapshots["start"], snapshots["end"]
    final = end["dma_observation"]
    if start["replay_ps"] or any(row["queued"] or row["inflight"]
                                for rows in final["channels"] for row in rows):
        raise ValueError(f"nonempty replay boundaries: {mode}")
    for direction, key in enumerate(("reads", "writes")):
        if sum(rows[direction]["accepted"] for rows in final["channels"]) != reference["ddr"][key]:
            raise ValueError(f"terminal {key} do not match the frozen replay")
    if sum(row["completed"] for rows in final["channels"] for row in rows) != reference["ddr"]["callbacks"]:
        raise ValueError("terminal returns do not match the frozen replay")
    return snapshots


def window(start, end, tokens):
    a, b = (snap["dma_observation"] for snap in (start, end))
    elapsed_ps = end["replay_ps"] - start["replay_ps"]
    device_elapsed_ps = end["device_ps"] - start["device_ps"]
    if elapsed_ps <= 0 or device_elapsed_ps <= 0:
        raise ValueError("empty window")
    rows = []
    for before, after in zip(a["channels"], b["channels"]):
        directions = {}
        for direction, x, y in zip(("read", "write"), before, after):
            deltas = {key: y[key] - x[key] for key in
                      ("submitted", "accepted", "completed", "queue_beat_ps", "inflight_beat_ps")}
            if min(deltas.values()) < 0:
                raise ValueError(f"counter reset inside window: {direction}")
            if (x["queued"] + deltas["submitted"] != deltas["accepted"] + y["queued"]
                    or x["inflight"] + deltas["accepted"] != deltas["completed"] + y["inflight"]):
                raise ValueError("window failed flow accounting")
            directions[direction] = dict(deltas, queued_start=x["queued"], queued_end=y["queued"],
                                         inflight_start=x["inflight"], inflight_end=y["inflight"])
        rows.append(directions)
    masks = [end_count - start_count for start_count, end_count in
             zip(a["active_mask_ticks"], b["active_mask_ticks"])]
    if min(masks) < 0 or sum(masks) * end["tick_ps"] != device_elapsed_ps:
        raise ValueError("window failed occupancy accounting")
    waits = {key: b[key] - a[key] for key in ("issue_throttle_ticks", "credit_wait_ticks", "dram_backpressure_ticks")}
    if min(waits.values()) < 0:
        raise ValueError("wait counters reset inside window")
    return dict(start_ps=start["replay_ps"], end_ps=end["replay_ps"], elapsed_ps=elapsed_ps,
                device_elapsed_ps=device_elapsed_ps, tokens=tokens, ddr_tick_ps=end["tick_ps"],
                channels=rows, active_mask_ticks=dict(zip(("none", "channel0_only", "channel1_only", "both"), masks)),
                channel_wait_ddr_ticks=waits)


def audit(original, instrumented, output):
    stages = {mode: compare_replay(original / name, instrumented / name, mode)
              for mode, name in REPLAY_NAMES.items()}
    prefill, decode = stages["prefill"], stages["decode"]
    result = {
        "scope": "frozen Qwen3-0.6B TLM DDR transport (requests and DRAMsim3 admissions/callbacks)",
        "note": "Queue/inflight integrals use DDR time; no per-P RTL activity or per-bit transitions.",
        "prefill": window(prefill["start"], prefill["prefill_end"], 2),
        "first_token": window(decode["start"], decode["retire_1"], 1),
        "decode": window(decode["retire_1"], decode["retire_2"], 1),
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    patcher = commands.add_parser("instrument")
    patcher.add_argument("source", type=Path)
    patcher.add_argument("destination", type=Path)
    auditor = commands.add_parser("audit")
    auditor.add_argument("original", type=Path)
    auditor.add_argument("instrumented", type=Path)
    auditor.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "instrument":
        instrument(args.source, args.destination)
    elif args.command == "audit":
        audit(args.original, args.instrumented, args.output)
    else:
        parser.error("choose instrument or audit")
