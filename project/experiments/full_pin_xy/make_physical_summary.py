"""Summarize actual separate gates without treating process status as qualification."""
from pathlib import Path
from collections import Counter
import argparse,csv,gzip,json,re,tkinter
EXPECTED={'act':860,'mxu':2172,'opentpu_aux':2229,'gemm':3753,'vector':2246,'llaccel_aux':13507}
TCL=tkinter.Tcl()
def read(p):
    if not p.exists():return ''
    return gzip.decompress(p.read_bytes()).decode('utf-8',errors='replace') if p.suffix=='.gz' else p.read_text(encoding='utf-8',errors='replace')
def slack(d,kind):
    m=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',read(d/f'timing.{kind}.txt'));return float(m[1]) if m else None
def summarize(root):
    root=Path(root);base=root/'trial_receipts';summary={c:{'trials':{},'full_C_migration_routed':False,'full_block_connectivity':'NOT_VERIFIED','parent_access':'UNKNOWN original handoff/target layers and version-matched parent paths',
        'full_DRC_GDS_LVS':'NOT_QUALIFIED','full_system_RC_STA_electrical':'NOT_QUALIFIED'} for c in EXPECTED}
    for d in sorted(base.glob('*/trials/*/*')):
        if not d.is_dir():continue
        case=next((c for c in sorted(EXPECTED,key=len,reverse=True) if d.name.startswith(c+'-')),None)
        if not case:continue
        plan=d.name[len(case)+1:];rev=d.parent.name;key=rev+'/'+plan
        p=d/'execution.json'
        if not p.exists():
            summary[case]['trials'].setdefault(key,{'state':'DRIVER_FAILED_OR_NOT_STARTED; consult batch log','snapshot':str(d.relative_to(base))});continue
        j=json.loads(p.read_text());completed=bool(j.get('finished_utc'));log=read(d/'openroad.log.gz')
        stages=list(csv.DictReader(read(d/'stages.tsv').splitlines(),delimiter='\t'))
        bystage={r['stage']:r['status'] for r in stages}
        c={'state':j.get('status','RUNNING_OR_RECEIPT_INCOMPLETE'),'completed':completed,'plan':plan,'selected_pin_count':j.get('selected_pin_count',8),'scheduler_job':j['scheduler_job'],'source_sha256':j['source_sha256'],
           'driver_commit':j['driver_commit'],'source_unchanged':j.get('source_unchanged',False),'failed_stages':[r for r in stages if r['status']=='FAIL'],
           'routed':bystage.get('detailed_route')=='EXECUTED','RCX_executed':bystage.get('extract_rc',bystage.get('baseline_rc'))=='EXECUTED',
           'setup_worst_slack_ns':slack(d,'setup'),'hold_worst_slack_ns':slack(d,'hold'),'raw_receipt':str(p.relative_to(base)),
           'original_external_driver_slew_load_models':'INCOMPLETE inherited boundary constraints; no silent added models',
           'whole_cell_master_XY_orient_connections_unchanged':j.get('fingerprint_checks',{}).get('cells',{}).get('exact_equal',False),
           'pdn_geometry_fingerprint_unchanged':j.get('fingerprint_checks',{}).get('pdn',{}).get('exact_equal',False),
           'die_unchanged':j.get('fingerprint_checks',{}).get('die',{}).get('exact_equal',False)}
        drc=d/'fresh_route.drc';c['fresh_native_DRC_count']=len(re.findall(r'^violation type:',read(drc),re.M)) if drc.exists() and bystage.get('fresh_native_drc')=='EXECUTED' else None
        if drc.exists() and drc.stat().st_size>0 and c['fresh_native_DRC_count']==0:c['fresh_native_DRC_count']='NONEMPTY_REPORT_REQUIRES_PARSE'
        check=read(d/'timing.checks.txt');c['reported_timing_electrical_violator_rows']=sum('(VIOLATED)' in line for line in check.splitlines()) if bystage.get('sta')=='EXECUTED' else None
        c['PSM_VDD_connected']='All shapes on net VDD are connected.' in log;c['PSM_VSS_connected']='All shapes on net VSS are connected.' in log
        for name in ['access.json','independent-access.json']:
            if (d/name).exists():
                access=json.loads((d/name).read_text());c['selected_access_all_terminals_pass']=access['pass'];c['selected_access_nets']=len(access['nets'])
        layers={}
        for layer,length in re.findall(r'^(metal\d+)\s+([\d.]+)um\s+\d+%',log,re.M):layers[layer]=float(length)
        c['actual_routed_wire_length_by_layer_um']=layers;c['actual_routed_wire_length_sum_um']=sum(layers.values()) if layers else None
        before=read(d/'before.pins.tsv.gz');after=read(d/'after.pins.tsv.gz')
        if before and after:
            aa=[TCL.splitlist(line) for line in before.splitlines()];bb=[TCL.splitlist(line) for line in after.splitlines()]
            a=Counter(aa);b=Counter(bb);ar={row[0]:row for row in aa if row[2] not in ['POWER','GROUND']};br={row[0]:row for row in bb if row[2] not in ['POWER','GROUND']}
            assert len(ar)==len(br)==EXPECTED[case] and set(ar)==set(br),(case,key,'actual signal pins changed')
            moved=[]
            for pin,row in ar.items():
                q=br[pin];assert row[:5]==q[:5],(case,key,pin,'function/dir/use/net/layer changed')
                rr=list(map(int,row[5:9]));ss=list(map(int,q[5:9]));assert rr[2]-rr[0]==ss[2]-ss[0] and rr[3]-rr[1]==ss[3]-ss[1],(case,key,pin,'size changed')
                if rr!=ss:moved.append(pin)
            assert len(moved)<=j.get('selected_pin_count',8),(case,key,'unexpected changed pins')
            # All PG rectangles also identical, independently of the SWire fingerprint.
            assert Counter(r for r in aa if r[2] in ['POWER','GROUND'])==Counter(r for r in bb if r[2] in ['POWER','GROUND'])
            c['actual_all_pin_contract_check']={'original_signals':len(ar),'moved_count':len(moved),'moved_pins':moved,'lost_extra_layer_direction_net_use_size_changes':0,'all_PG_pin_rectangles_unchanged':True}
        summary[case]['trials'][key]=c
    for p in sorted(base.glob('*/connectivity/*/*/execution.json')):
        rec=json.loads(p.read_text());src=Path(rec['source_odb']);case=next(c for c in sorted(EXPECTED,key=len,reverse=True) if src.parent.name.startswith(c+'-'))
        key=src.parent.parent.name+'/'+src.parent.name[len(case)+1:];t=summary[case]['trials'].get(key)
        if t and rec.get('result'):
            raw=base/t['raw_receipt'];j=json.loads(raw.read_text());assert j['outputs']['checked.odb']['sha256']==rec['source_sha256'],'Whole connectivity/source mismatch'
            t['whole_multi_terminal_signal_clock_geometry']=rec['result'];t['whole_geometry_receipt']=str(p.relative_to(base))
    for p in sorted(base.glob('*/finalized/*/*/execution.json')):
        rec=json.loads(p.read_text());case=rec['case'];key=rec['revision']+'/'+rec['plan'];t=summary[case]['trials'].get(key)
        if not t:continue
        t['clean_finalization']=rec;t['clean_receipt']=str(p.relative_to(base));t['authoritative_physical_odb']=str(Path(rec['legacy_RC_STA_receipt']).parents[3]/'finalized'/rec['revision']/(case+'-'+rec['plan'])/'clean.odb')
        t['independent_clean_DRC_count']=rec.get('independent_DRC_count');t['post_RCX_ODB_rejected_as_physical_master']=True
        if rec.get('whole_access'):
            t['post_RCX_whole_geometry_diagnostic']=t.get('whole_multi_terminal_signal_clock_geometry')
            t['whole_multi_terminal_signal_clock_geometry']=rec['whole_access']
        if rec.get('selected_access'):t['selected_access_all_terminals_pass']=rec['selected_access']['pass']
        log=read(p.parent/'export.log.gz');lengths={}
        for layer,length in re.findall(r'^(metal\d+)\s+([\d.]+)um\s+\d+%',log,re.M):lengths[layer]=float(length)
        if lengths:t['clean_actual_wire_length_by_layer_um']=lengths;t['clean_actual_wire_length_sum_um']=sum(lengths.values())
    # Router statistics printed BEFORE RCX remain a separate, explicit source.
    for s in summary.values():
        for t in s['trials'].values():
            if not t.get('raw_receipt'):continue
            log=read((base/t['raw_receipt']).parent/'openroad.log.gz')
            lengths={k:float(v) for k,v in re.findall(r'Total wire length on LAYER (metal\d+) = ([\d.]+) um\.',log)}
            if lengths:t['DRT_pre_RCX_wire_length_by_layer_um']=lengths;t['DRT_pre_RCX_wire_length_sum_um']=sum(lengths.values())
            via=re.findall(r'Total number of vias = (\d+)\.',log)
            if via:t['DRT_pre_RCX_vias']=int(via[-1])
    for case,s in summary.items():
        done=[t for t in s['trials'].values() if t.get('completed')];candidates=[t for t in done if t.get('plan')=='C']
        if candidates:
            t=max(candidates,key=lambda t:t['selected_pin_count']);n=t['selected_pin_count'];s['route_status']=f'{n}pin C实际重接完成；完整资格未验证' if t['routed'] else 'C实际试验失败/未完成，见回执'
            s['full_C_migration_routed']=bool(case=='act' and n==740 and t['routed'])
            full=t.get('whole_multi_terminal_signal_clock_geometry',{}).get('pass','待验证')
            s['drc_status']='独立clean进程DRC {}; selected-net连通 {}; 全块几何连通 {}；父层未验证'.format(t.get('independent_clean_DRC_count','待复核'),t.get('selected_access_all_terminals_pass','待补查'),full)
            s['sta_status']='RCX {}; setup {}ns / hold {}ns；电气违例行{}；系统边界不完整'.format(t['RCX_executed'],t['setup_worst_slack_ns'],t['hold_worst_slack_ns'],t['reported_timing_electrical_violator_rows'])
        else:s['route_status']='试验运行/驱动失败；未报告C通过';s['drc_status']='尚未完成';s['sta_status']='尚未完成'
    (root/'physical_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PHYSICAL_SUMMARY_UPDATED',sum(len(s['trials']) for s in summary.values()),'trial receipts; full qualification NOT inferred')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();summarize(a.root)
