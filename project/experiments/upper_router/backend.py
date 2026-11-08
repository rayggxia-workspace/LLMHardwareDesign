"""Lossless, model-independent routing geometry handoff (DEF + identity map).

This emits an *upper interconnect view*, not an invented placed logic design.
Its boundary ports reference the real native terminal IDs through bindings.json.
The consumer must stitch it to the SHA-bound native databases and re-extract.
"""
import argparse
import json
import math
from pathlib import Path

from check import digest, verify
from geometry import need, segment_shape, via_shapes


def merged_segments(segments):
    groups = {}
    for s in segments:
        axis = 0 if s['layer'] == 'M11' else 1
        lo, hi = sorted([s['a'][axis], s['b'][axis]])
        groups.setdefault((s['layer'], s['a'][1-axis]), []).append((lo, hi))
    out = []
    for (layer, fixed), spans in sorted(groups.items()):
        merged = []
        for a, b in sorted(spans):
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(b, merged[-1][1])
            else:
                merged.append([a, b])
        for a, b in merged:
            out.append({'layer': layer, 'a': [a, fixed] if layer=='M11' else [fixed, a],
                        'b': [b, fixed] if layer=='M11' else [fixed, b]})
    return out


def emit(spec, result, output, dbu_per_micron, *, via_resistance_ohm):
    verify(spec, result)
    need(not result['failed'], 'partial routing cannot be exported as a completed handoff')
    need(type(dbu_per_micron) is int and dbu_per_micron > 0, 'explicit DBU scale required')
    need(spec.get('context',{}).get('dbu_per_micron',dbu_per_micron)==dbu_per_micron,
         'DBU scale differs from bound native context')
    need(isinstance(via_resistance_ohm,(int,float)) and math.isfinite(via_resistance_ohm)
         and via_resistance_ohm>0,'explicit positive via resistance required')
    t = spec['technology']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    pins, records, identities, expected = [], [], {}, {}
    used_pins = {p for n in spec['nets'] if n['sinks'] for p in [n['driver']]+n['sinks']}
    port_ids = {p: 'p%06d' % i for i,p in enumerate(sorted(used_pins))}
    for i, n in enumerate(spec['nets']):
        if not n['sinks']:
            continue
        net = 'n%06d' % i
        paths = []
        r = result['routes'][n['id']]
        shapes = []
        for s in merged_segments(r['segments']):
            paths.append('metal%s ( %d %d ) ( %d %d )' % (s['layer'][1:],*s['a'],*s['b']))
            shapes.append([*segment_shape(s['layer'], s['a'], s['b'], t)])
        for v in r['via10']:
            paths.append('metal10 ( %d %d ) UR_via10' % tuple(v['at']))
            shapes.extend([layer,list(rect)] for layer,rect in via_shapes('via10',v['at'],t))
        for v in r['via11']:
            paths.append('metal11 ( %d %d ) UR_via11' % tuple(v))
            shapes.extend([layer,list(rect)] for layer,rect in via_shapes('via11',v,t))
        members = [n['driver']]+n['sinks']
        for p in members:
            # INPUT/OUTPUT are with respect to this interconnect-only view.
            # The physical native direction remains in the identity map.
            direction = 'INPUT' if p == n['driver'] else 'OUTPUT'
            ports = ''.join(' + PORT + LAYER metal10 ( %d %d ) ( %d %d ) + FIXED ( 0 0 ) N' % tuple(box)
                            for box in spec['pins'][p])
            pins.append('- %s + NET %s + DIRECTION %s + USE SIGNAL%s ;' % (port_ids[p],net,direction,ports))
        records.append('- %s %s + USE SIGNAL\n + ROUTED %s ;' %
                       (net,' '.join('( PIN %s )' % port_ids[p] for p in members),'\n NEW '.join(paths)))
        identities[net] = {'logical_net': n['id'], 'driver': n['driver'], 'sinks': n['sinks'],
                           'ports': {port_ids[p]: p for p in members}}
        expected[net] = shapes
    header = ('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN upper_interconnect ;\n'
              'UNITS DISTANCE MICRONS %d ;\nDIEAREA ( %d %d ) ( %d %d ) ;\n'
              'COMPONENTS 0 ;\nEND COMPONENTS\n') % (dbu_per_micron,*t['bounds'])
    text = header + 'PINS %d ;\n' % len(pins) + '\n'.join(pins) + '\nEND PINS\n'
    text += 'NETS %d ;\n' % len(records) + '\n'.join(records) + '\nEND NETS\nEND DESIGN\n'
    (output/'upper.def').write_text(text)
    # LEF for via definitions; routing layers must be provided by the SHA-bound
    # technology, independently checked for width and spacing before ingestion.
    lines = ['VERSION 5.6 ;\n']
    for index, name in [(10,'via10'),(11,'via11')]:
        v=t[name]
        lines.append('VIA UR_via%d\n RESISTANCE %.12g ;\n' % (index,via_resistance_ohm))
        for layer,size in [('metal%d'%index,v['cut']+2*v['lower_enclosure']),
                           ('via%d'%index,v['cut']),('metal%d'%(index+1),v['cut']+2*v['upper_enclosure'])]:
            h=size/2/dbu_per_micron
            lines.append(' LAYER %s ; RECT %.12g %.12g %.12g %.12g ;\n' % (layer,-h,-h,h,h))
        lines.append('END UR_via%d\n' % index)
    lines.append('END LIBRARY\n')
    (output/'upper-vias.lef').write_text(''.join(lines))
    metadata={'schema_version':'upper-backend-handoff/1','dbu_per_micron':dbu_per_micron,
              'spec_sha256':digest(spec),'route_sha256':digest(result),'context':spec.get('context',{}),
              'nets':identities,'expected_shapes':expected,'technology':t,
              'via_resistance_ohm':via_resistance_ohm,
              'physical_qualified':False,'native_stitched':False,
              'scope':'interconnect-only DEF; no invented native components, RC or timing qualification'}
    (output/'bindings.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('spec',type=Path);p.add_argument('routes',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--dbu-per-micron',required=True,type=int)
    p.add_argument('--via-resistance-ohm',required=True,type=float)
    a=p.parse_args()
    emit(json.loads(a.spec.read_text()),json.loads(a.routes.read_text()),a.output,a.dbu_per_micron,
         via_resistance_ohm=a.via_resistance_ohm)
