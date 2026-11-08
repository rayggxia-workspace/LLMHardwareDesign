"""Create minimal, SHA-bound physical probes for a composed native GDS."""
import argparse
import json
from pathlib import Path
from resource_base import load_library
from native_inventory import sha


def build(base,library,native):
    terms={}
    for name,p in base['endpoints'].items():
        terms[name]={'direction':'OUTPUT' if p['role']=='driver' else 'INPUT',
                     'native_net':p['native_net'],'signal_type':'SIGNAL',
                     'shapes':[{'layer':'metal10','rect':s['rect_dbu']} for s in p['m10_shapes']]}
    for a in base['assemblies']:
        dx,dy=a['translation_dbu']
        for name,p in library[a['template']]['inventory']['terms'].items():
            if p['signal_type'] not in ('POWER','GROUND'):continue
            terms[a['id']+'/'+name]={**{k:p[k] for k in ('direction','signal_type')},
                 'native_net':a['id']+'/'+p['native_net'],
                 'shapes':[{'layer':s['layer'],'rect':[s['rect'][0]+dx,s['rect'][1]+dy,s['rect'][2]+dx,s['rect'][3]+dy]} for s in p['shapes']]}
    return {'top':'NATIVE_RESOURCE_ASSEMBLY','dbu_per_micron':base['dbu_per_micron'],
            'terms':terms,'files':{'native/6_final.gds':{'sha256':sha(native)}}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','library','native_gds','output'):p.add_argument(n,type=Path)
    a=p.parse_args();result=build(json.loads(a.base.read_text()),load_library(a.library),a.native_gds)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
