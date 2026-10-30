"""Check actual opcode-preserving wire append; API probe, not a routed system."""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,re,sys
from run_exports import ROOT,IMAGE,BIN,sha
from run_escape_fixture import execute
from run_parent_trial import tcl

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'upper_adaptation_trial/r02/opentpu/placed_adapter_NOT_SYSTEM.odb'
    prior=json.loads((source.parent/'execution.json').read_text());assert sha(source)==prior['files'][source.name]['sha256']
    out=ROOT/'native_wire_append_api'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'TINY_NATIVE_API_PROBE_ONLY_NOT_PIN_ROUTING_OR_FUNCTIONAL_SYSTEM',
      'source_SHA':{str(source):sha(source)},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False}
    script=out/'probe.tcl'
    script.write_text('''read_db SOURCE
set b [ord::get_db_block];set tech [ord::get_db_tech]
puts "ACTUAL_APPEND_COMMANDS [info commands ::odb::*Wire*append*]"
foreach name {HPY_APPEND_A HPY_APPEND_B HPY_APPEND_C} {if {[$b findNet $name] ne "NULL"} {error "Probe name collision"}}
set na [odb::dbNet_create $b HPY_APPEND_A];set nb [odb::dbNet_create $b HPY_APPEND_B];set nc [odb::dbNet_create $b HPY_APPEND_C]
set a [odb::dbWire_create $na];set e [odb::dbWireEncoder];$e begin $a;$e newPath [$tech findLayer metal10] FIXED;$e addPoint 200000 200000;$e addPoint 200000 264000;$e end
set bb [odb::dbWire_create $nb];$e begin $bb;$e newPath [$tech findLayer metal10] ROUTED;$e addPoint 200000 200000;$e addTechVia [$tech findVia via10_0];$e addPoint 206400 200000;$e end
set c [odb::dbWire_create $nc]
$c append $a
$c append $bb
write_def DEFFILE
set f [open SHAPES w];puts $f "net\\tkind\\tlayer\\tx0\\ty0\\tx1\\ty1"
foreach n [list $na $nb $nc] {
 set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape];$itr begin [$n getWire]
 while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
  set s [odb::dbWirePathShape_shape_get $ps]
  if {[$s isVia]} {
   set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getVia]};lassign [$s getViaXY] x y
   foreach box [$v getBoxes] {puts $f [join [list [$n getName] VIA [[$box getTechLayer] getName] [expr {[$box xMin]+$x}] [expr {[$box yMin]+$y}] [expr {[$box xMax]+$x}] [expr {[$box yMax]+$y}]] "\\t"]}
  } else {puts $f [join [list [$n getName] WIRE [[$s getTechLayer] getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax]] "\\t"]}
 }}
};close $f
puts "ACTUAL_OPCODE_APPEND_EXECUTED_REQUIRES_COUNTER_AND_FIXED_STATUS_CHECK"
'''.replace('SOURCE',tcl(source)).replace('DEFFILE',tcl(out/'native_append.def')).replace('SHAPES',tcl(out/'actual_shapes.tsv')))
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec['native_returncode']=execute(common,script,out/'native.log',threads=1)
    if rec['native_returncode']==0:
        counters={n:Counter() for n in ['HPY_APPEND_A','HPY_APPEND_B','HPY_APPEND_C']}
        with (out/'actual_shapes.tsv').open() as f:
            for r in csv.DictReader(f,delimiter='\t'):counters[r['net']][tuple(r[k] for k in ['kind','layer','x0','y0','x1','y1'])]+=1
        assert counters['HPY_APPEND_A']+counters['HPY_APPEND_B']==counters['HPY_APPEND_C']
        text=(out/'native_append.def').read_text();m=re.search(r'^\s*- HPY_APPEND_C\s+(.*?);',text,re.M|re.S);assert m
        assert re.search(r'\+\s+FIXED\s+metal10\b',m.group(1)) and re.search(r'\+\s+ROUTED\s+',m.group(1))
        rec['actual_rectangle_multisets_and_native_FIXED_ROUTED_path_flags_preserved']=True
    rec['source_unchanged']=sha(source)==rec['source_SHA'][str(source)]
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('actual_rectangle_multisets_and_native_FIXED_ROUTED_path_flags_preserved') and rec['source_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
