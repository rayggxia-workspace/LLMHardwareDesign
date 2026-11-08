"""Independently audit identity, destination commit and source release."""


def check(log):
    current = None
    receipts, drops, accepted, holds, abandoned = [], [], [], [], []
    expected_drops = []
    tx_cycles, commit_cycles, release_cycles = [], [], []
    actual_tx, actual_commit, actual_release = [], [], []
    for line in log.splitlines():
        if line.startswith("N "):
            _, cycle, kind, block, *_ = line.split()
            if kind == "TX":
                actual_tx.append(int(cycle))
            elif kind == "STORE" and block == "1":
                actual_commit.append(int(cycle))
            elif kind == "ACK_RECV":
                actual_release.append(int(cycle))
        if not line.startswith("ACKG "):
            continue
        _, raw_cycle, kind, *fields = line.split()
        cycle = int(raw_cycle)
        identity = int(fields[0], 16) if fields else None
        if kind == "RESET":
            if current is not None:
                abandoned.append(current)
            current = None
        elif kind == "ARM":
            assert current is None, "source reused occupied slot"
            current = dict(identity=identity, arm=cycle, commit=None, accepted=None)
            tx_cycles.append(cycle)
        elif kind == "COMMIT":
            assert current is not None and identity == current["identity"]
            assert current["arm"] < cycle and current["commit"] is None
            current["commit"] = cycle
            commit_cycles.append(cycle)
        elif kind == "WIRE":
            if (current is not None and identity == current["identity"] and
                    current["commit"] is not None and current["commit"] < cycle and current["accepted"] is None):
                current["accepted"] = cycle
                accepted.append(identity)
            else:
                expected_drops.append(cycle + 1)
        elif kind == "DROP":
            drops.append(cycle)
        elif kind == "HOLD":
            assert current is not None and identity == current["identity"] and current["accepted"] is not None
            holds.append(cycle)
        elif kind == "DONE":
            assert current is not None and identity == current["identity"] and current["accepted"] < cycle
            receipts.append(dict(**current, released=cycle))
            release_cycles.append(cycle)
            current = None
        else:
            raise ValueError(f"unknown ACK event {kind}")
    assert tx_cycles == actual_tx, "guard arm does not match actual TX"
    assert commit_cycles == actual_commit, "commit does not match actual destination S response"
    assert release_cycles == actual_release, "source release without guard completion"
    assert drops == expected_drops, "bad acknowledgement accepted or rejected at the wrong edge"
    assert len(accepted) == len(receipts), "accepted acknowledgement lost before release"
    return dict(receipts=receipts, rejected=len(drops), held_cycles=len(holds), abandoned=abandoned, pending=current)
