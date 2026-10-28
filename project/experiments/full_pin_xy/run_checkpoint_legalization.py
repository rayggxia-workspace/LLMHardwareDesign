"""Isolated native legalization of the saved SYSTEM ECO checkpoint; not a routed view."""
from pathlib import Path
import csv,datetime,json,os,sys
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'leaf_eco/r08/opentpu_aux-C';proof=json.loads((source/'execution.json').read_text())
    checkpoint=source/'cell_repaired_NOT_ROUTED.odb';assert sha(checkpoint)==proof['files'][checkpoint.name]['sha256']
    assert proof['native_returncode']!=0 and proof['source_unchanged']
    for key in ['pins','pdn','die']:assert sha(source/('before.'+key+'.tsv'))==sha(source/('cell_repaired.'+key+'.tsv'))
    with (source/'before.cell_cost.tsv').open() as f:masters=sorted({r['master'] for r in csv.DictReader(f,delimiter='\t') if r['type']=='CORE_SPACER'})
    assert masters
    out=ROOT/'checkpoint_legalization'/revision;out.mkdir(parents=True,exist_ok=False)
    helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    script=out/'legalize.tcl';script.write_text(helpers+'\n'+ '\n'.join([
      'read_db '+tcl(checkpoint),'fingerprint '+tcl(out/'before'),
      'if {![stage isolated_legalization {detailed_placement -use_diamond_legalizer}]} {close $stages;exit 1}',
      'if {![stage placement_check {check_placement -verbose}]} {close $stages;exit 1}',
      'if {![stage restore_original_filler_master_set {filler_placement -prefix PINXY_ISO_FILL_ {'+' '.join(masters)+'};global_connect;check_placement -verbose}]} {close $stages;exit 1}',
      'fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'placed_NOT_ROUTED.odb'),'close $stages'])+'\n')
    rec={'scope':'ISOLATED_PLACEMENT_ONLY_NOT_ROUTED_OR_PHYSICALLY_QUALIFIED',
      'source_checkpoint':str(checkpoint),'source_sha256':sha(checkpoint),'source_receipt':str(source/'execution.json'),
      'source_receipt_sha256':sha(source/'execution.json'),'source_original_SDC_unchanged_not_used_for_this_placement_only_stage':True,
      'legalizer':'SUPPORTED_DIAMOND','hypothesis':'Test stale routing/timing observers; root cause not established',
      'filler_master_set':masters,'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec['native_returncode']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out),threads=4)
    rec['source_unchanged']=sha(checkpoint)==rec['source_sha256'] and sha(source/'execution.json')==rec['source_receipt_sha256']
    rec['geometry_invariants']={k:((out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv'))) for k in ['pins','pdn','die']}
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('CHECKPOINT_LEGALIZATION',rec['native_returncode'],'NOT_ROUTED_NOT_QUALIFIED',flush=True)
    return rec['native_returncode']


if __name__=='__main__':sys.exit(run(sys.argv[1]))
