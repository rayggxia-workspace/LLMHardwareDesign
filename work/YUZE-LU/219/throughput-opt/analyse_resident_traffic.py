"""Audit logical backing traffic after independent finite-S numeric replay.

This is an observation tool, not a relaxed allocator or a DRAM model. A copy
found elsewhere is only a reuse opportunity if a real legal path/layout exists.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from verify_resident_batch import replay


def audit(tile,program):
    actors=program['actors'];objects=tile['graph']['objects']
    tags={actor:{} for actor in actors};loads=Counter();stores=Counter();load_kinds=Counter()
    peak_tagged=Counter();peak_future_live=Counter();future=Counter()
    commits={(c['record'],c['external_address']) for c in tile['graph']['external_commits']}
    def uses(event):
        if event['op']=='ROW_M_TERM':return [*event['a_records'],event['b_record']]
        if event['op']=='E':return event['input_records']
        if event['op']=='STORE_COMMIT':return [event['record']]
        return []
    for event in program['events']:future.update(uses(event))
    backing=set();loaded=set();overwrites_live=0
    for e in program['events']:
        actor=e['actor'];op=e['op'];record=e.get('record');address=e.get('address')
        if op=='LOAD_ZERO':loads['guard_zero']+=1
        elif op=='LOAD':
            own=[at for at,value in tags[actor].items() if value==record]
            other=[(name,at) for name,row in tags.items() if name!=actor for at,value in row.items() if value==record]
            if address in own:category='already_at_destination'
            elif own:category='same_S_other_address'
            elif other:category='other_S_copy'
            elif (actor,record) in loaded:category='reloaded_without_S_copy'
            elif objects[record]['kind']=='produced':category='produced_without_S_copy'
            else:category='first_source_load'
            loads[category]+=1;loaded.add((actor,record))
            obj=objects[record]
            load_kinds['produced' if obj['kind']=='produced' else 'literal' if 'literal' in obj else 'external_input']+=1
            if obj['kind']=='produced' and record not in backing:raise ValueError('produced load has no observed backing write')
        elif op in ('STORE','STORE_COMMIT'):
            if tags[actor].get(address)!=record:raise ValueError('store/source tracking differs')
            stores['required_boundary' if (record,e['external_address']) in commits else 'scratch_backing']+=1
            backing.add(record)
        if op in ('LOAD','LOAD_ZERO','ROW_M_FINAL','E'):
            old=tags[actor].get(address)
            if old is not None and old!=record and future[old]>0:overwrites_live+=1
            if record is None:tags[actor].pop(address,None)
            else:tags[actor][address]=record
        for value in uses(e):
            future[value]-=1
            if future[value]<0:raise ValueError('future use accounting differs')
        for name,row in tags.items():
            peak_tagged[name]=max(peak_tagged[name],len(row))
            peak_future_live[name]=max(peak_future_live[name],sum(future[v]>0 for v in row.values()))
    if sum(loads.values())!=program['external_load_words'] or sum(stores.values())!=program['external_store_words']:
        raise ValueError('observed traffic does not match verified program')
    return {'load_words_by_copy_location':dict(loads),'load_words_by_kind':dict(load_kinds),
        'store_words_by_boundary':dict(stores),'capacity_words':{n:a['words'] for n,a in actors.items()},
        'peak_physically_tagged_words':dict(peak_tagged),'peak_conservative_future_live_words':dict(peak_future_live),
        'overwrites_of_future_live_copy':overwrites_live,'total_ticks':program['total_ticks'],
        'copy_ticks':program['copy_ticks'],'external_words':program['external_words']}


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    data=json.loads(a.source.read_text(encoding='utf-8'));tile=data['tile'];result={}
    for name,program in data['programs'].items():
        for fixture in data['fixtures']:
            replay(tile,program,{(t,i):v for t,i,v in fixture['inputs']})
        result[name]=audit(tile,program)
    out={'passed':True,'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),
        'numeric_cases_per_program':len(data['fixtures']),'plans':result,
        'scope':'logical 128-bit records, serial services, cold finite-S tile; copy locations are observations, not proof of legal free movement or DRAM traffic; future-live includes bank-retained B and boundary outputs'}
    a.output.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))


if __name__=='__main__':main()
