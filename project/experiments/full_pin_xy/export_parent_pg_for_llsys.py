"""Read actual common-parent PG into unchanged LL local coordinates."""
from pathlib import Path
import datetime,json,os,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_escape_fixture import execute
from run_parent_trial import tcl
DRIVER=Path(__file__).resolve().parent
def run(revision):
    source=ROOT/'common_checkpoint_def_import/r01';rp=source/'execution.json';q=json.loads(rp.read_text());odb=source/'imported_current_NOT_ROUTED_NOT_FROZEN.odb'
    assert q.get('completed_utc') and not q.get('actual_failure') and q['all_closed_sources_unchanged'] and all(q['original_parent_preserved'].values()) and q['all256_shared_geometry_and_graph_preserved']
    assert q['native_stages']['fresh_import.stages.tsv']['VDD']==q['native_stages']['fresh_import.stages.tsv']['VSS']=='EXECUTED'
    assert sha(odb)==q['files'][odb.name]['sha256']
    out=ROOT/'parent_pg_llsys_local'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_PARENT_PG_READONLY_FOR_LEAF_FIRST_HOP_NOT_BASE_QUALIFICATION','source_SHA':{str(p):sha(p) for p in [rp,odb]},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False}
    try:
        body=r'''
set b [ord::get_db_block];set i [$b findInst u_llaccel_aux]
if {$i eq "NULL" || [$i getOrient] ne "R0"} {error "Expected original R0 LL placement missing"}
lassign [$i getLocation] ix iy;set bb [$i getBBox];set maxx [expr {[$bb xMax]-$ix+20000}];set maxy [expr {[$bb yMax]-$iy+20000}]
set f [open OUTPUT w];puts $f "net\tlayer\tx0\ty0\tx1\ty1\tkind"
proc emit {f net layer a c d e ix iy maxx maxy} {
 if {$layer ni {metal5 metal6 metal7 via5 via6}} {return}
 set a [expr {$a-$ix}];set c [expr {$c-$iy}];set d [expr {$d-$ix}];set e [expr {$e-$iy}]
 if {$a>$maxx || $c>$maxy || $d< -20000 || $e< -20000} {return}
 puts $f [join [list $net $layer $a $c $d $e PARENT_PG] "\t"]
}
foreach n [$b getNets] {
 if {[$n getSigType] ni {POWER GROUND}} {continue}
 foreach sw [$n getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} {
   set via [$s getTechVia];if {$via eq "NULL"} {set via [$s getBlockVia]};lassign [$s getViaXY] x y
   foreach z [$via getBoxes] {emit $f [$n getName] [[$z getTechLayer] getName] [expr {$x+[$z xMin]}] [expr {$y+[$z yMin]}] [expr {$x+[$z xMax]}] [expr {$y+[$z yMax]}] $ix $iy $maxx $maxy}
  } else {emit $f [$n getName] [[$s getTechLayer] getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax] $ix $iy $maxx $maxy}
 }}
};close $f
set f [open TRANSFORM w];puts $f [list R0 $ix $iy [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$b getDbUnitsPerMicron]];close $f
help pin_access
if {[llength [info commands pin_access]]} {set f [open APBODY w];puts $f [info body pin_access];close $f}
'''
        for a,b in [('OUTPUT',out/'actual_parent_PG_local.tsv'),('TRANSFORM',out/'actual_transform.tsv'),('APBODY',out/'native_pin_access_body.txt')]:body=body.replace(a,tcl(b))
        script=out/'export.tcl';script.write_text('read_db '+tcl(odb)+'\n'+body+'\n')
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        rec['native_readonly_returncode']=execute(common,script,out/'native.log',threads=1)
        rec['actual_parent_pg_local_rows']=sum(1 for line in (out/'actual_parent_PG_local.tsv').open())-1
        rec['actual_R0_transform']=(out/'actual_transform.tsv').read_text().strip()
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in rec['source_SHA'].items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or rec.get('native_readonly_returncode')!=0 or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
