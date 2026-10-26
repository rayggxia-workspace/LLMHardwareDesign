"""Generate an internal fixed M10 landing access probe; no active circuitry.

The probe tests router capabilities only. It cannot qualify full block timing,
PG, extracted RC or physical views. Nothing permits editing the fixed M10 pin.
"""
import argparse
import json
from pathlib import Path
import re


def generate(out,cpus):
    out.mkdir(exist_ok=False)
    lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;']
    for direction in ['INPUT','OUTPUT']:
        name='LAND_'+direction
        lef += [f'MACRO {name}','  CLASS BLOCK ;','  ORIGIN 0 0 ;','  FOREIGN '+name+' 0 0 ;',
                '  SIZE 20 BY 20 ;','  SYMMETRY X Y ;','  PIN p','    DIRECTION '+direction+' ;',
                '    USE SIGNAL ;','    PORT','      LAYER metal10 ;','      RECT 8.4 8.4 9.2 9.2 ;',
                '    END','  END p','  OBS']
        for layer in range(1,11):
            lef += ['    LAYER metal%d ;'%layer]
            # Exact legal M10 window, rather than opening the whole native top.
            boxes=[(0,0,20,8.4),(0,9.2,20,20),(0,8.4,8.4,9.2),(9.2,8.4,20,9.2)]if layer==10 else[(0,0,20,20)]
            lef += ['    RECT %g %g %g %g ;'%box for box in boxes]
        lef+=['  END','END '+name]
    lef+=['END LIBRARY']
    (out/'landing.lef').write_text('\n'.join(lef)+'\n')
    (out/'probe.def').write_text('''VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN landing_probe ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA ( 0 0 ) ( 384000 384000 ) ;
COMPONENTS 2 ;
- U0 LAND_OUTPUT + FIXED ( 51200 51200 ) N ;
- U1 LAND_INPUT + FIXED ( 256000 256000 ) N ;
END COMPONENTS
NETS 1 ;
- link ( U0 p ) ( U1 p ) + USE SIGNAL ;
END NETS
END DESIGN
''')
    (out/'route.tcl').write_text('''read_lef overlay/research12.tech.lef
read_lef probe/landing.lef
read_def probe/probe.def
source /OpenROAD-flow-scripts/flow/platforms/nangate45/make_tracks.tcl
source overlay/new_tracks.tcl
set_thread_count %d
set_routing_layers -signal metal11-metal12
set_macro_extension 0
write_db probe/unrouted.odb
write_def probe/unrouted.def
global_route -guide_file probe/route.guide
detailed_route -output_drc probe/drc.rpt -output_guide_coverage probe/coverage.csv -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10
write_db probe/routed.odb
write_def probe/routed.def
'''%cpus)


def audit(out):
    text=(out/'routed.def').read_text()
    # Fail closed if the router creates any native-layer routed path. Via
    # enclosures must subsequently be checked against the existing landing.
    layers=re.findall(r'(?:ROUTED|NEW)\s+(metal\d+)\b',text)
    assert layers and set(layers)=={'metal11','metal12'},'native-layer route or missing new-layer coverage: '+repr(layers)
    sections=[]
    for name in ['COMPONENTS','PINS']:
        def section(path):
            source=path.read_text();match=re.search(r'(?m)^'+name+r'\s+\d+\s*;.*?^END '+name+r'\s*$',source,re.S|re.M)
            return match.group(0)if match else ''
        before=section(out/'unrouted.def');after=section(out/'routed.def')
        assert before==after,'fixed instance/pin changed: '+name
        sections.append(name)
    # drt uses an empty report when there are no violations.
    drc=(out/'drc.rpt').read_text()if(out/'drc.rpt').exists()else None
    assert drc is not None and not drc.strip(),'router DRC violations or no report'
    (out/'route-check.json').write_text(json.dumps(dict(schema='block-v1-route-probe/1',
        router_native_path_count=0,routed_path_layers=layers,fixed_sections_compared=sections,
        router_drc_empty=True,independent_geometry_qualification=False,rc_extraction_qualified=False),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('action',choices=['generate','audit']);p.add_argument('out',type=Path);p.add_argument('--cpus',type=int,default=1)
    a=p.parse_args();generate(a.out,a.cpus) if a.action=='generate' else audit(a.out)
