"""Keep the existing Link8 inventory while grouping actual native neighbours.

This only chooses passive connections between already qualified fixed cells.
It never changes a native pin, payload latency, reset state or acceptance gate.
"""
import collections


def balance(source, chunks, reference_counts):
    destinations = sorted({destination for _, destination, _ in chunks})
    assert {destination for owner, destination in reference_counts if owner == source} == set(destinations)
    result = []
    for destination in destinations:
        selected = [(side, list(chunk)) for side, target, chunk in chunks if target == destination]
        expected = reference_counts[(source, destination)]
        assert len(selected) <= expected <= sum(len(chunk) for _, chunk in selected)
        # Split a spatially contiguous group; never merge across native sides.
        while len(selected) < expected:
            choices = [(len(chunk), chunk[-1][0]-chunk[0][0], -index, index)
                       for index, (_, chunk) in enumerate(selected) if len(chunk) >= 2]
            assert choices
            index = max(choices)[-1]
            side, chunk = selected[index]
            middle = len(chunk)//2
            selected[index:index+1] = [(side, chunk[:middle]), (side, chunk[middle:])]
        assert len(selected) == expected
        result.extend((side, destination, chunk) for side, chunk in selected)
    # Match the original side/destination traversal, including split adjacency.
    return sorted(result, key=lambda row: (row[0], row[1], row[2][0][0], row[2][0][1]))


def reference_counts(links):
    assert len(links) == 316
    counts = collections.Counter((row['source_instance'], row['fanout_branch']) for row in links)
    assert sum(counts.values()) == 316
    assert {count for (source, _), count in counts.items() if source == 's_port'} == {17}
    assert sum(count for (source, _), count in counts.items() if source == 's_port') == 102
    return counts


def spatial_reset_order(rows):
    """Order equivalent reset loads around their actual source perimeter."""
    assert rows and all(row['source_instance'] == 's_port' for row in rows)
    assert len(rows) == 102
    def perimeter(row):
        x, y = row['source_pin_anchor_um']
        width, height = row['source_pin_die_um']
        assert width == height == 3200
        side = row['side']
        return {2: x, 1: width+y, 3: 2*width+height-x,
                0: 2*(width+height)-y}[side]
    sequence = sorted(rows, key=lambda row: (perimeter(row), row['instance']))
    candidates = []
    for offset in range(len(sequence)):
        rotated = sequence[offset:]+sequence[:offset]
        spans = []
        for start in range(0, len(rotated), 16):
            points = [row['source_pin_anchor_um'] for row in rotated[start:start+16]]
            spans.append(sum(max(p[axis] for p in points)-min(p[axis] for p in points) for axis in (0, 1)))
        candidates.append(((max(spans), sum(spans), offset), rotated))
    return min(candidates, key=lambda row: row[0])[1]
