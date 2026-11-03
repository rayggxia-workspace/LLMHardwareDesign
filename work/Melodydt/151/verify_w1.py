# -*- coding: utf-8 -*-
"""Verify W1 real-run evidence/source bindings; does not invoke a simulator."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,unquote
import argparse,hashlib,json,re,sys
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--output',type=Path);a=ap.parse_args();r=a.root.resolve();w=r/'work/Melodydt/151';j=lambda n:json.loads((w/n).read_text(encoding='utf8'))
    idx=j('w1-index.json');ex=j('w1-execution-index.json');c=j('w1-contract.json');rev=j('w1-independent-review.json');lock=j('phase2-source-lock.json');w0=j('w0-evidence-gates.json');old=j('phase2-rtl-evidence/run-receipt.json')
    checks=[];errors=[]
    def need(ok,n):
        checks.append(n)
        if not ok:errors.append(n)
    need(idx['research_parent']==ex['research_parent']==c['research_parent']=='bfe62ad179af72aef591622aa5c7a000f5d8b681','research_parent')
    need(idx['native_source']==ex['native_source']==lock['selected_PR144_ref']=='707878621b2add4ed218b8c43df2e95c9a56e2ba','native_ref')
    need(idx['new_RTL'] and idx['new_RTL_simulation'] and not any(idx[x] for x in ['W1_full_accepted','P2_fully_accepted','full_profiles_accepted','physical_accepted','server_upload_or_jobs']),'bounded_actual_RTL_claim')
    need(all(x['status']=='not_started' for x in idx['mainlines'][2:]) and idx['mainlines'][1]['id']=='L2','later_mainlines_not_started')
    need(len(lock['core_files'])==14,'14_locked_core_files')
    for f in lock['core_files']:
        p=r/f['path'];raw=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        need(sha(p)==f['sha256'] and blob==f['sha'],'frozen_native:'+f['path'])
    runs={x['run_id']:x for x in ex['runs']};need(set(runs)=={'regression-r01','w1-r01','w1-r02','w1-r03'},'all_attempts_retained')
    receipts={}
    for name,row in runs.items():
        p=r/row['receipt'];d=json.loads(p.read_text(encoding='utf8'));receipts[name]=d
        need(sha(p)==row['receipt_sha256'],'receipt_hash:'+name)
        need(d['status']==row['status'] and d['case_ids']==row['case_ids'] and len(d['case_ids'])==row['case_count'],'run_summary:'+name)
        for f in row['files']:need((r/f['path']).stat().st_size==f['bytes'] and sha(r/f['path'])==f['sha256'],'archive_hash:'+f['path'])
        parsed=[]
        for ent in d['runs']:
            log=p.parent/ent['log'];s=log.read_text(encoding='utf8');need(sha(log)==ent['log_sha256'],'actual_log:'+name+':'+ent['label'])
            if ent['label'].startswith('simulation-'):
                parsed+=re.findall(r'CASE_PASS ([A-Z][A-Z0-9_]+)',s)
                need(ent['exit_code']==0 and not re.search(r'FAIL_(P2|W1)|Fatal:',s),'simulation_exit_and_trace:'+name+':'+ent['label'])
        need(parsed==d['case_ids'] and len(parsed)==len(set(parsed)),'actual_case_markers:'+name)
        need(not d['scope']['server_or_SSH'] and not d['scope']['physical'] and not d['scope']['whole_model'],'execution_scope:'+name)
    need(receipts['regression-r01']['status']=='PASS_REAL_RTL_SIMULATION' and receipts['regression-r01']['case_ids']==old['case_ids'] and len(old['case_ids'])==19,'P2_regression_19_same_cases')
    need(receipts['w1-r01']['status']=='FAILED_OR_BLOCKED' and next(x for x in receipts['w1-r01']['runs'] if x['label']=='compile')['exit_code']==2 and not receipts['w1-r01']['case_ids'],'r01_failure_not_hidden')
    need(receipts['w1-r02']['status']=='PASS_REAL_RTL_SIMULATION' and len(receipts['w1-r02']['case_ids'])==28,'r02_retained_weaker_TB_pass')
    final=receipts['w1-r03'];ids=set(final['case_ids']);need(final['status']=='PASS_REAL_RTL_SIMULATION' and len(ids)==28 and all(x['exit_code']==0 for x in final['runs']),'final_r03_real_28_pass')
    finalp=(r/runs['w1-r03']['receipt']).parent
    log=(finalp/'simulation-block_w1_mst_tb.log').read_text(encoding='utf8')
    summary=re.search(r'PASS_W1_MST cases=(\d+) cycles=(\d+) inputAccept=(\d+) ingressReq=(\d+) ingressACK=(\d+) resultReq=(\d+) resultACK=(\d+) readReq=(\d+) readACK=(\d+) Mcmd=(\d+) Mrsp=(\d+) Ttake=(\d+)',log)
    values=list(map(int,summary.groups())) if summary else []
    need(values==[28,4422,240,239,237,97,96,96,96,176,175,92],'actual_final_counters_with_aborted_pending_work')
    paths={f['path'].replace('\\','/'):f for f in final['inputs'] if 'path' in f}
    for f in ex['final_files']:
        need(sha(r/f['path'])==f['sha256'],'final_file_hash:'+f['path'])
        if f['path'].startswith('project/'):need(f['path'] in paths and paths[f['path']]['sha256']==f['sha256'],'executed_final_source:'+f['path'])
    need(next(f for f in final['inputs'] if f['scope']=='run_script')['sha256']==sha(w/'run_w1_mst.py'),'executed_runner_byte_identity')
    for f in old['inputs']:
        if f.get('scope') in ['new_helper_RTL','new_MST_RTL','testbench']:
            candidates=list((r/'project/rtl/block_connection_p2').glob(f['name']))+list((r/'project/tb/block_connection_p2').glob(f['name']))
            if candidates:need(len(candidates)==1 and sha(candidates[0])==f['sha256'],'P2_original_source_unchanged:'+f['name'])
    for run in ['w1-r01','w1-r02']:
        for path in runs[run]['prior_changed_inputs']:
            p=r/path;original=next(f for f in receipts[run]['inputs'] if f['name']==p.name);need(sha(p)==original['sha256'],'prior_changed_input:'+path)
    coverage={
      'W1_INPUT8_STORED_BEFORE_START':['W1_INPUT8_STORED_BEFORE_START','W1_EARLY_START_PULSE_NOT_QUEUED'],
      'W1_VARIABLE_DOT8_ORACLE':['W1_DOT8_LITERAL_P2','W1_DOT8_ZERO','W1_DOT8_MAX_POSITIVE','W1_DOT8_MIN_NEGATIVE','W1_DOT8_DISTINCT_COLUMNS'],
      'W1_CANONICAL_PADDING_AND_STALE_RAM':['W1_CANONICAL_PADDING_AND_STALE_RAM'],
      'W1_TWO_DIFFERENT_FRAMES_NO_STALE_COMPLETE':['W1_TWO_DIFFERENT_FRAMES_NO_STALE_COMPLETE'],
      'W1_INPUT_OUTPUT_DONE_BACKPRESSURE':['W1_INPUT_OUTPUT_DONE_BACKPRESSURE','W1_PHASED_S_M_T_COUNTS_AND_HELD_START_ONCE'],
      'W1_RESET_ABORT_FRAME_RUN_DONE':['W1_ABORT_PARTIAL_INPUT_RECOVER','W1_ABORT_INPUT_NATIVE_ACCEPT_PENDING_ACK_RECOVER','W1_ABORT_COMPLETE_NOT_STARTED_RECOVER','W1_ABORT_RUN_PENDING_RESULT_ACK_RECOVER','W1_ABORT_AFTER_CONSUMED_OUTPUT_PREFIX_RECOVER','W1_ABORT_EXISTING_DONE_AND_SAME_EDGE_READY_RECOVER','W1_RESET_PARTIAL_INPUT_RECOVER','W1_RESET_INPUT_NATIVE_ACCEPT_PENDING_ACK_RECOVER','W1_RESET_COMPLETE_NOT_STARTED_RECOVER','W1_RESET_RUN_RECOVER','W1_RESET_AFTER_CONSUMED_OUTPUT_PREFIX_RECOVER','W1_RESET_EXISTING_DONE_RECOVER']}
    need(set(coverage)=={x['name'] for x in w0['W1_minimal_contract']['required_future_tests']},'all_six_W0_future_groups_mapped')
    for n,required in coverage.items():need(set(required)<=ids,'bounded_coverage_group:'+n)
    need('W1_NATIVE_EXEC_DESCRIPTOR_ERROR_RECOVER' in ids,'native_error_and_fresh_frame_recovery')
    need(rev['blocking_findings_open']==0 and rev['acceptance']['source_review_completed'] and not rev['acceptance']['external_PR_independent_approval'] and not rev['acceptance']['whole_W1_complete'],'peer_review_not_external_PR_acceptance')
    need(c['geometry']==w0['W1_minimal_contract']['geometry'] and c['counts']==w0['W1_minimal_contract']['counts'] and c['W0_input']['sha256']==sha(w/'w0-evidence-gates.json'),'W0_fixed_profile_preserved')
    for v in c['oracle']['future_vectors']:
        calc=[sum(v['A'][k]*v['B_columns'][n][k] for k in range(8)) for n in range(8)];need(calc==v['expected_S64'],'independent_vector_math:'+v['id'])
    need(all(g['gate_status']=='OPEN_NOT_EXECUTED' for g in w0['P2_remaining_gates']) and not j('phase2-verification-status.json')['P2_fully_accepted'],'original_P2_exit_not_closed')
    link_count=0
    for name in idx['reports']+['docs/decisions/2026-11-01-w1-fixed-program-variable-tensor-shell.md']:
        p=r/name;raw=p.read_bytes();s=raw.decode('utf8');need(b'\r' not in raw and raw.endswith(b'\n') and all(x.rstrip()==x for x in s.splitlines()),'UTF8_LF:'+name)
        for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)',s):
            u=urlsplit(target.strip('<>'));link_count+=1
            if not u.scheme and u.path:need((p.parent/unquote(u.path)).exists(),'local_link:'+name+':'+target)
    out={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,'python':sys.version,'script_sha256':sha(Path(__file__)),'checks_count':len(checks),'checks':checks,'errors':errors,'W1_cases':28,'P2_regression_cases':19,'final_sim_cycles':4422,'final_sim_counters':values,'W0_minimal_test_group_mapping':coverage,'document_links':link_count,'scope':'source/log/coverage/claim verification of retained actual ModelSim runs; not a fresh RTL run or full W1/model/physical acceptance'}
    if a.output:a.output.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks_count':len(checks),'W1_cases':28,'P2_cases':19,'errors':errors},ensure_ascii=False));return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
