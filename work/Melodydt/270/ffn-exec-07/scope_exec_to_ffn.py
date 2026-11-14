"""Scope the C639 arbitration trial to the fixture's actual FFN owner."""

import argparse
from pathlib import Path

from prepare_exec_priority import CONTROL
from prepare_native_probe import replace_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    replace_once(
        args.source / CONTROL,
        " wire first_exec_preempts_pair=first_exec_eligible&&!replay_prepared;",
        """ // Experiment fixture shares P0 with QKV/O. Observe its real ownership
 // handoff so the front half keeps exactly the baseline controller policy.
 wire first_exec_preempts_pair=first_exec_eligible&&!replay_prepared&&
      test_native_decode638_product_replay.ffn_owner;""",
    )


if __name__ == "__main__":
    main()
