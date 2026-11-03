"""Check P2 source lock, tested RTL bytes, actual logs and scope. Not simulation."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,unquote
from build_phase1_native import TOPS,parse_ports,port_signature

AUX='work/Melodydt/151/'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();A=r/AUX
    j=lambda n:json.loads((A/n).read_text(encoding='utf8'))
    errors=[]
    def need(ok,what):
        if not ok:errors.append(what)
    lock=j('phase2-source-lock.json');ports=j('phase2-native-ports.json');old=j('phase1-native-contract.json')
    rtl=j('phase2-rtl-evidence/run-receipt.json');status=j('phase2-verification-status.json');idx=j('phase2-index.json')
    roadmap=j('seven-stage-roadmap.json');peer=j('phase2-independent-review.json')
    need(lock['selected_PR144_ref']==idx['selected_PR144_ref']==rtl['source_ref']==
         '707878621b2add4ed218b8c43df2e95c9a56e2ba','selected_ref')
    need(len(lock['core_files'])==14 and sum(x['changed'] for x in lock['core_files'])==1,'core14_changed1')
    for x in lock['core_files']:
        raw=(r/x['path']).read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        need(len(raw)==x['bytes'] and blob==x['sha'] and h(r/x['path'])==x['sha256'],'core:'+x['path'])
    count=0
    for key,(path,module) in TOPS.items():
        actual=parse_ports((r/path).read_text(encoding='utf8'),module);count+=len(actual)
        need(actual==ports['macros'][key]['ports'] and port_signature(actual)==port_signature(old['macros'][key]['ports']),'ports:'+key)
    need(count==149 and ports['total_ports']==149,'ports149')
    need(rtl['status']=='PASS_REAL_RTL_SIMULATION' and rtl['native_compile_passed'] and len(rtl['case_ids'])==len(set(rtl['case_ids']))==19,'actual_RTL19')
    need(set(rtl['pass_markers'])=={'PASS_P2_S_CTRL','PASS_P2_MST'} and len(rtl['runs'])==6,'actual_markers6commands')
    byname={x.name:x for x in r.joinpath('project/rtl/block_connection_p2').glob('*.sv')}
    byname.update({x.name:x for x in r.joinpath('project/tb/block_connection_p2').glob('*.sv')})
    byname.update({Path(x['path']).name:r/x['path'] for x in lock['core_files']})
    byname.update({'phase2-source-lock.json':A/'phase2-source-lock.json','phase1-mst-vectors.json':A/'phase1-mst-vectors.json','run_phase2_mst.py':A/'run_phase2_mst.py'})
    for x in rtl['inputs']:
        need(x['name'] in byname and h(byname[x['name']])==x['sha256'],'tested_bytes:'+x['name'])
    evidence=A/'phase2-rtl-evidence'
    for x in rtl['runs']:
        need(x['exit_code']==0 and (evidence/x['log']).exists() and h(evidence/x['log'])==x['log_sha256'],'actual_log:'+x['label'])
    helper=(evidence/'simulation-helper.log').read_text(encoding='utf8');mst=(evidence/'simulation-mst.log').read_text(encoding='utf8')
    need(len(re.findall(r'CASE_PASS H\d\d_',helper))==6 and len(re.findall(r'CASE_PASS M\d\d_',mst))==13,'actual_case_tokens')
    need('cycles=1101' in mst and 'Sreq=113 Sack=112' in mst and 'Errors: 0, Warnings: 0' in mst,'actual_trace_totals')
    need(not rtl['scope']['physical_validation'] and not rtl['scope']['whole_model_validation'] and not rtl['scope']['SSH_or_server_used'],'bounded_scope')
    req=status['requirements'];oldplan=j('phase1-verification-plan.json')['requirements']
    need({x['id'] for x in req}=={x['id'] for x in oldplan} and len(req)==33,'keep_all33requirements')
    need(not status['P2_fully_accepted'] and not idx['P3_P7_started'] and not idx['common_base_frozen'],'no_false_acceptance')
    need(roadmap['current']['stage']=='P2' and all(x['status']=='not_started' for x in roadmap['stages'] if x['id'] in ['P3','P4','P5','P6','P7']),'route_current_onlyP2')
    need(status['resource_feedback']['new_control_declared_bits']==419 and status['resource_feedback']['ROM_bits']==336,'declared_resources')
    # Resolve newly introduced links in current reports and decision.
    docs=['docs/PHASE2_MST_IMPLEMENTATION.md','docs/decisions/2026-11-01-p2-latest-rtl-and-mst-prototype.md']
    for name in docs:
        for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)',(r/name).read_text(encoding='utf8')):
            u=urlsplit(target)
            if not u.scheme and u.path:need((r/name).parent.joinpath(unquote(u.path)).exists(),'link:'+target)
    out={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,
         'selected_PR144_ref':lock['selected_PR144_ref'],'research_parent':lock['research_parent'],
         'checks':{'core_files':14,'changed_leaf_files':1,'native_macros':7,'native_ports':149,'RTL_CASE_PASS':19,'actual_tool_commands':6,'requirements_retained':33,'P2_fully_accepted':False},
         'errors':errors,'execution_code_commit':'new checker uncommitted at execution; source SHA in phase2-checks; delivery commit bound by PR',
         'not_executed':['full P2 acceptance matrix','P3-P7','synthesis/P&R/physical qualification','whole model/MEM platform','Projects sync']}
    if a.output:a.output.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks':out['checks'],'errors':errors},ensure_ascii=False));return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
