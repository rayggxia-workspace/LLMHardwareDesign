"""Strict native DEF routed-path partition for a target-conditioned H2 pilot.

No coordinate rewriting: each native NEW path must contain one layer, explicit
first point and at most one via. Unknown syntax fails before creating output.
"""
import collections
import hashlib
import json
from pathlib import Path
import re

def partition(source, output, bottom=8):
    text = Path(source).read_text()
    match = re.search(r'^NETS (\d+) ;\n(.*?)^END NETS',text,re.M|re.S)
    assert match
    nets = re.findall(r'^\s*- (.*?);',match[2],re.M|re.S)
    assert len(nets) == int(match[1])
    rows = []
    changed = []
    fixed_paths = custom_paths = 0
    layers = collections.Counter()
    via_counts = collections.Counter()
    lengths = collections.Counter()
    fixed_lengths = collections.Counter()
    guides = {}
    landings = []
    for record in nets:
        split = re.split(r'\+ ROUTED |\n\s*NEW ',record)
        header = split[0].strip()
        assert len(split)>1 and re.search(r'\+ USE (?:SIGNAL|CLOCK)',header)
        name = header.split()[0]
        clock = '+ USE CLOCK' in header
        kept = []
        removed = []
        boxes = []
        for path in split[1:]:
            tokens = path.strip().split()
            assert re.fullmatch(r'metal\d+',tokens[0]), tokens[:6]
            layer = int(tokens[0][5:])
            points = re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+(-?\d+))?\s*\)',path)
            assert points and '*' not in points[0][:2]
            stripped = re.sub(r'\([^)]*\)','',path).split()
            assert len(stripped) in (1,2), stripped
            via = stripped[1] if len(stripped)==2 else None
            if via:
                # Native detailed-route vias in this technology, not PG arrays.
                v = re.fullmatch(r'via(\d+)(?:_\d+)?',via)
                assert v, via
                upper = int(v[1])+1
                assert layer in (upper-1,upper)
                assert len(points)==1, 'Via path must be separate from wire segments'
                via_counts[via]+=1
            else:
                upper = layer
            x,y = map(int,points[0][:2])
            xs,ys=[x],[y]
            length = 0
            for px,py,extension in points[1:]:
                nx = x if px=='*' else int(px)
                ny = y if py=='*' else int(py)
                assert x==nx or y==ny
                length += abs(nx-x)+abs(ny-y)
                x,y = nx,ny
                xs.append(x);ys.append(y)
            layers[layer] += 1
            lengths[layer] += length
            # Fixed boundary via and its upper landing are prepaid access.
            # Custom routing starts at that landing; it cannot invent V7.
            frozen = clock or (via and upper<=bottom) or (not via and layer<bottom)
            if via and upper==bottom and not clock:
                landings.append(dict(net=name,via=via,x=x,y=y))
            if frozen:
                kept.append(path.strip())
                fixed_paths += 1
                fixed_lengths[layer] += length
            else:
                removed.append(path.strip())
                custom_paths += 1
                for guide_layer in sorted({layer,upper}):
                    if guide_layer>=bottom:
                        boxes.append([max(0,min(xs)-13440),max(0,min(ys)-13440),
                            min(3340000,max(xs)+13440),min(3340000,max(ys)+13440),guide_layer])
        if removed:
            changed.append(dict(net=name,removed_paths=len(removed),fixed_paths=len(kept)))
            guides[name]=boxes
        rows.append('    - '+header+'\n'+''.join('      + FIXED '+p+'\n' for p in kept)+'    ;\n')
    # Full DEF import is required. Native -incremental accepts the file but
    # does not import the ordinary routing in this binary; geometry audit
    # exposed that loss. Preserve every other native DEF section verbatim.
    deftext=text[:match.start()]+'NETS '+str(len(rows))+' ;\n'+''.join(rows)+text[match.end()-len('END NETS'):]
    Path(output).write_text(deftext)
    return dict(source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        bottom_custom_metal=bottom,nets=len(rows),affected_nets=changed,fixed_paths=fixed_paths,
        removed_custom_paths=custom_paths,paths_per_layer=layers,
        custom_guides=guides,
        access_landings=landings,
        source_wire_um={k:v/2000 for k,v in lengths.items()},
        frozen_wire_um={k:v/2000 for k,v in fixed_lengths.items()},vias=via_counts,
        scope='H1 target-conditioned lower prefabricated wires, all clock wires fixed; upper data paths deleted for real reroute. Not an independent multi-target base.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('source',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--bottom',type=int,default=8)
    a=p.parse_args()
    result=partition(a.source,a.output,a.bottom)
    a.output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='affected_nets'},indent=2))
    print('Affected nets:',len(result['affected_nets']))
