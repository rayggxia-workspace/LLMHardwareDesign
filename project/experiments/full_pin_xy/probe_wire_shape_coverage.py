"""Read-only native dbWireShapeItr RECT-coverage probe; no leaf repair."""
from pathlib import Path
import datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent

def run(revision,profile='shape_iterator'):
    assert profile in ['shape_iterator','inventory','decoder_rect','decoder_payload','rect_native_shape','rect_native_coord']
    source=ROOT/'pin_metal_encoding_API/r02';rp=source/'execution.json';q=json.loads(rp.read_text())
    odb=source/'encoding_probe_NOT_LEAF.odb'
    assert q.get('completed_utc') and q['native_returncodes']['encode_and_export']==0 and sha(odb)==q['files'][odb.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,odb]};out=ROOT/'wire_shape_coverage_API'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'READ_ONLY_NATIVE_RECT_OPCODE_EXPORTER_COVERAGE_NOT_LEAF_OR_DRC_QUALIFICATION','profile':profile,'source_SHA':inputs,'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        body=r'''puts "NATIVE_SHAPE_API [info commands ::odb::*WireShapeItr*]"
set b [ord::get_db_block];set it [odb::dbWireShapeItr];set shape [odb::dbShape]
set f [open OUTPUT w];puts $f "net\tlayer\tx0\ty0\tx1\ty1\tvia"
foreach name {HPY_PATCH_POINT_PAIR HPY_PATCH_RECT_OPCODE} {
 set n [$b findNet $name];$it begin [$n getWire]
 while {[$it next $shape]} {
  set l [$shape getTechLayer]
  puts $f [join [list $name [$l getName] [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax] [$shape isVia]] "\t"]
 }
};close $f
'''
        if profile=='inventory':
            body='puts "ACTUAL_WIRE_BINDING_INVENTORY [lsort [info commands ::odb::*Wire*]]"\n'
        if profile=='decoder_rect':
            # This closed probe net was built with exactly PATH, POINT, RECT;
            # inspect those three known encoder operations, never arbitrary
            # enum numbers or speculative getRect calls on real leaf wires.
            body=r'''set b [ord::get_db_block];set n [$b findNet HPY_PATCH_RECT_OPCODE]
if {$n eq "NULL"} {error "Closed known RECT probe net missing"}
puts "ACTUAL_DECODER_ENUM_VARS [lsort [info vars ::odb::*WireDecoder*]]"
foreach name [lsort [info vars ::odb::*WireDecoder*]] {puts "ENUM_VALUE $name [set $name]"}
set d [odb::dbWireDecoder];$d begin [$n getWire]
set f [open OUTPUT w];puts $f "stage\tstatus\tvalue"
for {set i 0} {$i<3} {incr i} {
 set op [$d next];puts $f [join [list opcode_$i 0 $op] "\t"]
 if {$i==1} {set status [catch {$d getPoint} value];puts $f [join [list native_point $status $value] "\t"]}
 if {$i==2} {
  set status [catch {$d getRect} value];puts $f [join [list native_rect $status $value] "\t"]
  set status [catch {$d getLayer} value];if {!$status} {set value [$value getName]}
  puts $f [join [list native_layer $status $value] "\t"]
 }
};close $f
'''
        if profile=='decoder_payload':
            body=r'''set b [ord::get_db_block];set n [$b findNet HPY_PATCH_RECT_OPCODE]
if {$n eq "NULL"} {error "Known native RECT probe missing"}
set w [$n getWire];set f [open OUTPUT w];puts $f "stage\tstatus\tvalue"
puts "NATIVE_INT_REFERENCE_HELPERS [lsort [concat [info commands ::odb::*intp*] [info commands ::odb::*intArray*]]]"
set status [catch {$w length} count];puts $f [join [list wire_length_API $status $count] "\t"]
if {!$status && [string is integer -strict $count] && $count>0 && $count<=64} {
 for {set i 0} {$i<$count} {incr i} {
  foreach method {getOpcode getData} {
   set status [catch {$w $method $i} value]
   puts $f [join [list ${method}_$i $status $value] "\t"]
  }
 }
};close $f
'''
        if profile=='rect_native_shape':
            # r04 verified the exact closed wire length and RECT opcode/index.
            # getShape sees a real constructed dbShape, never a null pointer.
            body=r'''set b [ord::get_db_block];set n [$b findNet HPY_PATCH_RECT_OPCODE];set w [$n getWire]
if {[$w length]!=7 || [$w getOpcode 3]!=14} {error "Known closed native RECT payload differs"}
set s [odb::dbShape];set f [open OUTPUT w];puts $f "stage\tstatus\tvalue"
set status [catch {set s [$w getShape 3]} value];puts $f [join [list native_getShape $status $value] "\t"]
if {!$status} {
 set layer [$s getTechLayer]
 puts $f [join [list actual_shape 0 [list [$layer getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax] [$s isVia]]] "\t"]
};close $f
'''
        if profile=='rect_native_coord':
            body=r'''set b [ord::get_db_block];set n [$b findNet HPY_PATCH_RECT_OPCODE];set w [$n getWire]
if {[$w length]!=7 || [$w getOpcode 3]!=14} {error "Known source differs"}
set f [open OUTPUT w];puts $f "stage\tstatus\tvalue"
foreach i {2 3} {
 set status [catch {$w getCoord $i} value];puts $f [join [list native_getCoord_$i $status $value] "\t"]
}
set d [odb::dbWireDecoder];$d begin $w
for {set i 0} {$i<3} {incr i} {set op [$d next]}
set l [$d getLayer];puts $f [join [list native_RECT_layer 0 [$l getName]] "\t"]
close $f
'''
        script=out/'probe.tcl';script.write_text('read_db '+tcl(odb)+'\n'+body.replace('OUTPUT',tcl(out/'native_all_shapes.tsv')))
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        rec['native_returncode']=execute(common,script,out/'native.log',threads=1)
        if rec['native_returncode']==0 and profile in ['shape_iterator','decoder_rect','decoder_payload','rect_native_shape','rect_native_coord']:rec['actual_shape_export_text']=(out/'native_all_shapes.tsv').read_text()
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('native_returncode')==0 and rec['all_closed_sources_unchanged'] else 1
if __name__=='__main__':sys.exit(run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'shape_iterator'))
