"""Verify real boundary provenance, unchanged local program and actual RTL."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from resident_batch_probe import analyse
from resident_survey import reference
from verify_resident_batch import replay


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    read=lambda p:json.loads(p.read_text());r=a.runtime
    old=read(r/'lane-enriched.json');new=read(r/'lane-actual-boundaries-v2.json');ir=read(r/'integer-reference.json')
    if new['tile']['external_capacity_words']!=old['tile']['external_capacity_words']:raise ValueError('external budget changed')
    if new['tile']['scratch_words']!=old['tile']['scratch_words']:raise ValueError('scratch geometry changed')
    fixturefile=r/'actual-boundary-provenance/fixtures.json';provenance=new['actual_boundary_provenance']
    if hashlib.sha256(fixturefile.read_bytes()).hexdigest()!=provenance['fixture_sha256']:raise ValueError('boundary fixture SHA differs')
    source=read(fixturefile);traces=0
    for fixture in new['fixtures']:
        sample=fixture['source_sample'];indices=fixture['element_indices'];values={(t,i):v for t,i,v in fixture['inputs']}
        actual={(t,i):v for f in source if f['sample']==sample and f['element'] in indices for t,i,v in f['inputs']}
        if any(actual.get(key)!=value for key,value in values.items()):raise ValueError('boundary values or original indices changed')
        for name,program in new['programs'].items():
            def local(events):return [{k:v for k,v in e.items() if k!='external_address'} for e in events]
            if local(program['events'])!=local(old['programs'][name]['events']):raise ValueError('relocation changed native or local work')
            seen=replay(new['tile'],program,values)['observed_native_outputs'];traces+=1
            for rr,g in enumerate(new['tile']['graphs']):
                for primitive,value in reference(ir['primitive_program'],g,values).items():
                    word=seen[new['tile']['graph']['primitive_outputs'][f'{rr}:{primitive}']]&0xffffffff
                    if (word-(1<<32) if word&(1<<31) else word)!=value:raise ValueError('actual boundary numeric mismatch')
    rtl=r/'lane-actual-rtl-v2';results=[analyse(rtl,rtl/f'simulate-{i}.log',i) for i in range(4)]
    negative=read(rtl/'run-result.json')['negative'];badk=read(rtl/'negative-k-result.json')
    if negative['returncode']==0 or badk['returncode']==0 or not badk['actual_K_fault'] or not badk['numeric_failure']:raise ValueError('actual-boundary fault controls did not fail')
    result={'passed':True,'real_input_sets':len(new['fixtures']),'elements_per_set':len(new['tile']['graphs']),
        'independent_numeric_traces':traces,'RTL_programs_per_initialization':[v['cases'] for v in results],
        'RTL_manifest_sha256':results[0]['manifest_sha256'],'external_budget_unchanged':True,
        'actual_wrong_row_returncode':negative['returncode'],'actual_wrong_K_returncode':badk['returncode'],
        'scope':'saved real-weight boundary samples with original indices and unchanged local programs; not a new whole-model/loop/LC/MC/SystemC/DRAM/energy/token/s run'}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
