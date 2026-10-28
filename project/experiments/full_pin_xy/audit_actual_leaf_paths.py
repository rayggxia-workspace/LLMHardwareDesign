"""Read actual failed ECO SPEF and source SDC; expose paths without relaxing it."""
from pathlib import Path
import datetime,json,os,sys
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision,case):
    assert case in ['vector','opentpu_aux']
    source=ROOT/('vector_resume/r01' if case=='vector' else 'checkpoint_route/r01')
    p=source/'execution.json';j=json.loads(p.read_text());assert j.get('completed_utc')
    old=json.loads((ROOT/'trials/access-r03'/(case+'-C')/'execution.json').read_text())
    odb=source/'routed.odb';spef=source/'extracted.spef';sdc=Path(old['source_sdc'])
    for f in [odb,spef]:assert sha(f)==j['files'][f.name]['sha256']
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    out=ROOT/'actual_path_audit'/revision/case;out.mkdir(parents=True,exist_ok=False)
    inputs={str(f):sha(f) for f in [p,odb,spef,sdc]}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    script=out/'audit.tcl'
    lines=['read_liberty '+tcl(path) for path in old['libs']]+['read_db '+tcl(odb),'read_sdc '+tcl(sdc),
      'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','read_spef '+tcl(spef)]
    for kind in ['setup','hold']:
        lines.append('report_worst_slack -'+('max' if kind=='setup' else 'min')+' -digits 6 > '+tcl(out/(kind+'.txt')))
        lines.append('report_checks -path_delay '+('max' if kind=='setup' else 'min')+' -fields {capacitance slew fanout} -format full_clock_expanded -group_path_count 12 -endpoint_path_count 1 -digits 6 > '+tcl(out/(kind+'_paths.txt')))
        lines.append('report_checks -path_delay '+('max' if kind=='setup' else 'min')+' -format json -group_path_count 12 -endpoint_path_count 1 > '+tcl(out/(kind+'_paths.json')))
    lines+=['report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt'),
      'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt'),
      'check_setup -verbose > '+tcl(out/'constraint_coverage.txt')]
    script.write_text('\n'.join(lines)+'\n')
    rc=execute(common,script,out/'native.log',threads=1)
    rec={'scope':'READ_ONLY_REAL_EXTRACTED_CRITICAL_PATH_DIAGNOSIS_NOT_REPAIR_OR_QUALIFICATION',
      'case':case,'native_returncode':rc,'source_SHA':inputs,'original_SDC_and_extracted_SPEF_preserved':True,
      'source_worst_slacks_exactly_replayed':{},'full_qualification':False,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    for kind in ['setup','hold']:
        q=out/(kind+'.txt');ref=source/(kind+'.txt')
        rec['source_worst_slacks_exactly_replayed'][kind]=q.exists() and ref.exists() and q.read_text()==ref.read_text()
    rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rc==0 and all(rec['source_worst_slacks_exactly_replayed'].values()) and rec['all_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
