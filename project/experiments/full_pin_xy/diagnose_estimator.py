"""Isolate VECTOR repair from all GRT/SPEF/incremental state; no constraint waiver."""
from pathlib import Path
import datetime,json,os,subprocess,sys
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    early_fillers=os.environ.get('PINXY_EST_FILLERS_BEFORE_ESTIMATE')=='1'
    source=ROOT/'finalized/access-r03/vector-C';p=source/'execution.json';proof=json.loads(p.read_text())
    assert proof['independent_DRC_count']==0 and proof['whole_access']['pass']
    trial=Path(proof['legacy_RC_STA_receipt']);old=json.loads(trial.read_text());odb=source/'clean.odb';sdc=Path(old['source_sdc'])
    assert sha(odb)==proof['clean_odb_sha256'] and sha(sdc)==old['input_sha256'][str(sdc)]
    model=ROOT/'leaf_timing_models/r07/vector-C/execution.json';m=json.loads(model.read_text())
    assert m['clean_odb_sha256']==sha(odb) and m['SPEF_replay_matches_recorded_trial_1e_minus5_ns']
    out=ROOT/'estimator_diagnosis'/revision;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    # Search only known source roots in the installed image, no network/source
    # substitution. Absence is recorded, not guessed to identify a commit.
    code='''from pathlib import Path
import hashlib,json
records=[]
for root in [Path('/OpenROAD-flow-scripts/tools/OpenROAD/src/est'),Path('/OpenROAD/src/est')]:
 if not root.exists():continue
 for p in root.rglob('*'):
  if not p.is_file() or p.suffix not in ['.cc','.cpp','.hh','.h']:continue
  raw=p.read_bytes();text=raw.decode(errors='replace');lines=text.splitlines()
  for i,line in enumerate(lines):
   if 'inconsistent parasitics state' in line:records.append({'source':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'line':i+1,'context':'\\n'.join(lines[max(0,i-35):i+20])})
print(json.dumps({'matching_installed_source':records,'source_absence_is_not_a_root_cause':not records},indent=2))
'''
    raw=subprocess.check_output(common+[IMAGE,'python3','-c',code]);(out/'installed_EST0104_source.json').write_bytes(raw)
    helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    lines=[helpers]+['read_liberty '+tcl(path) for path in old['libs']]
    lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
      'fingerprint '+tcl(out/'before')]
    if early_fillers:lines+=['if {![stage remove_fillers_before_estimator {remove_fillers}]} {close $stages;exit 1}']
    lines+=[
      'if {![stage isolated_placement_estimator {estimate_parasitics -placement;report_worst_slack -max -digits 6 > '+tcl(out/'HEURISTIC_before.setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'HEURISTIC_before.hold.txt')+'}]} {close $stages;exit 1}',
      'if {![stage isolated_repair_design {'+('' if early_fillers else 'remove_fillers;')+'repair_design -max_utilization 85;write_db '+tcl(out/'cell_repaired_NOT_LEGALIZED_OR_ROUTED.odb')+'}]} {close $stages;exit 1}',
      'report_worst_slack -max -digits 6 > '+tcl(out/'HEURISTIC_after.setup.txt'),
      'fingerprint '+tcl(out/'after'),'close $stages',
      'puts "ISOLATED_ESTIMATOR_TRIAL_NO_GRT_NO_SPEF_NO_INCREMENTAL; not final RC or STA"']
    script=out/'reproduce.tcl';script.write_text('\n'.join(lines)+'\n')
    inputs={str(q):sha(q) for q in [p,trial,odb,sdc,model]}
    rc=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out),threads=4)
    rec={'scope':'ISOLATED_VECTOR_EST0104_DIAGNOSIS_NOT_PHYSICAL_IMPLEMENTATION',
      'change_from_failed_r09':'No GRT initialization, no start_incremental, no SPEF imported in repair process; exact source SPEF separately replayed in matching r07 model',
      'fillers_removed_before_estimation':early_fillers,
      'single_variable_from_isolated_r01':'Move remove_fillers before estimate_parasitics, without changing repair_design or constraints' if early_fillers else 'Baseline isolated ordering: estimate then remove_fillers then repair_design',
      'source_SHA':inputs,'original_SDC_clocks_layers_preserved':True,
      'native_returncode':rc,'actual_final_RC_STA':'NOT_EXECUTED','full_qualification':False,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'all_sources_unchanged':all(sha(Path(k))==v for k,v in inputs.items()),
      'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    rec['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('ISOLATED_ESTIMATOR',rc,flush=True);return rc


if __name__=='__main__':sys.exit(run(sys.argv[1]))
