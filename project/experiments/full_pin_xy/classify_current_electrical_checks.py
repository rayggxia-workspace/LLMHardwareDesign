"""Separate actual slew/capacitance findings from mixed timing markers.

Closed current-source reports only; no fresh checks, no weakened constraints.
Resolve the worst measured drivers through native fingerprints and BPin list.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
DRIVER=Path(__file__).resolve().parent
CASES={'act':'finalized/act-access-r03/act-C','mxu':'mxu_actual_via_tip/r01','opentpu_aux':'system_stacked_via_route/r01/opentpu_aux-C','gemm':'antenna_incremental_eco/r01/gemm-C','vector':'vector_resume/r01','llaccel_aux':'owned_cap_wire_restore/r01'}

def run(revision,profile='original_current'):
    assert profile in ['original_current','wire13093']
    out=ROOT/'current_electrical_classification'/revision;out.mkdir(parents=True,exist_ok=False)
    expected=json.loads((DRIVER/'deadline_current_sources.json').read_text());rec={'scope':'CLOSED_CURRENT_SOURCE_REPORT_CLASSIFICATION_NOT_NEW_STA_OR_FULL_RULE_QUALIFICATION','source_profile':profile,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'checks_reexecuted':False,'cases':{},'source_SHA':{}}
    cases=dict(CASES);reuse=None
    if profile=='wire13093':
        cases['llaccel_aux']='llsys_wire_pin_retention/r01';path=ROOT/cases['llaccel_aux']/'execution.json';latest=json.loads(path.read_text());assert latest.get('completed_utc') and latest['fresh_DRC_count']==0 and latest['all_closed_sources_unchanged']
        expected['llaccel_aux']=dict(source_ODB=str(path.parent/'routed.odb'),ODB_SHA256=latest['files']['routed.odb']['sha256'])
        prior=ROOT/'current_electrical_classification/r01/execution.json';reuse=json.loads(prior.read_text());assert reuse.get('completed_utc') and not reuse.get('actual_failure') and reuse['all_closed_sources_unchanged'];rec['source_SHA'][str(prior)]=sha(prior)
    try:
        for case,rel in cases.items():
            if reuse and case not in ['act','llaccel_aux']:
                assert reuse['cases'][case]['ODB_SHA256']==expected[case]['ODB_SHA256'];rec['cases'][case]=reuse['cases'][case];rec['cases'][case]['reused_unchanged_source_from']='current_electrical_classification/r01';continue
            folder=ROOT/rel;rp=folder/'execution.json';q=json.loads(rp.read_text());odb=Path(expected[case]['source_ODB']);assert sha(odb)==expected[case]['ODB_SHA256']
            rec['source_SHA'].update({str(rp):sha(rp),str(odb):sha(odb)});index=q.get('files',q.get('outputs',{}))
            matches=[folder/name for name in index if name.endswith('checks.txt')]
            if not matches and case=='act' and profile=='wire13093':
                trial=ROOT/'trials/act-access-r03/act-C/execution.json';tq=json.loads(trial.read_text());assert tq.get('finished_utc') and tq['returncode']==0 and q['clean_byte_identical_to_pre_RCX_source']
                assert expected[case]['ODB_SHA256'] in {m['sha256'] for n,m in tq['outputs'].items() if n.endswith('.odb')}
                report=trial.parent/'timing.checks.txt';assert sha(report)==tq['outputs'][report.name]['sha256'];rec['source_SHA'].update({str(trial):sha(trial),str(report):sha(report)})
                matches=[report];index=dict(index);index[report.name]=tq['outputs'][report.name]
            result={'ODB_SHA256':expected[case]['ODB_SHA256'],'units':'OpenSTA source native report: ns time / fF capacitance; original Nangate liberty units retained','electrical_report_status':'MATCHING_REPORT_NOT_FOUND','full_qualification':False}
            if not matches:rec['cases'][case]=result;continue
            assert len(matches)==1;report=matches[0];assert sha(report)==index[report.name]['sha256'];rec['source_SHA'][str(report)]=sha(report)
            sections={};current='timing_mixed_not_further_classified';allmarkers=0
            for line in report.read_text().splitlines():
                if line.strip() in ['max slew','max capacitance','max fanout']:current=line.strip();sections.setdefault(current,[])
                if '(VIOLATED)' not in line:continue
                allmarkers+=1
                if current=='timing_mixed_not_further_classified':continue
                m=re.match(r'^\s*(\S+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+\(VIOLATED\)',line)
                assert m,(case,current,line)
                sections[current].append({'pin':m[1],'limit':float(m[2]),'actual':float(m[3]),'slack':float(m[4]),'native_report_line':line})
            result.update(electrical_report_status='ACTUAL_SOURCE_REPORT_CLASSIFIED',report=str(report),report_SHA256=sha(report),all_literal_VIOLATED_markers=allmarkers,by_electrical_type={k:{'actual_violating_rows':len(v),'worst_five':sorted(v,key=lambda z:z['slack'])[:5]} for k,v in sections.items()})
            result['remaining_mixed_timing_markers']=allmarkers-sum(len(v) for v in sections.values())
            requested={row['pin'] for rows in sections.values() for row in sorted(rows,key=lambda z:z['slack'])[:5]};instances={p.rsplit('/',1)[0] for p in requested};terms={}
            fingerprints=[folder/name for name in index if name.endswith('.cells.tsv') and name.startswith('after')]
            if not fingerprints:fingerprints=[folder/name for name in index if name.endswith('.cells.tsv') and name.startswith('before')]
            if fingerprints:
                assert len(fingerprints)==1;fp=fingerprints[0];assert sha(fp)==index[fp.name]['sha256'];rec['source_SHA'][str(fp)]=sha(fp)
                for line in fp.open():
                    p=line.split()
                    if p and p[0] in instances:
                        if len(p)==3:terms.setdefault(p[0]+'/'+p[1],{})['native_net']=p[2]
                        elif len(p)>=5:
                            for pin in requested:
                                if pin.rsplit('/',1)[0]==p[0]:terms.setdefault(pin,{})['actual_cell_master']=p[1]
            pinfiles=[folder/name for name in index if name.endswith('.pins.tsv') and name.startswith('after')]
            if pinfiles:
                assert len(pinfiles)==1;pf=pinfiles[0];assert sha(pf)==index[pf.name]['sha256'];rec['source_SHA'][str(pf)]=sha(pf)
                bynet={}
                for line in pf.open():
                    p=line.split()
                    if len(p)==9 and p[2] not in ['POWER','GROUND']:bynet.setdefault(p[3].strip('{}'),[]).append({'pin':p[0].strip('{}'),'direction':p[1],'layer':p[4],'box_DBU':list(map(int,p[5:]))})
                for pin,row in terms.items():row['actual_interface_pins']=bynet.get(row.get('native_net',''),[])
            result['worst_driver_native_correspondence']={p:terms.get(p,{'status':'NOT_RESOLVED_FROM_AVAILABLE_FINGERPRINT'}) for p in sorted(requested)};rec['cases'][case]=result
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in rec['source_SHA'].items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
