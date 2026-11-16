"""Relocate unchanged local plans to source-checked real-model sample indices.

Only explicit external addresses change; every native/local address event is
preserved and independently replayed. This is not a new full-model execution.
"""
import argparse
from copy import deepcopy
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import lower,bind_external
from resident_batch_graph import build,digest
from native_lane_cover import cover
from resident_survey import reference
from verify_resident_batch import replay


def main():
    p=argparse.ArgumentParser()
    for n in ('programs','ir','boundary_directory','output'):p.add_argument(n,type=Path)
    a=p.parse_args();data=json.loads(a.programs.read_text());old=data['tile'];ir=json.loads(a.ir.read_text())
    file=a.boundary_directory/'generated/actual-boundary-fixtures.json';receipt=json.loads((a.boundary_directory/'receipt.json').read_text())
    sha=hashlib.sha256(file.read_bytes()).hexdigest()
    if receipt['recovered']['generated/actual-boundary-fixtures.json']['sha256']!=sha:raise ValueError('saved actual model fixture SHA differs')
    raw=json.loads(file.read_text());names={o['tensor'] for o in old['graph']['objects'].values() if o['kind']=='external' and 'literal' not in o}
    by_sample={}
    for f in raw:
        if {t for t,i,v in f['inputs']}==names:by_sample.setdefault(f['sample'],[]).append(f)
    chosen={sample:sorted(rows,key=lambda f:f['element'])[:old['rows']] for sample,rows in by_sample.items()}
    if len(chosen)!=3 or any(len(fs)!=old['rows'] for fs in chosen.values()):raise ValueError('not enough actual boundary samples')
    indices=[f['element'] for f in chosen[0]]
    if any([f['element'] for f in rows]!=indices for rows in chosen.values()):raise ValueError('actual sample indices differ')
    graphs=[bind_external(lower(ir['primitive_program'],old['graphs'][0]['primitives'],index),ir) for index in indices]
    scratch=max(old['scratch_start'],1+max(o['external_address'] for g in graphs for o in g['objects'].values()))
    original=build(graphs,scratch_start=scratch,external_capacity_words=old['external_capacity_words'],max_rows=len(graphs))
    tile=cover(original)
    if tile['graph']['operations']!=old['graph']['operations']:raise ValueError('index relocation changes native work or identities')
    if set(tile['graph']['objects'])!=set(old['graph']['objects']):raise ValueError('relocated object identities differ')
    for key,obj in tile['graph']['objects'].items():
        clean=lambda o:{k:v for k,v in o.items() if k not in ('index','external_address')}
        if clean(obj)!=clean(old['graph']['objects'][key]):raise ValueError('relocation changes literal/format/source contract')
    programs={}
    for name,body in data['programs'].items():
        new=deepcopy(body);new['tile_sha256']=digest(tile)
        for e in new['events']:
            if e['op'] in ('LOAD','STORE','STORE_COMMIT'):e['external_address']=tile['graph']['objects'][e['record']]['external_address']
        programs[name]=new
    fixtures=[];checked=0
    for sample,rows in chosen.items():
        values={}
        for f in rows:
            for t,i,v in f['inputs']:
                if (t,i) in values and values[(t,i)]!=v:raise ValueError('actual samples conflict')
                values[t,i]=v
        for body in programs.values():
            got=replay(tile,body,values)['observed_native_outputs'];checked+=1
            for rr,g in enumerate(graphs):
                for primitive,value in reference(ir['primitive_program'],g,values).items():
                    word=got[tile['graph']['primitive_outputs'][f'{rr}:{primitive}']]&0xffffffff
                    if (word-(1<<32) if word&(1<<31) else word)!=value:raise ValueError('actual boundary differs from original primitive program')
        fixtures.append({'inputs':[[t,i,v] for (t,i),v in values.items()],'source_sample':sample,'token_ids':rows[0]['ids'],'element_indices':indices})
    result={'tile':tile,'programs':programs,'fixtures':fixtures,
        'actual_boundary_provenance':{'fixture_sha256':sha,'source_receipt_sha256':hashlib.sha256((a.boundary_directory/'receipt.json').read_bytes()).hexdigest(),
            'prior_job':receipt['job'],'new_full_model_run':False,'native_work_and_local_addresses_preserved':True}}
    a.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'passed':True,'sample_sets':len(fixtures),'elements_per_set':len(indices),'indices':indices,'independent_numeric_traces':checked,
        'scope':'saved actual-weight full-model boundary inputs at explicit original indices, not a new full-model, LC/MC, timing or token/s run'}))


if __name__=='__main__':main()
