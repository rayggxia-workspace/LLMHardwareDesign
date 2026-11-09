"""Source-derived timing, not an RTL simulator or a measured physical clock.

All edges refer to an idle, zero-backpressure, single serial P controller.
Leaf latency excludes the command acceptance edge and response consumption.
"""
def m_leaf_latency(tiles, awide, bwide, rows=1):
    assert 1 <= tiles <= 4 and 1 <= rows <= 8
    q = tiles * (3 if awide else 1) * (3 if bwide else 1)
    starts, fetches = [], []
    for row in range(rows):
        start = 1 if not row else starts[-1] + q + 1
        if row >= 2:
            start = max(start, fetches[row - 2] + 5)
        fetch = max(start + q + 2, fetches[-1] + 4 if row else 0)
        starts.append(start)
        fetches.append(fetch)
    return fetches[-1] + 8


def command_done_latency(leaf_latency, store=False):
    return leaf_latency + (7 if store else 2)


def command_accept_interval(leaf_latency, store=False):
    return command_done_latency(leaf_latency, store) + 2


def load_done_latency(tiles, rows, bwide=False, reuse_b=False):
    """Specialized derived LOAD formulas awaiting actual server calibration.

    P external LOAD accept -> first load_done value after an edge. Retiring
    done takes the next edge; another LOAD can be accepted one edge later.
    Includes the original one-credit A/B holds (II=2), real S response and
    B-before-A scheduling. Do not apply under memory/M contention or stalls.
    """
    assert 1 <= tiles <= 4 and rows in (0, 1, 3)
    assert not (rows == 0 and reuse_b)
    if reuse_b:
        return (2 if rows == 1 else 6) * tiles + 5
    if rows == 0:
        return (4 if bwide else 2) * tiles + 5
    if rows == 1:
        return (6 if bwide else 4) * tiles + 5
    return 6 * tiles + (9 if bwide else 7)


def prior_full_p(segments, contexts):
    """Exactly reproduces run11's bench, including its explicit LOAD hold."""
    full_to_mac, bonly_to_mac = 14, 12
    mac = command_accept_interval(m_leaf_latency(1, False, False))
    outputs = 16 * command_accept_interval(3, store=True)
    if contexts:
        return segments * (full_to_mac + mac) + 7 * segments * (bonly_to_mac + mac) + outputs + 8 * command_accept_interval(0)
    return 8 * segments * (full_to_mac + mac) + outputs


def verify_frozen_points():
    assert [m_leaf_latency(4, f & 1, f & 2, 8) for f in range(4)] == [53, 114, 114, 306]
    assert [prior_full_p(s, c) for s in (2, 8) for c in (False, True)] == [672, 676, 2112, 2032]
    return {"run10_leaf_rows8": [53, 114, 114, 306], "run11_complete_P": [672, 676, 2112, 2032]}


if __name__ == '__main__':
    import json
    print(json.dumps(verify_frozen_points()))
