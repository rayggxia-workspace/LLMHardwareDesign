"""Minimal real PG test for nine measured placement-replay orientation errors.

Read the immutable routed checkpoint of an already completed route phase, even
while its independent qualification job is still processing. No active file
is modified; the live receipt is saved as a snapshot, never a closed receipt.
"""
from pathlib import Path
import csv,datetime,json,os,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent
def run(revision):
    source=ROOT/'current_driver_sizing/r05/vector';live=source/'execution.json';snapshot=live.read_bytes();q=json.loads(snapshot)
    assert q['native_returncodes']['real_route_RC_STA']==0 and q['source_SHA']
    assert 'VDD\tFAIL\tPSM-0069' in (source/'real_route_RC_STA.stages.tsv').read_text()
    legal=ROOT/'current_driver_sizing/r04/vector';lp=legal/'execution.json';l=json.loads(lp.read_text());poses=legal/'placed.cells.tsv'
    assert l.get('completed_utc') and l['all_closed_sources_unchanged'] and l['native_returncodes']['isolated_geometry_size_and_legalization']==0 and sha(poses)==l['files'][poses.name]['sha256']
    selection=legal/'all_actual_violating_drivers_and_size_contracts.json';assert sha(selection)==l['files'][selection.name]['sha256'];names={r['instance'] for r in json.loads(selection.read_text()) if r['new_master']};assert len(names)==75
    expected={}
    for line in poses.open():
        p=line.split();name=p[0].strip('{}') if p else ''
        if len(p)>=6 and name in names:expected[name]=(p[1],int(p[2].strip('{}')),int(p[3].strip('{}')),p[-2],p[-1])
    assert set(expected)==names
    odb=source/'routed.odb';inputs={str(p):sha(p) for p in [odb,lp,poses,selection]}
    out=ROOT/'vector_pose_power_fix'/revision;out.mkdir(parents=True,exist_ok=False);(out/'source_live_receipt_SNAPSHOT_NOT_TERMINAL.json').write_bytes(snapshot)
    rec={'scope':'MINIMAL_ACTUAL_NINE_ORIENTATION_PG_FIX_NOT_REROUTED_OR_FULL_QUALIFICATION','source_SHA':inputs,
      'source_job_receipt_was_closed_at_start':bool(q.get('completed_utc')),'source_route_phase_returncode':0,
      'source_overall_qualification_not_inherited':True,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'full_qualification':False,'signal_reroute_RC_STA':'NOT_EXECUTED_LOCAL_PG_DIAGNOSIS_ONLY'}
    try:
        specs='set expected_poses {\n'+''.join('{'+tcl(n)+' '+tcl(v[0])+' '+str(v[1])+' '+str(v[2])+' '+v[3]+' '+v[4]+'}\n' for n,v in expected.items())+'}\n'
        (out/'all75_verified_native_poses.tcl').write_text(specs)
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        body=helper+'\nread_db '+tcl(odb)+'\nsource '+tcl(out/'all75_verified_native_poses.tcl')+'\nset b [ord::get_db_block]\nfingerprint '+tcl(out/'before')+r'''
set fixes {};set f [open FIXES w];puts $f "instance\tmaster\tx\ty\told_orientation\tnew_orientation"
foreach r $expected_poses {
 lassign $r name master x y orient status;set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $master || [$i getLocation] ne [list $x $y] || [$i getPlacementStatus] ne $status} {error "Measured legal pose source differs in more than orientation"}
 if {[$i getOrient] ne $orient} {puts $f [join [list $name $master $x $y [$i getOrient] $orient] "\t"];lappend fixes [list $name $orient];$i setOrient $orient;$i setLocation $x $y}
 if {[$i getLocation] ne [list $x $y] || [$i getOrient] ne $orient} {error "Orientation API shifted the verified lower-left pose"}
};close $f
if {[llength $fixes]!=9} {error "Not the measured nine-orientation replay defect"}
stage legal_pose_check {check_placement -verbose}
'''
        body=body.replace('FIXES',tcl(out/'actual9_orientation_fixes.tsv'))
        body+='\n'+'\n'.join(['fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'orientation_corrected_NOT_SIGNAL_REROUTED.odb'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}','close $stages'])
        script=out/'check.tcl';script.write_text(body+'\n');common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_returncode']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out),threads=1)
        rec['original_pin_PG_die_unchanged']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']};assert all(rec['original_pin_PG_die_unchanged'].values())
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    if (out/'stages.tsv').exists():rec['native_stages']={r['stage']:r['status'] for r in csv.DictReader((out/'stages.tsv').open(),delimiter='\t')}
    rec['all_source_geometry_and_closed_legal_inputs_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return int(bool(rec.get('actual_failure')) or rec.get('native_returncode')!=0 or not all(rec.get('native_stages',{}).get(k)=='EXECUTED' for k in ['legal_pose_check','VDD','VSS']) or not rec['all_source_geometry_and_closed_legal_inputs_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
