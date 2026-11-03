# -*- coding: utf-8 -*-
"""Verify bounded W3 actual-run provenance and frozen numerical inputs, no simulator."""
from pathlib import Path
import argparse,hashlib,json,re,sys
from datetime import datetime,timezone
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--output',type=Path);a=ap.parse_args();r=a.root.resolve();w=r/'work/Melodydt/151';read=lambda n:json.loads((w/n).read_text(encoding='utf8'))
    ex=read('w3-execution-index.json');idx=read('w3-index.json');lock=read('phase2-source-lock.json');v=read('w3-contract-vectors.json');checks=[];errors=[]
    def need(ok,name):
        checks.append(name)
        if not ok:errors.append(name)
    need(ex['research_parent']==idx['research_parent']==v['input_parent']=='99d6df2e094febe4ea8fc9896301adbbfdc803ed','research_parent')
    need(ex['native_source']==idx['native_source']==v['native_source']==lock['selected_PR144_ref']=='707878621b2add4ed218b8c43df2e95c9a56e2ba','native_source')
    need(idx['new_RTL'] and idx['new_RTL_simulation'] and not any(idx[x] for x in ['W3_full_accepted','P2_fully_accepted','full_F_accepted','full_models_accepted','physical_accepted','server_upload_or_jobs']),'bounded_scope')
    need(all(x['status']=='not_started' for x in idx['mainlines'][3:]),'L4_to_L8_not_started')
    need(len(lock['core_files'])==14,'14_core_source_lock')
    for f in lock['core_files']:
        p=r/f['path'];b=p.read_bytes();need(sha(p)==f['sha256'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['sha'],'native_frozen:'+f['path'])
    expected={'regression-r01':47,'ffn-r01':19,'ffn-r02':21,'adapters-r01':46};runs={x['run_id']:x for x in ex['runs']};need(set(runs)==set(expected),'all4_actual_attempts_retained')
    receipts={}
    for name,row in runs.items():
        p=r/row['receipt'];d=json.loads(p.read_text(encoding='utf8'));receipts[name]=d
        need(sha(p)==row['receipt_sha256'],'receipt_hash:'+name)
        need(d['status']==row['status']=='PASS_REAL_RTL_SIMULATION' and d['case_ids']==row['case_ids'] and len(d['case_ids'])==expected[name],'actual_case_count:'+name)
        for f in row['files']:need((r/f['path']).stat().st_size==f['bytes'] and sha(r/f['path'])==f['sha256'],'archive:'+f['path'])
        parsed=[]
        for cmd in d['runs']:
            log=p.parent/cmd['log'];s=log.read_text(encoding='utf8');need(sha(log)==cmd['log_sha256'] and cmd['exit_code']==0,'log_exit_hash:'+name+':'+cmd['label'])
            if cmd['label'].startswith('simulation-'):
                parsed+=re.findall(r'CASE_PASS ([A-Z][A-Z0-9_]+)',s);need(not re.search(r'FAIL_(W3|W1|P2)|Fatal:',s),'no_failure_trace:'+name+':'+cmd['label'])
        need(parsed==d['case_ids'] and len(parsed)==len(set(parsed)),'case_order_and_unique:'+name)
        need(not d['scope']['server_or_SSH'] and not d['scope']['physical'],'execution_scope:'+name)
        for f in d['inputs']:
            path=f.get('path','').replace('\\','/');current=r/path
            if current.is_file() and sha(current)==f['sha256']:continue
            old=[r/n for n in row['prior_changed_inputs'] if Path(n).name==f['name']]
            # The local runner path was outside root during execution; final runner is copied byte-for-byte.
            if f.get('scope')=='run_script':old=[w/f['name']]
            need(any(q.is_file() and sha(q)==f['sha256'] for q in old),'input_current_or_preserved:'+name+':'+f['name'])
    for f in ex['final_files']:need((r/f['path']).stat().st_size==f['bytes'] and sha(r/f['path'])==f['sha256'],'final_source:'+f['path'])
    need(len(runs['ffn-r01']['prior_changed_inputs'])==1 and not runs['ffn-r02']['prior_changed_inputs'] and not runs['adapters-r01']['prior_changed_inputs'],'old_FFN_TB_preserved')
    for name,marker,cycles in [('ffn-r02','PASS_W3_FFN8',7524),('adapters-r01','PASS_W3_ADAPTERS',2231)]:
        p=(r/runs[name]['receipt']).parent;log='\n'.join(q.read_text(encoding='utf8') for q in p.glob('simulation-*.log'));need(re.search(marker+r' cases='+str(expected[name])+r' cycles='+str(cycles)+r'\b',log) is not None,'actual_final_summary:'+name)
    need(receipts['regression-r01']['research_parent']=='bfe62ad179af72aef591622aa5c7a000f5d8b681' and 'historical' in ex['regression_metadata_note'],'inherited_runner_label_not_rewritten')
    need(v['contract']['normal_counts']=={'S_requests_ACKs':32,'S_write':26,'S_read':6,'M_commands_responses':15,'loader_accept_done':3,'T_words':1,'E_services':2,'G_services':1},'finite_frame_counts')
    need(v['table_provenance']['table_validation']['equal_all_nodes'] and v['table_provenance']['table_validation']['parsed_nodes']==2564 and v['table_provenance']['oracle_uses_math_not_table_values'],'independent_math_table_nodes')
    need(len(v['vectors'])==6 and v['vectors'][2]['expected']['S_words_hex']['473']=='7fff'*8 and v['vectors'][3]['expected']['S_words_hex']['473']=='8000'*8,'six_vectors_extreme_clipping')
    oracle=read('w3-oracle-checks.json');need(oracle['status']=='PASS_PYTHON_INTEGER_ORACLE_AND_SOURCE_TABLE_CHECKS_ONLY' and oracle['contract_sha256']==sha(w/'w3-contract-vectors.json') and oracle['reference_sha256']==sha(w/'w3_integer_reference.py') and not oracle['new_RTL_execution_by_oracle_agent'],'oracle_receipt_scope_hash')
    result={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,'check_count':len(checks),'checks':checks,'errors':errors,'script_sha256':sha(Path(__file__)),'scope':'hash/log/contract evidence validation only; actual RTL runs separately retained; not new simulation or external PR approval'}
    if a.output:a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks':len(checks),'errors':errors}));raise SystemExit(0 if not errors else 1)
if __name__=='__main__':main()
