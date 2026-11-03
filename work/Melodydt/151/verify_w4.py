# -*- coding: utf-8 -*-
"""Validate bounded W4 evidence hashes/contracts, no simulator invocation."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--output',type=Path);a=ap.parse_args();r=a.root.resolve();w=r/'work/Melodydt/151';j=lambda n:json.loads((w/n).read_text(encoding='utf8'));ex=j('w4-execution-index.json');idx=j('w4-index.json');lock=j('phase2-source-lock.json');checks=[];errors=[]
    def need(v,n):
        checks.append(n)
        if not v:errors.append(n)
    need(ex['research_parent']==idx['research_parent']=='0101cc7e1e6d5718455fb45b61c7428439efc09a','research_parent')
    need(ex['baseline_merge']==idx['baseline_merge']==j('w4-baseline-merge.json')['merge_commit']=='0e8e970359452b745cde09f77efeac041df5fd10','merged_baseline')
    need(ex['native_source']==idx['native_source']==lock['selected_PR144_ref']=='707878621b2add4ed218b8c43df2e95c9a56e2ba','native_lock')
    need(idx['new_RTL'] and idx['new_RTL_simulation'] and not any(idx[n] for n in ['W4_full_accepted','W5_full_accepted','full_L4_accepted','full_F_or_A_accepted','P2_fully_accepted','physical_accepted','server_upload_or_jobs']),'bounded_acceptance')
    need(all(x['status']=='not_started' for x in idx['mainlines'][4:]) and idx['mainlines'][3]['id']=='L4','L4_started_L5plus_not_started')
    need(len(lock['core_files'])==14,'native14')
    for f in lock['core_files']:
        p=r/f['path'];b=p.read_bytes();need(sha(p)==f['sha256'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['sha'],'native_frozen:'+f['path'])
    native=j('w4-baseline-merge.json')['native_comparison'];need(len(native)==14 and all(any(x['path']==f['path'] and x['sha']==f['sha'] and x['sha256']==f['sha256'] for x in native) for f in lock['core_files']),'latest_PR144_core_identity')
    expected={'n-r01':29,'f8-r01':25,'regression-p2-w1-r01':47,'regression-w3-r01':67};runs={x['run_id']:x for x in ex['runs']};need(set(runs)==set(expected),'all4_actual_runs_retained')
    receipts={}
    for name,row in runs.items():
        p=r/row['receipt'];d=json.loads(p.read_text(encoding='utf8'));receipts[name]=d;need(sha(p)==row['receipt_sha256'],'receipt_sha:'+name)
        need(d['status']==row['status']=='PASS_REAL_RTL_SIMULATION' and len(d['case_ids'])==row['case_count']==expected[name] and d['case_ids']==row['case_ids'],'case_counts:'+name)
        for f in row['files']:need((r/f['path']).stat().st_size==f['bytes'] and sha(r/f['path'])==f['sha256'],'archive:'+f['path'])
        actual=[]
        for cmd in d['runs']:
            log=p.parent/cmd['log'];s=log.read_text(encoding='utf8');need(sha(log)==cmd['log_sha256'] and cmd['exit_code']==0,'log_exit_sha:'+name+':'+cmd['label'])
            if cmd['label'].startswith('simulation-'):
                actual+=re.findall(r'CASE_PASS ([A-Z][A-Z0-9_]+)',s);need(not re.search(r'FAIL_(W4|W3|P2|W1)|Fatal:',s),'no_failure_trace:'+name+':'+cmd['label'])
        need(actual==d['case_ids'] and len(actual)==len(set(actual)),'case_order_unique:'+name)
        need(not d['scope']['server_or_SSH'] and not d['scope']['physical'],'execution_scope:'+name)
        for f in d['inputs']:
            path=f.get('path','').replace('\\','/');q=r/path
            if q.is_file() and sha(q)==f['sha256']:continue
            fallback=w/f['name'] if f.get('scope')=='run_script' else w/'w4-rtl-evidence/prior-inputs'/f['name']
            need(fallback.is_file() and sha(fallback)==f['sha256'],'actual_input_or_preserved_prior:'+name+':'+f['name'])
    for f in ex['final_files']:need((r/f['path']).stat().st_size==f['bytes'] and sha(r/f['path'])==f['sha256'],'final_files:'+f['path'])
    for name,top,marker,cycles in [('n-r01','block_w4_n_tb','PASS_W4_N',20336),('f8-r01','block_w4_f8_tb','PASS_W4_F8_FFN8',16323)]:
        p=(r/runs[name]['receipt']).parent;log=(p/('simulation-'+top+'.log')).read_text(encoding='utf8');need(re.search(marker+' cases='+str(expected[name])+' cycles='+str(cycles)+r'\b',log) is not None,'actual_final_summary:'+name)
    need(receipts['regression-p2-w1-r01']['research_parent']=='bfe62ad179af72aef591622aa5c7a000f5d8b681' and receipts['regression-w3-r01']['research_parent']=='99d6df2e094febe4ea8fc9896301adbbfdc803ed','inherited_metadata_preserved')
    need('byte-identical' in ex['inherited_runner_metadata'],'historical_labels_explained')
    nv=j('w4-n-vectors.json');fv=j('w4-f8-vectors.json');need(len(nv['vectors'])==11 and len(fv['vectors'])==6,'11N_6F8_vectors')
    need({x['count'] for x in nv['vectors']}=={1,8,9,257},'actual_bounded_count_set')
    need(nv['provenance']['EXP']['validation']['math_nodes']==1025 and nv['provenance']['EXP']['validation']['all_equal'] and nv['provenance']['G']['validation']['parsed_nodes']==2564,'math_EXP_G_tables')
    need(fv['normal_counts']['S_requests_ACKs']==39 and fv['normal_counts']['S_write']==29 and fv['normal_counts']['S_read']==10 and fv['normal_counts']['N_native_commands_responses']==4,'normal_F8_counts')
    for x in fv['vectors']:
        e=x['expected'];need(e['residual']==[8*v for v in x['x']],'original_residual:'+x['id']);need(e['S_words_hex']['475']==('%04x'%1024)*8,'fixed_gamma:'+x['id'])
    prior=w/'w4-rtl-evidence/prior-inputs/build_w4_vectors.py';rp=j('w4-generator-reproduction.json');need(sha(prior)==rp['prior_builder_sha256'] and sha(w/'build_w4_vectors.py')==rp['current_builder_sha256'],'repro_fix_old_and_current_builder')
    need(all(rp[n]['fresh_directory_equal'] for n in ['w4-n-vectors.json','w4-f8-vectors.json','block_w4_n_tb.sv','block_w4_f8_tb.sv']),'agent_reproduction_record')
    oracle=j('w4-oracle-checks.json');need(oracle['status']=='PASS_PYTHON_ONLY_NOT_RTL_EXECUTION' and oracle['N_vectors']==11 and oracle['F8_vectors']==6,'integer_oracle_scope')
    need(oracle['files']['w4_integer_reference.py']==sha(w/'w4_integer_reference.py'),'integer_oracle_source_hash')
    result={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,'check_count':len(checks),'checks':checks,'errors':errors,'script_sha256':sha(Path(__file__)),'scope':'hash/log/contract validation only; actual ModelSim runs separately archived; not external PR approval'}
    if a.output:a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks':len(checks),'errors':errors}));raise SystemExit(0 if not errors else 1)
if __name__=='__main__':main()
