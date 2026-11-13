"""Check the 24 transport-quiescence observations from the frozen #264 RTL bench."""

import argparse
from collections import namedtuple
import hashlib
import json
from pathlib import Path
import re


SOURCE_COMMIT = "69ce47aa7fda8d732997131a90206ec4895c2ed7"
Checkpoint = namedtuple("Checkpoint", "name quiescent generation beats descriptors held_fault")
CHECKPOINT = re.compile(
    r"^(.+?)\s+quiescent=([01]) generation=([0-9]+) beats=([0-9]+) "
    r"descriptors=([0-9]+) held_fault=([01])$"
)
PASS = "PASS typed DMA transport_quiescent"


def reference():
    """Protocol expectations from the directed stimulus and ownership rules."""
    # Cold generation 1 remains unready until the matching generation-2 purge.
    # A client return held in a skid still owns its live beat. Only accepted
    # CLOSE releases the corresponding incomplete legacy descriptor.
    return [Checkpoint(*row) for row in (
        ("cold after reset before purge", 0, 1, 0, 0, 0),
        ("cold purge offer stalled", 0, 1, 0, 0, 0),
        ("cold purge accepted in wait", 0, 1, 0, 0, 0),
        ("wrong purge completion", 0, 1, 0, 0, 0),
        ("wrong purge held fault", 0, 1, 0, 0, 1),
        ("matched cold purge consumed", 1, 2, 0, 0, 0),
        ("same-cycle stale DDR response", 0, 2, 0, 0, 0),
        ("held fault backpressure", 0, 2, 0, 0, 1),
        ("fault consumed", 1, 2, 0, 0, 0),
        ("same-cycle new client request", 0, 2, 0, 0, 0),
        ("descriptor and beat reserved", 0, 2, 1, 1, 0),
        ("registered backend offer held", 0, 2, 1, 1, 0),
        ("client return skid held", 0, 2, 1, 1, 0),
        ("beats empty descriptor open", 0, 2, 0, 1, 0),
        ("real CLOSE returned idle", 1, 2, 0, 0, 0),
        ("same-cycle new P FENCE", 0, 2, 0, 0, 0),
        ("P FENCE backend offer held", 0, 2, 0, 0, 0),
        ("P FENCE held client reply", 0, 3, 0, 0, 0),
        ("P FENCE client reply consumed", 1, 3, 0, 0, 0),
        ("same-cycle cancel offer", 0, 3, 0, 0, 0),
        ("held cancel acknowledgement", 0, 3, 0, 0, 0),
        ("cancel acknowledgement consumed", 1, 3, 0, 0, 0),
        ("same-cycle mode change offer", 0, 3, 0, 0, 0),
        ("mode change consumed", 1, 3, 0, 0, 0),
    )]


def compare(log_path):
    data = log_path.read_bytes()
    expected = reference()
    observed = []
    passed = False
    for line in data.decode("ascii").splitlines():
        if "%Error" in line or "%Fatal" in line or "Assertion failed" in line:
            raise ValueError("RTL reports failure: " + line)
        if line == PASS:
            if passed or len(observed) != len(expected):
                raise ValueError("duplicate or premature RTL PASS")
            passed = True
        elif "quiescent=" in line:
            match = CHECKPOINT.fullmatch(line)
            if passed or match is None:
                raise ValueError("malformed or out-of-order checkpoint: " + line)
            name, *values = match.groups()
            row = Checkpoint(name, *map(int, values))
            index = len(observed)
            if index >= len(expected) or row != expected[index]:
                target = expected[index]._asdict() if index < len(expected) else None
                raise ValueError("checkpoint {}: expected {!r}, observed {!r}".format(
                    index + 1, target, row._asdict()))
            observed.append(row)
    if not passed:
        raise ValueError("missing RTL PASS")
    return {"schema": "issue265-dma-quiescence-rtl/1", "source_commit": SOURCE_COMMIT,
            "scope": "typed DMA transport readiness against the directed testbench backend",
            "log_sha256": hashlib.sha256(data).hexdigest(), "matched_checkpoints": len(observed),
            "checkpoints": [row._asdict() for row in observed]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.log), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, "DMA quiescence comparison failed: {}\n".format(error))


if __name__ == "__main__":
    main()
