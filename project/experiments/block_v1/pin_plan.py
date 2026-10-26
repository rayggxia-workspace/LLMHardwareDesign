"""Finite A/C* candidates from the exact current leaf port inventory.

This creates planned M10 windows, not a routed/pin-access qualification.
All observation ports have the same treatment as ordinary data ports.
"""
from collections import defaultdict
import math


def generate(bits, leaf, policy):
    assert policy in ('A', 'C')
    width, height = leaf['die_um']
    assert width == height
    # Native M10: width .8, pitch 1.6, half-pitch offset .8 um.
    # Every final candidate must independently verify these against its ODB.
    pitch, offset, size = 1.6, .8, .8
    groups = defaultdict(list)
    for bit in bits:
        groups[bit['port']].append(bit)
    assert 'clk' in groups and len(groups['clk']) == 1
    groups = {name: sorted(values, key=lambda b:b['index']) for name, values in sorted(groups.items())}
    slots = [offset+pitch*i for i in range(math.floor((width-2*offset)/pitch)+1)
             if 20 <= offset+pitch*i <= width-20]
    assert slots
    low, high = offset, offset+pitch*math.floor((width-2*offset)/pitch)
    perimeter = ([(low, y, 'left') for y in slots]
                 + [(x, high, 'top') for x in slots]
                 + [(high, y, 'right') for y in reversed(slots)]
                 + [(x, low, 'bottom') for x in reversed(slots)])
    wide = [name for name in groups if policy == 'C' and len(groups[name]) > 32]
    columns = math.ceil(math.sqrt(max(1, len(wide))))
    rows = math.ceil(max(1, len(wide))/columns)
    result = []
    edge_cursor = 0
    for name, entries in groups.items():
        count = len(entries)
        if name in wide:
            group_index = wide.index(name)
            cx = width*(group_index % columns+1)/(columns+1)
            cy = height*(group_index//columns+1)/(rows+1)
            nx = math.ceil(math.sqrt(count)); ny = math.ceil(count/nx)
            # Two native tracks between adjacent access windows. Round the
            # group origin once, retaining exact regular spacing afterwards.
            x0 = offset+pitch*round((cx-pitch*(nx-1)-offset)/pitch)
            y0 = offset+pitch*round((cy-pitch*(ny-1)-offset)/pitch)
            positions = [(x0+2*pitch*(i % nx), y0+2*pitch*(i//nx), 'internal') for i in range(count)]
        else:
            assert edge_cursor+count <= len(perimeter), 'Insufficient single-row edge capacity'
            positions = perimeter[edge_cursor:edge_cursor+count]
            edge_cursor += count
        for entry, (x, y, region) in zip(entries, positions):
            pin = name if count == 1 else '%s[%d]' % (name, entry['index'])
            assert size/2 <= x <= width-size/2 and size/2 <= y <= height-size/2
            result.append(dict(pin=pin, port=name, index=entry['index'], direction=entry['direction'],
                               role=entry['role'], layer='metal10', xy_um=[round(x, 6), round(y, 6)],
                               size_um=[size, size], region=region))
    assert len(result) == len(bits) and len({p['pin'] for p in result}) == len(bits)
    # Uniform boxes: a neighboring-cell search independently rejects overlaps
    # and insufficient edge-to-edge spacing, including across group borders.
    occupied = defaultdict(list)
    for pin in result:
        x, y = pin['xy_um']; key = (math.floor(x/pitch), math.floor(y/pitch))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in occupied[key[0]+dx, key[1]+dy]:
                    ox, oy = other['xy_um']
                    assert max(abs(x-ox), abs(y-oy)) >= pitch-1e-7, (pin, other)
        occupied[key].append(pin)
    return dict(schema='block-v1-pin-plan/1', policy=policy, pins=result,
                native_m10_assumptions=dict(width_um=size, pitch_um=pitch, offset_um=offset),
                ports=len(bits), internal_ports=sum(p['region']=='internal' for p in result),
                qualified_access=False,
                scope='Derived current-source candidate XY only; actual geometry, access, route and RC acceptance pending')
