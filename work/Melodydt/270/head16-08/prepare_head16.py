"""Instrument HEAD16 and enable the existing bounded WeightFetch only on that page."""

import argparse
from hashlib import sha256
from pathlib import Path


BASE = {
    "native_tlm_projection.py": "fcf1c313b46a9b74dd5e149e85b4aee15607963c53668d2b6758c8ace3ead4a3",
    "run_native_tlm_request.py": "25dc5f344db8afec16a7ec742f176c48fa74857da66410d2e3688382d2682e7d",
}


def edit(source, old, new):
    if source.count(old) != 1:
        raise ValueError("expected one occurrence of {}".format(old))
    return source.replace(old, new, 1)


def projection(source):
    for old, new in (
        ("            prefixes = [[0]", "            tile_enter = self.clock.now\n"
         "            prefixes = [[0]"),
        ("            def tile(k):\n", "            def tile(k):\n"
         "                nonlocal tile_enter\n                tile_enter = self.clock.now\n"),
        ("                slots = {}\n", "                if head16:\n"
         '                    self.stats["head_activation_ps"] += self.clock.now - tile_enter\n'
         "                slots = {}\n"),
        ("                    nonlocal next_fetch, executing, wait_start\n",
         "                    nonlocal next_fetch, executing, wait_start, exec_start\n"),
        ("                wait_start = self.clock.now\n\n",
         "                wait_start = self.clock.now\n                exec_start = wait_start\n\n"),
        ("                        self.edge(finish_group,",
         "                        exec_start = self.clock.now\n                        self.edge(finish_group,"),
        ("                    accumulate(data, activation, shift, prefixes[next_run], head16)",
         '                    if head16:\n                        self.stats["head_exec_ps"] += self.clock.now - exec_start\n'
         "                    accumulate(data, activation, shift, prefixes[next_run], head16)"),
        ("                if index == groups * ways:\n                    self.busy = False",
         '                if index == groups * ways:\n                    if head16:\n'
         '                        self.stats["head_output_write_ps"] += self.clock.now - tile_enter\n'
         "                    self.busy = False"),
    ):
        source = edit(source, old, new)
    return source


def runner(source):
    for old, new in (
        ("from collections import defaultdict", "from collections import Counter, defaultdict\nfrom hashlib import sha256"),
        ("        self.best = None\n", "        self.best = None\n        self.digest = sha256()\n"
         "        self.tiles = []\n"),
        ("        def run(done):\n            def projected():",
         """        def run(done):
            clock = self.projection.clock
            start = clock.now
            counters = self.projection.stats.copy()

            def projected():
                projected_ps = clock.now"""),
        ('                    for index, logit in enumerate(unpack("<128i", payload), first):',
         '''                    output_ps = clock.now
                    self.digest.update(payload)
                    for index, logit in enumerate(unpack("<128i", payload), first):'''),
        ("                    self.columns += 128\n                    done()",
         """                    self.columns += 128
                    elapsed = self.projection.stats - counters
                    event = dict(first=first, launch_ps=start, m_terminal_ps=projected_ps,
                                 read_done_ps=output_ps, argmax_done_ps=clock.now,
                                 activation_ps=elapsed["head_activation_ps"],
                                 weight_wait_ps=elapsed["weight_wait_ps"],
                                 m_exec_ps=elapsed["head_exec_ps"],
                                 write_ps=elapsed["head_output_write_ps"],
                                 weight_beats=elapsed["weight_read_returns"],
                                 records=elapsed["weight_records_consumed"])
                    self.tiles.append(event)
                    done()"""),
        ('    parser.add_argument("--ffn-rtl-weight-fetch", action="store_true")',
         '    parser.add_argument("--ffn-rtl-weight-fetch", action="store_true")\n'
         '    parser.add_argument("--head-rtl-weight-fetch", action="store_true")'),
        ("                    vocabulary = Vocabulary(projection)",
         """                    head_projection = Projection(clock, dram, memory, u, p0,
                                                 source_word=512, scratch_word=1008,
                                                 scratch_sram=p0,
                                                 rtl_weight_fetch=args.head_rtl_weight_fetch)
                    vocabulary = Vocabulary(head_projection)"""),
        ('                    log(dict(step=step, token=retired[-1][0], retirement_ps=clock.now))',
         '''                    with (args.out / "head16.jsonl").open("a", encoding="ascii") as trace:
                        trace.write(json.dumps(dict(step=step, page=index, columns=vocabulary.columns,
                                                    logits_sha256=vocabulary.digest.hexdigest(),
                                                    token=vocabulary.best[1], logit=vocabulary.best[0],
                                                    retirement_ps=clock.now, tiles=vocabulary.tiles)) + "\n")
                    log(dict(step=step, token=retired[-1][0], retirement_ps=clock.now))'''.replace(' + "\n")', ' + "\\n")')),
    ):
        source = edit(source, old, new)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    for name, render in (("native_tlm_projection.py", projection), ("run_native_tlm_request.py", runner)):
        path = args.source / name
        data = path.read_bytes()
        if sha256(data).hexdigest() != BASE[name]:
            raise ValueError("sealed FFN source changed: {}".format(path))
        path.write_text(render(data.decode("utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main()
