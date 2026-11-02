"""Candidate fixed native M7-M10 PG access wrapper; never edits a frozen source."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--leaf',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    row=json.loads(a.manifest.read_text())['leaves'][a.leaf]
    original=Path(row['final_files']['6_final.odb']['path']);digest=sha(original);assert digest==row['final_files']['6_final.odb']['sha256']
    r=dict(passed=False,job=os.environ['SLURM_JOB_ID'],leaf=a.leaf,inputs={str(a.manifest):sha(a.manifest),str(original):digest,str(Path(__file__)):sha(Path(__file__))},
           native_leaf_qualified=False,whole_system_qualified=False,
           scope='Candidate permanent native PG wrapper. Original accepted files preserved. Fresh RC/STA, GDS full deck, exact connectivity and actual upper PG remain mandatory.')
    try:
        script='set_thread_count 16\nread_db {'+str(original)+'}\nset b [ord::get_db_block]\nset tech [[ord::get_db] getTech]\n'
        script+='write_def {'+str(a.out/'original.def')+'}\nwrite_verilog {'+str(a.out/'original.v')+'}\n'
        script+='set f [open {'+str(a.out/'fixed-access.tsv')+'} w]\n'
        native=Path(__file__).resolve().parents[1]/'block_v1'
        sys.path.insert(0,str(native))
        script+='source {'+str(native/'odb_geometry.tcl')+'}\nset added_wires {}\n'
        script+=r'''
set die [$b getDieArea]
if {[$b getDbUnitsPerMicron]!=2000 || [$die xMin]!=0 || [$die yMin]!=0} {error "Unexpected native coordinates"}
foreach {supply px} {VDD 16190 VSS 32190} {
 set n [$b findNet $supply]
 if {$n eq "NULL"} {error "Missing native supply"}
 set rails {}
 foreach sw [$n getSWires] {foreach box [$sw getWires] {
  if {![$box isVia] && [[$box getTechLayer] getName] eq "metal7" && [$box xMax]-[$box xMin]>20000 && [$box yMax]-[$box yMin]==2800} {
   lappend rails [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
  }
 }}
 if {![llength $rails]} {error "No supported original M7 supply rails"}
 set wire [odb::dbSWire_create $n ROUTED]
 lappend added_wires [list $supply $wire]
 set metal10 [$tech findLayer metal10]
 set bottom 16140;set top [expr {[$die yMax]-16140}]
 odb::dbSBox_create $wire $metal10 [expr {$px-2000}] $bottom [expr {$px+2000}] $top STRIPE
 puts $f "STRAP\t$supply\tmetal10\t[expr {$px-2000}]\t$bottom\t[expr {$px+2000}]\t$top"
 foreach rail $rails {
  lassign $rail x0 y0 x1 y1
  set x [expr {$x0+800}];set y [expr {($y0+$y1)/2}]
  if {$px+2400 >= $x || $y-800<$bottom || $y+800>$top} {error "Fixed bridge outside reserved periphery"}
  odb::dbSBox_create $wire [$tech findLayer metal8] [expr {$px-400}] [expr {$y-400}] [expr {$x+400}] [expr {$y+400}] STRIPE
  foreach {v vx} [list via7_0 $x via8_0 $px via9_0 $px] {
   set via [$tech findVia $v];if {$via eq "NULL"} {error "Missing native via $v"}
   odb::dbSBox_create $wire $via $vx $y STRIPE
   puts $f "VIA\t$supply\t$v\t$vx\t$y"
  }
  puts $f "BRIDGE\t$supply\tmetal8\t[expr {$px-400}]\t[expr {$y-400}]\t[expr {$x+400}]\t[expr {$y+400}]"
 }
 # One declared M10 interface BPin, separate from immutable native PG ports.
 set port [$b findBTerm $supply]
 if {$port eq "NULL" || [$port getNet] ne $n || [$port getSigType] ne [$n getSigType]} {error "Missing original typed supply port"}
 set pin [odb::dbBPin_create $port];$pin setPlacementStatus FIRM
 odb::dbBox_create $pin $metal10 [expr {$px-2000}] 16140 [expr {$px+2000}] 20140
}
close $f
'''
        script+='set s [open {'+str(a.out/'actual-added-geometry.tsv')+'} w]\nforeach pair $added_wires {lassign $pair net wire;foreach box [$wire getWires] {bvgeom::db_box $s $net $box fixed-pg}}\nclose $s\n'
        script+='write_def {'+str(a.out/'wrapper.def')+'}\nwrite_db {'+str(a.out/'wrapper.odb')+'}\nwrite_verilog {'+str(a.out/'wrapper.v')+'}\n'
        script+='drt::check_drc_cmd {'+str(a.out/'native-whole-drc.rpt')+'} 0 0 0 0 fixed_pg_access\n'
        (a.out/'fixed-access.tcl').write_text(script)
        with (a.out/'openroad.log').open('w') as log:q=subprocess.run(['openroad','-no_init','-exit',a.out/'fixed-access.tcl'],stdout=log,stderr=subprocess.STDOUT,cwd=a.out)
        assert q.returncode==0,'Actual fixed access construction/check failed'
        assert sha(original)==digest,'Original accepted database changed'
        assert sha(a.out/'original.v')==sha(a.out/'wrapper.v'),'Signal logic/ports changed'
        from native_escape_audit import def_inventory
        before,_=def_inventory(a.out/'original.def');after,_=def_inventory(a.out/'wrapper.def')
        assert before==after,'Existing regular net wiring changed'
        r['native_drc']=(a.out/'native-whole-drc.rpt').read_text()
        r['native_drc_zero']=not r['native_drc'].strip()
        assert r['native_drc_zero'],'Native complete DRC failed'
        gds=row['final_files']['6_final.gds'];assert sha(gds['path'])==gds['sha256']
        manifest=dict(native=gds['path'],native_sha256=gds['sha256'],geometry=str(a.out/'actual-added-geometry.tsv'),out=str(a.out))
        (a.out/'gds-input.json').write_text(json.dumps(manifest,indent=2)+'\n')
        template=Path(__file__).with_name('pg_fixed_gds.py');r['inputs'][str(template)]=sha(template)
        (a.out/'join.py').write_text(template.read_text().replace('PG_ACCESS_MANIFEST_PLACEHOLDER',str(a.out/'gds-input.json')))
        with (a.out/'gds.log').open('w') as log:q=subprocess.run(['klayout','-b','-r',a.out/'join.py'],stdout=log,stderr=subprocess.STDOUT,cwd=a.out)
        assert q.returncode==0 and json.loads((a.out/'gds-readback.json').read_text())['passed']
        deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc');r['inputs'][str(deck)]=sha(deck)
        with (a.out/'full-deck.log').open('w') as log:q=subprocess.run(['klayout','-b','-rd','in_gds='+str(a.out/'wrapper.gds'),'-rd','report_file='+str(a.out/'full-deck.lyrdb'),'-r',deck],stdout=log,stderr=subprocess.STDOUT,cwd=a.out)
        assert q.returncode==0
        from native_drc import summarize
        r['full_deck']=summarize(a.out/'full-deck.lyrdb');assert r['full_deck']['total_items']==0
        r['construction_completed']=True;r['passed']=True
    finally:
        r['outputs']={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    assert r['passed'],'Candidate fixed access violates complete native DRC'

if __name__=='__main__':main()
