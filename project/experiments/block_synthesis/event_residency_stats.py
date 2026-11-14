"""Summarize measured reservations and actual DDR handoff commands."""
from collections import Counter, defaultdict


def handoff_stats(plan, spec):
    windows, sizes = spec['windows'], spec['value_bytes']
    accesses = defaultdict(list)
    transfer_bytes = Counter()
    transfers = Counter()
    operand_bytes = 0
    used = defaultdict(set)

    def use(window, value, start, end, write):
        used[windows[window]['site']].add(window)
        accesses[window].append((start, end, value, write))

    for row in plan['tasks']:
        for event in row['evaluation']['events']:
            start, end = event['start'], event['end']
            if event['kind'] == 'move':
                src, dst, value = (event[key] for key in ('src', 'dst', 'value'))
                direction = 'ddr_read' if src == 'DDR' else 'ddr_write' if dst == 'DDR' else 'on_chip'
                transfer_bytes[direction] += sizes[value]
                transfers[direction] += 1
                if src != 'DDR':
                    use(src, value, start, end, False)
                if dst != 'DDR':
                    use(dst, value, start, end, True)
            else:
                for window, value in event['inputs'].items():
                    operand_bytes += sizes[value]
                    use(window, value, start, end, False)
                for window, value in event['outputs'].items():
                    use(window, value, start, end, True)

    timeline = defaultdict(list)
    for window, events in accesses.items():
        current, lo, hi = None, 0, 0
        site = windows[window]['site']
        for start, end, value, write in sorted(events):
            if write:
                if current is not None:
                    timeline[site].extend(((lo, sizes[current]), (hi, -sizes[current])))
                current, lo = value, start
            hi = max(hi, end)
        if current is not None:
            timeline[site].extend(((lo, sizes[current]), (hi, -sizes[current])))

    peaks = {}
    for site, events in timeline.items():
        current = peak = 0
        for _, change in sorted(events):
            current += change
            peak = max(peak, current)
        peaks[site] = peak
    return {
        'handoff_ddr_read_bytes': transfer_bytes['ddr_read'],
        'handoff_ddr_write_bytes': transfer_bytes['ddr_write'],
        'handoff_on_chip_copy_bytes': transfer_bytes['on_chip'],
        'handoff_copies': dict(transfers),
        'handoff_sram_operand_bytes': operand_bytes,
        'peak_live_handoff_sram_bytes': peaks,
        'used_handoff_window_bytes': {site: sum(windows[window]['bytes'] for window in names)
                                      for site, names in used.items()},
    }
