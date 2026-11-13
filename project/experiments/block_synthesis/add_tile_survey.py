"""Cost-only Add aggregation opportunity on an independently checked plan.

Includes every original split32 command and copy. Does not generate a new
schedule or assert system/makespan savings. Integration must still provide
independent candidate checks, S invalidation and full numerical replay.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from add_tile_recipe import read_qualification,aggregate_cost
from streaming_ir import counts,enumerate_bindings,repeat,call
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def survey(ir,plan,qualification,origin_manifest):
    verify_cost(ir);verify(ir['tasks'],ir['hardware'],plan)
    h=ir['hardware'];proved=h.get('tile_service_profiles',{}).get('provenance',[])
    if origin_manifest not in {p['manifest_sha256'] for p in proved}:
        raise ValueError('Add probe does not use the selected inventory P proof')
    tasks={t['id']:t for t in ir['tasks']};nodes={n['id']:n for n in ir['primitive_program']['instructions']}
    program={p['id']:p for p in ir['program']};rows=[];excluded={}
    allowed=h['tile_service_bindings']['P']
    for row in plan['tasks']:
        node=nodes.get(row['id'])
        if not node or node['op']!='Add':continue
        task=tasks[row['id']];old=next(b for b in task['bindings'] if b['id']==row['binding'])
        if (node['bits']!=32 or set(old.get('macro_binding',{}))!={'M','E'} or
                old['macro_binding']['M'] not in allowed):
            excluded[node['id']]='unqualified selected Add binding';continue
        n=len(node['inputs']);size=math.prod(node['shape'])
        stats=counts(repeat(size*n,call('split32')),ir['native_templates'])
        prep=next(b for b in enumerate_bindings(stats,h) if b['macro_binding']==old['macro_binding'])
        pm=h['leaf_inventory'][old['macro_binding']['M']]
        temporary=program[node['id']]['temporary_external_region']['words'];choices=[]
        for tile in range(1,9):
            ag=aggregate_cost(size,n,tile,qualification,h['virtual_memory'],pm,signs=node['attributes']['signs'])
            if ag['prepared_tile_words']>temporary or ag['P_words']>h['sites'][pm['site']]['words']:continue
            choices.append((prep['ticks']+ag['ticks'],tile,ag))
        if not choices:excluded[node['id']]='finite preparation scratch/tail';continue
        cost,tile,ag=min(choices,key=lambda x:x[:2])
        rows.append({'id':node['id'],'elements':size,'inputs':n,'signs':node['attributes']['signs'],
            'old_ticks':old['ticks'],'old_words':old['external_read_words']+old['external_write_words'],
            'proposal_ticks':cost,'proposal_words':prep['external_read_words']+prep['external_write_words']+ag['external_words'],
            'prep_ticks':prep['ticks'],'tile':tile,'P_words':ag['P_words'],
            'temporary_words':temporary,'prepared_tile_words':ag['prepared_tile_words']})
    return {'scope':'cost-only opportunity with unchanged split preparation explicitly charged; not a new executable plan or makespan speedup',
        'cases':rows,'excluded':excluded,'old_serial_ticks':sum(x['old_ticks'] for x in rows),
        'proposal_serial_ticks':sum(x['proposal_ticks'] for x in rows),
        'old_words':sum(x['old_words'] for x in rows),'proposal_words':sum(x['proposal_words'] for x in rows),
        'unchanged':'same selected M/E instances, numeric format and finite external scratch; proposed aggregate footprint must still invalidate incompatible readonly cache'}


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('plan',type=Path)
    p.add_argument('proof',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    q=read_qualification(a.proof);manifest=json.loads((a.proof/'manifest.json').read_text())
    result=survey(json.loads(a.ir.read_text()),json.loads(a.plan.read_text()),q,manifest['origin_manifest_sha256'])
    result['input_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.ir,a.plan,a.proof/'manifest.json')}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','input_sha256')}))


if __name__=='__main__':main()
