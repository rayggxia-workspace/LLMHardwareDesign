"""Plan candidate Gather landings on the U39 outline and preserve existing pads."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from resident_gather_contract import DMA

DIE = (2432000, 1968000)
PITCH = 3200
PAD = 4000
CLEARANCE = 4000

def overlaps(a, b):
    return a[0]<b[2]+CLEARANCE and b[0]<a[2]+CLEARANCE and a[1]<b[3]+CLEARANCE and b[1]<a[3]+CLEARANCE

def native_shapes(path):
    data = path.read_bytes()
    text = data.decode()
    if 'DIEAREA ( 0 0 ) ( 2432000 1968000 ) ;' not in text:
        raise ValueError('U outline changed')
    pins = text.split('\nPINS ', 1)[1].split('\nEND PINS', 1)[0]
    for record in re.split(r'\n\s+- ', pins)[1:]:
        name = record.split()[0]
        placements = re.findall(r'\+ (?:FIXED|PLACED) \( (\d+) (\d+) \) N', record)
        rects = [tuple(map(int, r)) for r in re.findall(
            r'\+ LAYER metal10 \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', record)]
        if rects:
            if len(placements) != 1:
                raise ValueError(f'{name}: unexpected placement')
            xy = list(map(int, placements[0])) * 2
            yield name, [tuple(a+b for a,b in zip(xy, r)) for r in rects], '+ USE SIGNAL' in record

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('mapped', 'original', 'out'):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    original = [(name, shapes, signal) for name, shapes, signal in native_shapes(args.original)]
    blocked = [rect for _, shapes, _ in original for rect in shapes]
    mapped = json.loads(args.mapped.read_bytes())
    module = mapped['modules']['u_n32_native_frame_64']
    ports = module['ports']
    netnames, cells = module['netnames'], module['cells']
    next_bit = 1 + max(bit for port in netnames.values() for bit in port['bits'] if isinstance(bit, int))
    ties = 0
    for name, width, output in DMA:
        port = ports['dma_'+name]
        assert len(port['bits'])==width and port['direction']==('output' if output else 'input')
        for i, bit in enumerate(port['bits']):
            if isinstance(bit, str):
                assert output and bit in ('0','1')
                tag = f'gather_tie_{name}_{i}'
                cells[tag] = {'hide_name': 0, 'type': f'LOGIC{bit}_X1', 'parameters': {},
                              'attributes': {}, 'port_directions': {'Z': 'output'}, 'connections': {'Z': [next_bit]}}
                port['bits'][i] = next_bit
                netnames['dma_'+name]['bits'][i] = next_bit
                ties += 1
                next_bit += 1

    locations = []
    # The incoming and outgoing control landings remain at their original sites.
    for name, shapes, signal in original:
        if not signal or len(shapes)!=1 or name.startswith('late_leaf_adapter_'):
            continue
        assert name.split('[')[0] in ports
        locations.append((name, *shapes[0]))
    n_original = len(locations)
    assert n_original > 270
    # Candidate box grid on actual M10 tracks between the fixed M10 power rails.
    available = []
    for y in range(3340+5*PITCH, 300000, 3*PITCH):
        for x in range(3390+25*PITCH, DIE[0]-34000, 3*PITCH):
            rect = (x-PAD//2,y-PAD//2,x+PAD//2,y+PAD//2)
            if all(not overlaps(rect, b) for b in blocked):
                available.append(rect)
    i = 0
    for name, width, output in DMA:
        for bit in range(width):
            port = f'dma_{name}'+(f'[{bit}]' if width>1 else '')
            locations.append((port, *available[i]))
            i += 1
    assert i==650 and len({r[0] for r in locations})==len(locations)
    (args.out/'landings.tsv').write_text(''.join('\t'.join(map(str, r))+'\n' for r in locations))
    (args.out/'with-output-ties.json').write_text(json.dumps(mapped))
    (args.out/'pins.json').write_text(json.dumps({
        'source_def_sha256': hashlib.sha256(args.original.read_bytes()).hexdigest(),
        'preserved_landings': n_original, 'gather_landings': i, 'independent_output_ties': ties,
        'scope': 'candidate pin sites before placement and lower routing'
    }, indent=2)+'\n')

if __name__ == '__main__':
    main()

