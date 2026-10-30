"""Finite A/C* candidates from the exact current leaf port inventory.

This creates planned M10 windows, not a routed/pin-access qualification.
All observation ports have the same treatment as ordinary data ports.
"""
from collections import defaultdict
import math


def generate(bits, leaf, policy, grid):
    assert policy in ('A', 'C')
    width, height = leaf['die_um']
    assert width == height
    px,py=grid['pitch_x'],grid['pitch_y'];ox,oy=grid['offset_x'],grid['offset_y']
    size=grid['width'];required=grid['cut_width']+grid['cut_spacing']
    sx=math.ceil((required-1e-10)/px);sy=math.ceil((required-1e-10)/py)
    assert sx>=1 and sy>=1
    groups = defaultdict(list)
    for bit in bits:
        groups[bit['port']].append(bit)
    assert 'clk' in groups and len(groups['clk']) == 1
    groups = {name: sorted(values, key=lambda b:b['index']) for name, values in sorted(groups.items())}
    def slots(offset,pitch,stride,lo,hi):
        start=math.ceil((lo-offset)/pitch);end=math.floor((hi-offset)/pitch)
        return [offset+pitch*i for i in range(start,end+1,stride)]
    xs=slots(ox,px,sx,20,width-20);ys=slots(oy,py,sy,20,height-20)
    assert xs and ys
    lowx=ox+px*math.ceil((size/2-ox)/px)
    lowy=oy+py*math.ceil((size/2-oy)/py)
    highx=ox+px*math.floor((width-size/2-ox)/px)
    highy=oy+py*math.floor((height-size/2-oy)/py)
    perimeter=[]
    # Enough legal edge rows for C8's complete observation/data inventory,
    # inside the same fixed 20um margin. Native via9 requires 1.68um center
    # separation, so every other 1.6um track is used in both dimensions.
    for row in range(math.floor((20-size/2)/max(sx*px,sy*py))):
        lx,hx=lowx+row*sx*px,highx-row*sx*px
        ly,hy=lowy+row*sy*py,highy-row*sy*py
        perimeter += ([(lx,y,'left-row%d'%row)for y in ys]
            +[(x,hy,'top-row%d'%row)for x in xs]
            +[(hx,y,'right-row%d'%row)for y in reversed(ys)]
            +[(x,ly,'bottom-row%d'%row)for x in reversed(xs)])
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
            x0=ox+px*round((cx-sx*px*(nx-1)/2-ox)/px)
            y0=oy+py*round((cy-sy*py*(ny-1)/2-oy)/py)
            positions=[(x0+sx*px*(i%nx),y0+sy*py*(i//nx),'internal')for i in range(count)]
        else:
            assert edge_cursor+count <= len(perimeter), 'Insufficient legal edge-row capacity'
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
        x,y=pin['xy_um'];key=(math.floor(x/required),math.floor(y/required))
        assert abs((x-ox)/px-round((x-ox)/px))<1e-7
        assert abs((y-oy)/py-round((y-oy)/py))<1e-7
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in occupied[key[0]+dx, key[1]+dy]:
                    other_x,other_y=other['xy_um']
                    assert max(abs(x-other_x),abs(y-other_y))>=required-1e-7,(pin,other)
        occupied[key].append(pin)
    return dict(schema='block-v1-pin-plan/1', policy=policy, pins=result,
                native_m10_grid=grid,track_stride=[sx,sy],
                ports=len(bits), internal_ports=sum(p['region']=='internal' for p in result),
                qualified_access=False,
                scope='Derived current-source candidate XY only; actual geometry, access, route and RC acceptance pending')
