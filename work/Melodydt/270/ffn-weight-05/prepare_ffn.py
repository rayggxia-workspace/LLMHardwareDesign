"""Activate the sealed PR #260 weight-bank model on FFN pages only."""

import argparse
from pathlib import Path


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"expected one occurrence of {old!r}")
    return source.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("upstream", type=Path)
    args = parser.parse_args()
    read = lambda directory, name: (directory / name).read_text(encoding="utf-8")

    name = "native_tlm_projection.py"
    prior = read(args.source, name)
    projection = read(args.upstream, name)
    if prior[prior.index("def accumulate("):prior.index("class Projection:")] != (
            projection[projection.index("def accumulate("):projection.index("class Projection:")]):
        raise ValueError("sealed records use different arithmetic")
    for old, new in (
        ("                next_fetch, next_run, executing = 0, 0, False",
         "                next_fetch, next_run, executing = 0, 0, False\n"
         "                wait_start = self.clock.now"),
        ("                    nonlocal next_fetch, executing", "                    nonlocal next_fetch, executing, wait_start"),
        ("                        executing = True\n",
         "                        executing = True\n"
         "                        self.stats[\"weight_wait_ps\"] += self.clock.now - wait_start\n"),
        ("                    nonlocal next_run, executing", "                    nonlocal next_run, executing, wait_start"),
        ("                    executing = False\n                    advance()",
         "                    executing = False\n                    wait_start = self.clock.now\n                    advance()"),
    ):
        projection = replace_once(projection, old, new)

    ffn = read(args.upstream, "native_tlm_ffn.py")
    for old, new in (
        ("        self.mid_barrier_ps = 0", "        self.mid_barrier_ps = 0\n"
         "        self.active_batch = []\n        self.weight_batches = []"),
        ("                def finish():\n                    self.scope_count += 1",
         "                started = self.clock.now\n"
         "                wait_before = projection.stats[\"weight_wait_ps\"]\n"
         "                returns_before = projection.stats[\"weight_read_returns\"]\n"
         "                def finish():\n"
         "                    self.active_batch.append(dict(\n"
         "                        target=target, kind=\"down\" if ways == 1 else \"gate_up\",\n"
         "                        start_ps=started, terminal_ps=self.clock.now,\n"
         "                        weight_wait_ps=projection.stats[\"weight_wait_ps\"]-wait_before,\n"
         "                        weight_beats=projection.stats[\"weight_read_returns\"]-returns_before))\n"
         "                    self.scope_count += 1"),
        ("    def after_wait(self):\n        if not self.stripe:",
         "    def after_wait(self):\n"
         "        if self.active_batch:\n"
         "            if (sorted(row[\"target\"] for row in self.active_batch) != [0, 1, 2] or\n"
         "                    len({row[\"kind\"] for row in self.active_batch}) != 1):\n"
         "                raise ValueError(\"FFN WAIT does not retire exactly one three-P batch\")\n"
         "            self.weight_batches.append(dict(wait_end_ps=self.clock.now, projections=self.active_batch))\n"
         "            self.active_batch = []\n"
         "        if not self.stripe:"),
    ):
        ffn = replace_once(ffn, old, new)

    runner = read(args.source, "run_native_tlm_request.py")
    for old, new in (
        ('    parser.add_argument("--pipeline-memory", action="store_true")',
         '    parser.add_argument("--pipeline-memory", action="store_true")\n'
         '    parser.add_argument("--ffn-rtl-weight-fetch", action="store_true")'),
        ("ffn = FFN(clock, dram, memory, u, banks, dma, activation)",
         "ffn = FFN(clock, dram, memory, u, banks, dma, activation,\n"
         "                              rtl_weight_fetch=args.ffn_rtl_weight_fetch)"),
        ("                timing_file.write(json.dumps(dict(",
         "                if ffn is not None:\n"
         "                    if ffn.active_batch or len(ffn.weight_batches) != 64:\n"
         "                        raise ValueError(\"FFN batches did not drain\")\n"
         "                    with (args.out / \"ffn-weight-timing.jsonl\").open(\"a\", encoding=\"ascii\") as metrics:\n"
         "                        metrics.write(json.dumps(dict(step=step, page=index,\n"
         "                                                      batches=ffn.weight_batches))+ \"\\n\")\n"
         "                timing_file.write(json.dumps(dict("),
        ('                elif descriptor[:4] == b"FDS8":\n                    awaiting_residual = True',
         '                elif descriptor[:4] == b"FDS8":\n                    awaiting_residual = True\n'
         '                    down_address, = unpack_from("<Q", descriptor, 24)\n'
         '                    payload = b"".join(memory(down_address + offset) for offset in range(0, 8192, 64))\n'
         '                    from hashlib import sha256\n'
         '                    with (args.out / "ffn-down.sha256.jsonl").open("a", encoding="ascii") as hashes:\n'
         '                        hashes.write(json.dumps([step, index, sha256(payload).hexdigest()])+ "\\n")'),
    ):
        runner = replace_once(runner, old, new)
    for name, content in (
        ("native_tlm_projection.py", projection),
        ("native_tlm_ffn.py", ffn),
        ("run_native_tlm_request.py", runner),
    ):
        (args.source / name).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
