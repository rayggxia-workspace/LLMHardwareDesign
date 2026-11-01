# -*- coding: utf-8 -*-
"""Validate W0 source identity, role provenance and unchanged acceptance limits."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,unquote

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--latest-source-dir',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
    r=a.root.resolve();w=r/'work/Melodydt/151';j=lambda n:json.loads((w/n).read_text(encoding='utf8'))
    idx=j('w0-index.json');inp=j('w0-inputs.json');lock=j('w0-source-lock.json');native=j('w0-native-contract.json');roles=j('w0-role-contracts.json');gates=j('w0-evidence-gates.json');old=j('island-variant-routes.json')
    errors=[];checks=[]
    def need(ok,n):
        checks.append(n)
        if not ok:errors.append(n)
    parent='bd7cb2f3060c61e5d28a2ece0653dd9336a024af';leaf='707878621b2add4ed218b8c43df2e95c9a56e2ba'
    need(idx['research_parent']==inp['research_parent']==lock['research_parent']==native['research_parent']==roles['parent_commit']==gates['input_parent_full_commit']==parent,'all_parent_refs')
    need(idx['native_source']==inp['native_source']==lock['selected_native_ref']==native['selected_native_ref']==roles['native_source_commit']==gates['leaf_source_commit']==leaf,'all_native_refs')
    need(not any(idx[k] for k in ['W0_independently_accepted','P2_fully_accepted','W1_started','new_RTL','new_simulation','server_upload_or_jobs','full_profiles_accepted']),'preparation_not_acceptance_or_new_execution')
    need(len(idx['mainlines'])==8 and all(x['status']=='not_started' for x in idx['mainlines'][1:]),'only_first_mainline_prepared')
    need(native['source_lock_sha256']==digest(w/'w0-source-lock.json'),'native_source_lock_link')
    core=j('phase2-source-lock.json')['core_files'];core_by={x['path']:x for x in core};latest_count=0
    need(len(lock['core_files'])==14 and {x['path'] for x in lock['core_files']}==set(core_by),'14_core_paths')
    for x in lock['core_files']:
        p=r/x['path'];b=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();oldcore=core_by[x['path']]
        need(x['selected_git_blob_sha']==x['latest_git_blob_sha']==oldcore['sha']==blob and x['selected_sha256']==x['latest_sha256']==oldcore['sha256']==digest(p),'same_core_bytes:'+x['path'])
        if a.latest_source_dir:
            q=a.latest_source_dir/x['path'];need(q.exists() and q.read_bytes()==b,'latest_observed_bytes:'+x['path']);latest_count+=1
    need(native['summary']['ports']==sum(len(v['ports']) for v in native['macros'].values())==149 and native['summary']['channels']==24,'seven_native_ports_and_channels')
    need(set(native['macros'])==set('MNEGRST'),'seven_native_types')
    for x in lock['P2_implementation']['P2_actual_source_hashes']:
        need(digest(r/x['path'])==x['sha256'] and x['matches_actual_run_input'],'P2_actual_run_input:'+x['path'])
    need(gates['actual_P2']['case_count']==19 and not gates['actual_P2']['P2_fully_accepted'],'historical_19_not_full_P2')
    p1=j('phase1-verification-plan.json');original_ids={x['id'] for x in p1['requirements']}
    need({x['id'] for x in gates['all_P1_requirement_trace']}==original_ids and len(original_ids)==33,'33_requirements_preserved')
    need(len(gates['P2_remaining_gates'])==13 and all(x['gate_status']=='OPEN_NOT_EXECUTED' for x in gates['P2_remaining_gates']),'13_P2_gates_stay_open')
    all_rows=[]
    for s in roles['role_shards']:
        p=w/s['file'];raw=p.read_bytes();d=json.loads(raw.decode('utf8'))
        need(len(raw)==s['bytes'] and digest(p)==s['sha256'] and len(d['role_contracts'])==s['role_count'],'role_shard_integrity:'+s['variant'])
        all_rows+=d['role_contracts']
    expected={v['variant_id']+':'+x['edge_id'] for v in old['variant_rows'] for x in v['data_role_edges']}
    need(len(all_rows)==len({x['role_uid'] for x in all_rows})==172 and {x['role_uid'] for x in all_rows}==expected,'172_exact_original_role_keys')
    for x in all_rows:
        need(not x['admission']['full_role_mapping_accepted'] and x['responsibility_work_packages'] and x['validation_obligation'],'role_not_falsely_accepted:'+x['role_uid'])
        pointer=x['source_role_provenance']['json_pointer'].split('/');origin=old['variant_rows'][int(pointer[2])]['data_role_edges'][int(pointer[4])]
        need(origin['edge_id']==x['edge_ID'] and origin['data_role']==x['role'],'role_source_pointer:'+x['role_uid'])
    need(sum(roles['applicability_counts'].values())==172 and roles['applicability_counts']['inactive_for_current_source_options']==5,'conditional_domain_not_172_unconditional_edges')
    for x in inp['files']:need(digest(r/x['path'])==x['sha256'] and (r/x['path']).stat().st_size==x['bytes'],'frozen_input:'+x['path'])
    road=j('seven-stage-roadmap.json');need(road['current']['stage']=='P2' and all(x['status']=='not_started' for x in road['stages'] if x['id'] in ['P3','P4','P5','P6','P7']),'original_P2_P7_status_retained')
    link_count=0
    for n in idx['reports']+['docs/decisions/2026-11-01-w0-versioned-contracts-before-island-shell.md']:
        p=r/n;raw=p.read_bytes();text=raw.decode('utf8');need(b'\r' not in raw and raw.endswith(b'\n') and all(z.rstrip()==z for z in text.splitlines()),'UTF8_LF:'+n)
        for href in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)',text):
            u=urlsplit(href.strip('<>'));link_count+=1
            if not u.scheme and u.path:need((p.parent/unquote(u.path)).exists(),'local_link:'+n+':'+href)
    out={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,'python':sys.version,'checks_count':len(checks),'checks':checks,'errors':errors,'research_parent':parent,'native_source':leaf,'script_sha256':digest(Path(__file__)),'latest_source_byte_comparisons':latest_count,'latest_sources_status':'verified_separately_fetched_frozen_observation' if a.latest_source_dir else 'NOT_EXECUTED_optional_source_dir','role_count':172,'document_links':link_count,'scope':'static source/provenance/contract/acceptance-boundary checks only; no new RTL/compiler/model/physical execution'}
    if a.output:a.output.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks_count':len(checks),'latest_sources':latest_count,'roles':172,'errors':errors},ensure_ascii=False));return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
