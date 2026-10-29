"""Read real bit_1025 metal/via/PG/OBS context; never a repair or access pass."""
from pathlib import Path
import datetime,json,os,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'llsys_actual_via_tips/r02';rp=source/'execution.json'
    q=json.loads(rp.read_text());assert q.get('completed_utc') and q['fresh_DRC_count']==0
    assert q['all_closed_sources_unchanged'] and q['whole_signal_geometry']['pass']
    odb=source/'routed.odb';assert sha(odb)==q['files'][odb.name]['sha256']
    audit=ROOT/'parent_noap_grid_audit/r01/execution.json';a=json.loads(audit.read_text())
    assert a['all_closed_sources_unchanged'] and a['actual_complete_selected_net_row_counts']['bit_1025']==535
    out=ROOT/'llsys_noap_context'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,audit]}
    rec={'scope':'ACTUAL_NATIVE_NoAP_PIN_WIRE_VIA_FOREIGN_METAL_PG_OBS_DIAGNOSIS_NOT_REPAIR',
         'source_SHA':inputs,'source_native_DRC_count':0,'full_qualification':False,
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'target':'bit_1025','original_pin_layer':'metal5','original_pin_box_DBU':[707700,2128980,707980,2129260],
         'diagnostic_window_DBU':[702770,2123440,711980,2133400],
         'candidate_own_actual_via_cap_DBU':[706770,2129120,707050,2129400],
         'candidate_policy':'Geometric possibility only; no pin moved. Actual local metals/OBS/PG/via and parent AP must be checked.',
         'not_checked':['Repair or fresh DRC','Parent AP','PRL/EOL/enclosure and complete rules','RC/STA/electrical/function qualification']}
    try:
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        extra='''set b [ord::get_db_block];set bt [$b findBTerm bit_1025];set net [$bt getNet]
set f [open '''+tcl(out/'actual_target_via_definitions.tsv')+''' w]
puts $f "via\tkind\tx\ty\tlayer\tx0\ty0\tx1\ty1"
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
$itr begin [$net getWire]
while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
 set s [odb::dbWirePathShape_shape_get $ps];if {![$s isVia]} {continue}
 set kind TECH;set via [$s getTechVia];if {$via eq "NULL"} {set kind BLOCK;set via [$s getVia]}
 lassign [$s getViaXY] x y
 foreach box [$via getBoxes] {puts $f [join [list [$via getName] $kind $x $y [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]}
}};close $f
puts {ACTUAL_BIT_1025_VIA_DEFINITIONS_READ_ONLY}
'''
        script=out/'read_actual.tcl'
        script.write_text('set ::env(PINXY_AUDIT_ODB) '+tcl(odb)+'\nset ::env(PINXY_AUDIT_PIN) bit_1025\nset ::env(PINXY_AUDIT_BOX) '+tcl(' '.join(map(str,rec['diagnostic_window_DBU'])))+'\nset ::env(PINXY_AUDIT_OUT) '+tcl(out/'all_actual_local_metal_PG_OBS.tsv')+'\nsource '+tcl(DRIVER/'audit_parent_region.tcl')+'\n'+extra)
        rec['native_read_only_returncode']=execute(common,script,out/'native.log',threads=1)
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec.get('native_read_only_returncode')==0 and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
