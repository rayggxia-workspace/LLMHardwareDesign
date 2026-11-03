"""Check P1 source lock, adopted route and explicit MST fixture; not RTL."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import unquote,urlsplit

AUX='work/Melodydt/151/'
DOCS=['docs/SEVEN_MACRO_INTERFACE_ROADMAP.md','docs/PHASE1_INTERFACE_BASELINE.md',
 'docs/PHASE1_NATIVE_INTERFACE_CONTRACT.md','docs/PHASE1_MST_REFERENCE.md',
 'docs/STEPS_1_3_WORK_REPORT.md','docs/SIX_CONNECTION_SYSTEM_DESIGN.md',
 'docs/SAMPLE_LEGAL_CONNECTION_LEDGER.md','docs/handoffs/2026-10-31-issue-151-six-connections.md',
 'progress/Melodydt/STATUS.md',AUX+'README.md',AUX+'phase1-port-inventory.md',
 'docs/decisions/2026-11-01-seven-macro-route-and-p1-baseline.md']
DATA=['phase1-index.json','phase1-version-comparison.json','seven-stage-roadmap.json',
 'phase1-verification-plan.json','phase1-native-contract.json','phase1_mst_reference.py',
 'phase1-mst-vectors.json','verify_phase1_mst_reference.py','build_phase1_native.py',
 'check_phase1_native.py','phase1-native-checks.json','phase1-native-independent-checks.json',
 'phase1-reference-verification.json','verify_phase1.py']
LINK=re.compile(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();j=lambda n:json.loads((r/AUX/n).read_text(encoding='utf8'))
    idx=j('phase1-index.json');ver=j('phase1-version-comparison.json');native=j('phase1-native-contract.json')
    road=j('seven-stage-roadmap.json');plan=j('phase1-verification-plan.json');vec=j('phase1-mst-vectors.json')
    ref=j('phase1-reference-verification.json');ni=j('phase1-native-independent-checks.json');ng=j('phase1-native-checks.json')
    errors=[]
    def need(ok,name):
        if not ok:errors.append(name)
    locked='643c6012a11cbf461146ac40fbf61485223fe946';parent='343f4d4775ffab61b2ed2df13de243cc659c157a'
    need(idx['research_input_commit']==ver['research_input_commit']==parent,'research_input')
    need(idx['selected_RTL_commit']==ver['selected_RTL_commit']==native['leaf_source_commit']==
         road['source_lock']['current_RTL_commit']==plan['RTL_source_commit']==vec['frozen_leaf_ref']==locked,'selected_RTL')
    need(ver['seven_headers_equal'] and ver['core_equal_count']==13 and ver['core_changed_count']==1,'observed_diff')
    changed=[x for x in ver['core_file_comparison'] if x['changed']]
    need(len(changed)==1 and changed[0]['path']=='project/rtl/block_library_v1/block_v1_r.sv','only_R_changed')
    need(ver['observed_R_git_blob_recomputed']==changed[0]['observed_git_blob'],'observed_R_blob')
    source_count=0
    for x in ver['selected_file_hashes']:
        raw=(r/x['path']).read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        need(blob==x['git_blob_sha'] and hashlib.sha256(raw).hexdigest()==x['sha256'] and len(raw)==x['bytes'],'source:'+x['path']);source_count+=1
    need(source_count==14,'fourteen_sources')
    need(set(native['macros'])==set('MNEGRST') and sum(len(v['ports']) for v in native['macros'].values())==149,'seven_149_ports')
    need(native['scope']['system_has_external_memory'] and not native['scope']['common_base_frozen'] and
         not native['scope']['RTL_combination_verified'] and not native['scope']['latest_upstream_auto_imported'],'native_scope')
    need(ni['result']=='PASS' and ni['channels_checked']==24 and ni['trace_references_checked']>=138,'native_independent')
    need(ng['result']=='PASS' and len(ng['negative_contract_mutations'])==11 and all(z['rejected'] for z in ng['negative_contract_mutations']),'native_mutations')
    stages=road['stages'];by={s['id']:s for s in stages}
    need(list(by)==['P1','P2','P3','P4','P5','P6','P7'],'seven_stage_order')
    need(road['current']['stage']=='P1' and not road['current']['later_stages_started'] and
         not idx['later_stages_started'] and not idx['system_RTL_started'],'only_P1')
    need(all(by[k]['status']=='not_started' and not by[k]['implementation_started'] for k in list(by)[1:]),'later_not_started')
    seen=set();active=set()
    def visit(k):
        if k in active:errors.append('stage_dependency_cycle:'+k);return
        if k in seen:return
        active.add(k)
        for dep in by[k]['depends_on']:
            need(dep in by,'missing_stage_dependency:'+dep)
            if dep in by:visit(dep)
        active.remove(k);seen.add(k)
    for k in by:visit(k)
    req=plan['requirements'];need(len(req)==len({z['id'] for z in req})==33,'requirements33_unique')
    need(all(z['spec_phase']=='P1' and z['execution_phase'] in by and z['evidence'] and
             z['status']==('specified_not_accepted' if z['execution_phase']=='P1' else 'not_executed')
             for z in req),'requirements_future_evidence')
    need(set(z['execution_phase'] for z in req)==set(by),'all_stages_have_evidence')
    f=vec['minimal_mst_profile'];allot=f['allocation']
    need(f['id']=='P2_S8_DOT8_RAW64' and f['a']==[1,-2,3,-4,5,-6,7,-8] and
         f['b_column_constants']==list(range(1,9)) and f['result_s64']==[-4*(n+1) for n in range(8)],'literal_MST_math')
    need([allot[k] for k in ['a_base','b_base','result_base']]==[448,452,456] and
         allot['total_reserved_bytes']==192 and allot['t_words']==4,'MST_allocation')
    need([x['op'] for x in f['commands']]==[6,4,10,3,3,3,3] and f['commands'][2]['data']=='0x9884','MST_commands')
    expected=[]
    for i in range(0,8,2):expected.append('0x%032x'%((f['result_s64'][i]&((1<<64)-1))|((f['result_s64'][i+1]&((1<<64)-1))<<64)))
    need(f['result_s_words_and_t_payload']==expected and f['t_begin']['words']==4,'MST_wire_words')
    need(ref['status']=='PASS_BOUNDED_PYTHON_REFERENCE_ONLY' and ref['checks_total']==527124 and
         not ref['scope']['RTL_executed'] and not ref['scope']['RTL_handshake_passed'],'reference_not_RTL')
    for z in ref['artifacts']:
        if z['name'] in ['phase1_mst_reference.py','phase1-mst-vectors.json','verify_phase1_mst_reference.py']:
            need(hashlib.sha256((r/AUX/z['name']).read_bytes()).hexdigest()==z['sha256'],'reference_artifact:'+z['name'])
    links=0;anchors=0;artifacts=[]
    for name in DOCS+[AUX+n for n in DATA]:
        raw=(r/name).read_bytes();text=raw.decode('utf8')
        need(b'\r' not in raw and raw.endswith(b'\n') and all(z.rstrip()==z for z in text.splitlines()),'whitespace:'+name)
        if name.endswith('.json'):json.loads(text)
        artifacts.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        if not name.endswith('.md'):continue
        for target in LINK.findall(text):
            links+=1;u=urlsplit(target.strip('<>'))
            if not u.scheme and u.path:
                dest=(r/name).parent.joinpath(unquote(u.path)).resolve();need(dest.exists(),'link:'+name+':'+target)
                if dest.is_file() and u.fragment.startswith('L'):
                    mm=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',u.fragment)
                    need(bool(mm) and 1<=int(mm.group(1))<=int(mm.group(2) or mm.group(1))<=len(dest.read_text(encoding='utf8').splitlines()),'anchor:'+target);anchors+=1
    result={'schema_version':1,'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
      'passed':not errors,'research_input_commit':parent,'selected_RTL_commit':locked,'python':sys.version,
      'execution_code_commit':'checker uncommitted at execution; exact source SHA in artifacts, delivery commit in PR receipt',
      'checks':{'stages':7,'current_stage':'P1','future_requirements':33,'selected_core_sources':14,'top_macros':7,'ports':149,
        'channels':24,'source_traces':ni['trace_references_checked'],'negative_contract_mutations':11,
        'bounded_Python_assertions':ref['checks_total'],'MST_reserved_S_bytes':192,'MST_T_bytes':64,
        'markdown_links':links,'source_anchors':anchors,'new_system_RTL':0,'RTL_executions':0,'later_stages_started':False},
      'artifacts':artifacts,'errors':errors,
      'not_executed':['RTL/SystemC/inference','full model compilation/quality','synthesis/P&R','MEM interface/bandwidth implementation','Projects sync']}
    if a.output:a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks':result['checks'],'errors':errors},ensure_ascii=False));return int(bool(errors))

if __name__=='__main__':raise SystemExit(main())
