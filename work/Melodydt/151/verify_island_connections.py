# -*- coding: utf-8 -*-
"""Cross-check source identities, existing evidence and proposed route coverage."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, sys
from urllib.parse import urlsplit, unquote

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--source-dir',type=Path,help='optional separately fetched source tree; never uploaded by this tool')
    p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();w=r/'work/Melodydt/151'
    j=lambda n:json.loads((w/n).read_text(encoding='utf8'))
    idx=j('island-connection-index.json');inp=j('island-connection-inputs.json')
    routes=j('island-variant-routes.json');plan=j('island-sync-plan.json');e=j('island-connection-evidence.json')
    bom=j('block-variant-models.json');road=j('seven-stage-roadmap.json');receipt=j('phase2-rtl-evidence/run-receipt.json')
    errors=[];checks=[]
    def need(ok,name):
        checks.append(name)
        if not ok:errors.append(name)
    parent='051fddb9a3d2cecd4b76c43d07ec8581db9402ce';leaf='707878621b2add4ed218b8c43df2e95c9a56e2ba'
    need(idx['research_parent']==inp['research_parent']==routes['research_parent']==plan['input_commit']==e['research_parent']==parent,'research_parent')
    need(idx['leaf_source']==inp['leaf_source']==routes['leaf_source']==plan['leaf_source_commit']==e['native_source']==leaf,'native_source')
    expected={'A_plain','A_gate','F','D','H','X'}
    rb={x['variant_id']:x for x in routes['variant_rows']};mb={x['variant_id']:x for x in bom['variant_rows']}
    need(set(rb)==set(mb)==set(idx['variants'])==expected,'six_variants_BOM_and_routes')
    for n in expected:need(rb[n]['macro_counts']==mb[n]['counts'],'BOM_unchanged:'+n)
    need(not any(idx[k] for k in ['new_RTL','new_simulation','server_upload_or_jobs','P2_fully_accepted','P3_P7_started','complete_profiles_accepted','direct49_links_assumed']),'no_excess_implementation_claim')
    need(not routes['scope']['implementation_status_audited_here'],'route_roles_not_implementation_audit')
    need(road['current']['stage']=='P2' and all(s['status']=='not_started' for s in road['stages'] if s['id'] in ['P3','P4','P5','P6','P7']),'original_route_progress_retained')
    need(len(e['components'])==16 and len({x['id'] for x in e['components']})==16,'16_distinct_component_findings')
    need(e['summary']['current_RTL_directories_listed']==12 and e['summary']['new_tests_or_simulations_run']==0,'remote_inventory_and_no_new_tests')
    paths={x['path']:x for x in e['current_sources']}
    for x in e['current_sources']:
        need(x['ref']==parent and re.fullmatch('[a-f0-9]{40}',x['git_blob_sha']) and re.fullmatch('[a-f0-9]{64}',x['sha256']),'source_identity:'+x['path'])
    for x in e['components']:
        need(all(n in paths for n in x['source_paths']),'component_sources:'+x['id'])
        need(not x['new_physical_qualification_claim'],'no_physical_transfer:'+x['id'])
    p2=e['P2_existing_test_evidence'];need(p2['case_ids']==receipt['case_ids'] and len(p2['case_ids'])==19 and not p2['P2_fully_accepted'],'P2_retained_19_cases_not_phase_exit')
    actual_inputs={x['name']:x['sha256'] for x in receipt['inputs']}
    for x in p2['five_new_RTL_TB_source_bindings']:
        need(x['path'] in paths and paths[x['path']]['sha256']==x['sha256']==actual_inputs[Path(x['path']).name] and x['matches_actual_P2_run_input'],'P2_source_bound:'+x['path'])
    pr=e['PR133'];need(pr['state']=='open' and not pr['merged'] and not e['historical_source']['current051_presence'],'PR133_not_current_bridge')
    need('project/rtl/wide_service/memory_link.sv' in paths and e['historical_source']['path'] not in paths,'external_target_bridge_not_T6K_or_linkclose')
    for x in inp['files']:
        raw=(r/x['path']).read_bytes();need(len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256'],'input_bytes:'+x['path'])
    checked_sources=0;missing_sources=[]
    source_rows=list(e['current_sources'])
    if a.source_dir:
        for x in source_rows:
            f=a.source_dir/x['path']
            if not f.exists():f=r/x['path']
            if not f.exists():missing_sources.append(x['path']);continue
            raw=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            need(blob==x['git_blob_sha'] and hashlib.sha256(raw).hexdigest()==x['sha256'] and len(raw)==x['bytes'],'source_bytes:'+x['path']);checked_sources+=1
        x=e['historical_source'];f=a.source_dir/'history'/x['ref']/x['path']
        if f.exists():
            raw=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            need(blob==x['git_blob_sha'] and hashlib.sha256(raw).hexdigest()==x['sha256'],'historical_bridge_bytes');checked_sources+=1
        else:missing_sources.append('history/'+x['path'])
        need(not missing_sources,'all_requested_source_bytes_present')
    link_count=0
    for n in idx['reports']+['docs/decisions/2026-11-01-local-island-ports-and-shared-materialization.md']:
        f=r/n;raw=f.read_bytes();text=raw.decode('utf8')
        need(b'\r' not in raw and raw.endswith(b'\n') and all(z.rstrip()==z for z in text.splitlines()),'UTF8_LF:'+n)
        for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)',text):
            u=urlsplit(target.strip('<>'));link_count+=1
            if not u.scheme and u.path:need((f.parent/unquote(u.path)).exists(),'local_link:'+n+':'+target)
    out={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,'python':sys.version,
         'research_parent':parent,'native_source':leaf,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'checks_count':len(checks),'checks':checks,'errors':errors,'source_byte_checks':checked_sources,
         'source_bytes_status':'verified_requested_sources' if a.source_dir else 'NOT_EXECUTED_use_optional_source_dir',
         'source_missing':missing_sources,'document_links':link_count,
         'scope':'source identity/evidence boundary/role and work-package consistency only; not RTL, numeric, liveness, performance or physical acceptance'}
    if a.output:a.output.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks':len(checks),'source_byte_checks':checked_sources,'errors':errors},ensure_ascii=False))
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
