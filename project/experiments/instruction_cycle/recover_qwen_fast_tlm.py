"""Reconcile the complete 110666 trace after the post-close statistics bug."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from fast_tlm_replay import DramBridge


TRACE_SHA = "512dd64e4eff5db20837bd40ac263e5b83d6282a8a69218310ef782c951e8815"
PROGRESS_SHA = "67e458ad4469ad17ccd8bcfc485d371f921f1902742dec9b52d8e64f184bb4c4"
LOG_SHA = "c190e34da00be6ae7deafc57abe8c6538d499f2525a9b348e2cc6a91d7124605"
DEPLOYMENT_SHA = "74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef"
KV_SHA = "78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e"


def sealed(path, expected):
    payload = path.read_bytes()
    if sha256(payload).hexdigest() != expected:
        raise ValueError("unexpected digest for {}".format(path))
    return payload


def check_close(library, config, output):
    """Use the real two-channel C++ transport and verify stats after disposal."""
    clock = SimpleNamespace(sequence=iter(range(10000)), now=0, after=lambda _, done: done())
    ddr = DramBridge(clock, library, config, output, credits=32, core_ps=3334)
    payloads = ((0, None), (64, bytes(64)))
    callbacks = []
    for address, payload in payloads:
        ddr.submit(SimpleNamespace(address=address, payload=payload), lambda key=address: callbacks.append(key))
    while ddr.pending and ddr.next_tick <= 630 * 4096:
        ddr.advance(630 * 4096)
    before = ddr.stats
    ddr.close()
    after = ddr.stats
    after["reads"] = -1
    if (sorted(callbacks) != [0, 64] or ddr.stats != before or
            (before["reads"], before["writes"], before["callbacks"]) != (1, 1, 2)):
        raise ValueError("DDR counters did not survive drained close")
    return dict(before)


def recover(failed, kv, output):
    """Build the summary from the candidate trace, not the reference result."""
    timeline = sealed(failed / "decode/page-timing.jsonl", TRACE_SHA)
    progress = sealed(failed / "decode/progress.jsonl", PROGRESS_SHA)
    sealed(failed / "slurm-110666.out", LOG_SHA)
    binding = json.loads(sealed(kv, KV_SHA))
    pages = [json.loads(line) for line in timeline.splitlines()]
    retirements = [(row["token"], row["retirement_ps"])
                   for row in map(json.loads, progress.splitlines()) if "token" in row]
    if ([(row["step"], row["page"]) for row in pages] !=
            [(step, page) for step in (1, 2) for page in range(291)] or
            [p["end_ps"] for p in pages if p["page"] == 290] != [time for _, time in retirements]):
        raise ValueError("failed job lacks two complete phases and matching retirements")
    counts = Counter()
    for row in pages:
        counts.update(row["ddr"])
    if counts["reads"] + counts["writes"] != counts["callbacks"]:
        raise ValueError("candidate DDR transaction counts did not drain")
    first, second = binding["phases"][1:3]
    if [(phase["first"], phase["exclusive_end"], phase["rows"]) for phase in (first, second)] != [
            (512, 513, 1), (513, 514, 1)]:
        raise ValueError("unexpected sealed two-step KV geometry")
    # Both retirement markers are emitted only after the original runner's
    # per-step layer, vocabulary and live KV write/reread identity checks.
    result = dict(pages=len(pages), positions=second["exclusive_end"], retirements=retirements,
                  ddr=dict(counts), completed_layers_in_current_position=36,
                  timing_calibrated=False, numerically_accepted=False,
                  dma_scope="32 credits per channel and rolling issue limits with FIFO arbitration",
                  retirement_interval_ps=retirements[-1][1] - retirements[0][1], initial_history=first["first"],
                  kv_cross_step_read_beats=first["required_commits"] * binding["row_bytes"] // 64,
                  deployment_sha256=DEPLOYMENT_SHA, kv_binding_sha256=KV_SHA,
                  scope="two native mother program decode phases with modeled local services")
    output.mkdir()
    (output / "page-timing.jsonl").write_bytes(timeline)
    (output / "execution.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    for channel in ("channel0", "channel1"):
        shutil.copytree(failed / "decode" / channel, output / channel)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("failed", type=Path)
    parser.add_argument("kv", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    smoke = Path("close-smoke")
    smoke.mkdir()
    stats = check_close(args.library.resolve(), args.config.resolve(), smoke)
    (smoke / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="ascii")
    recover(args.failed, args.kv, Path("recovered"))


if __name__ == "__main__":
    main()
