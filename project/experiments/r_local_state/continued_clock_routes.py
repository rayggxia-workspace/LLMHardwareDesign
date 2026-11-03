"""Continue an already-FIXED clock source using unchanged strict audit routines.

Preparation mirrors the existing native name/cell/geometry binding. The only
additional operation is the independently proven temporary ROUTED flag overlay
for GRT. fixed_clock_routes.py and every audit/acceptance rule remain unchanged.
"""
from pathlib import Path
import json,gzip,shutil,subprocess
from fixed_clock_routes import sha,records,canonical_net,canonical_cell

def prepare(physical,source,proof):
 r=json.loads((proof/'receipt.json').read_text());assert r['passed']and r['source_odb']==str(source/'flow/results/nangate45/r166_1024/base/6_final.odb')and r['source_odb_sha256']==sha(Path(r['source_odb']))
 for name,row in r['artifacts'].items():assert sha(proof/name)==row['sha256']and(proof/name).stat().st_size==row['bytes']
 name_rows=[line.split('\t')[0]for line in(proof/'clock-nets.tsv').read_text().splitlines()]
 names=set(name_rows)
 # Each independently mapped source has its own measured clock tree.
 #392 has5041 nets;404 has5091. Require the complete unique native inventory
 # and its exact successful overlay proof, rather than another source's count.
 assert len(name_rows)==len(names)==r['clock_nets']==r['already_fixed_routes']and r['route_flag_changes']==0 and len(names)>0
 assert r['routed_overlay_tokens_verified']==r['tokens_verified']
 nets=records(proof/'before.def','NETS',names);cells=set();normalized={}
 for name,row in nets.items():
  normalized[name],connections=canonical_net(row,'FIXED')
  for c in connections:
   assert len(c)==4
   if c[1]!='PIN':cells.add(c[1])
 # Native names and their DEF-escaped spellings must form a proven bijection.
 #445 rejected literal backslashes in the real state-register names.
 inventory=physical/'clock_source_names.tcl'
 inventory.write_text('set_thread_count 16\nread_db {'+r['source_odb']+'}\n'+'''set cells [dict create]
foreach net [[ord::get_db_block] getNets] {
 if {[$net getSigType] eq "CLOCK"} {foreach term [$net getITerms] {set inst [$term getInst];dict set cells [$inst getName] 1}}
}
set f [open {'''+str(physical/'CLOCK_NATIVE_NAMES.tsv')+'''} w]
foreach name [lsort [dict keys $cells]] {puts $f $name}
close $f
set found [dict create]
foreach cell [get_cells -hierarchical *] {
 set inst [sta::sta_to_db_inst $cell]
 if {$inst ne "NULL"} {set name [$inst getName];if {[dict exists $cells $name]} {dict set found $name 1}}
}
if {[dict size $found]!=[dict size $cells]} {error "Source ODB/STA clock instance names differ"}
puts "R166_SOURCE_CLOCK_NAMES; native=[dict size $cells]; STA=[dict size $found]; exact_names=1"
''')
 with(physical/'clock_source_names.log').open('w')as log:subprocess.run(['openroad','-no_init','-exit',str(inventory)],stdout=log,stderr=subprocess.STDOUT,check=True)
 native_rows=(physical/'CLOCK_NATIVE_NAMES.tsv').read_text().splitlines();native=set(native_rows);assert len(native_rows)==len(native)
 #456 measured all97499 names equal literally in DEF and ODB. The4096
 #selection-FF names retain their backslashes in both; do not unescape them.
 mapping={name:name for name in cells}
 assert len(set(mapping.values()))==len(cells)and set(mapping.values())==native,'DEF/native clock instance names are not bijective'
 assert all(not any(c in name for c in ['\t','\n','\r'])for name in native)and sha(Path(r['source_odb']))==r['source_odb_sha256']
 components=records(proof/'before.def','COMPONENTS',cells)
 baseline=dict(nets=normalized,cells={name:canonical_cell(row,False)for name,row in components.items()},native_cells=mapping)
 (physical/'CLOCK_BASELINE.json.gz').write_bytes(gzip.compress(json.dumps(baseline).encode(),mtime=0))
 shutil.copyfile(proof/'fixed-clocks.def',physical/'CLOCK_FIXED.def')
 binding=dict(proof=str(proof),proof_receipt_sha256=sha(proof/'receipt.json'),source_odb=r['source_odb'],source_odb_sha256=r['source_odb_sha256'],baseline_sha256=sha(physical/'CLOCK_BASELINE.json.gz'),overlay_sha256=sha(physical/'CLOCK_FIXED.def'),native_names_sha256=sha(physical/'CLOCK_NATIVE_NAMES.tsv'),native_names_script_sha256=sha(inventory),clock_nets=len(names),clock_cells=len(cells),restoration_protocol='exact-source-clock-restore-v1',qualification_transferred=False,scope='Lock clock cells and DFF endpoints. GRT may clear regular wires: require unchanged complete clock connectivity/attributes and cell masters/positions, reject any surviving changed clock geometry, restore exact source wires FIXED, then audit complete geometry before DRT, after DRT and final. Every original final gate remains mandatory.')
 (physical/'CLOCK_ROUTE_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
 module=Path(__file__).with_name('fixed_clock_routes.py').resolve()
 shutil.copyfile(proof/'routed-clocks.def',physical/'CLOCK_ROUTED.def')
 (physical/'fixed_clock_prepare.tcl').write_text('read_def -floorplan_initialize {'+str(physical/'CLOCK_ROUTED.def')+'}\n'+'''set locked [dict create];set nc 0
foreach net [$block getNets] {
 if {[$net getSigType] ne "CLOCK"} {continue}
 if {[$net getWire] eq "NULL"} {error "Existing clock route missing"}
 incr nc
 foreach term [$net getITerms] {set inst [$term getInst];dict set locked [$inst getName] $inst}
}
if {$nc!='''+str(len(names))+''' || [dict size $locked]!='''+str(len(cells))+'''} {error "Clock network membership changed"}
set f [open $here/CLOCK_LOCKED_CELLS.tsv w]
dict for {name inst} $locked {$inst setPlacementStatus LOCKED;puts $f $name}
close $f
set protected {}
foreach cell [get_cells -hierarchical *] {
 set inst [sta::sta_to_db_inst $cell]
 if {$inst ne "NULL" && [dict exists $locked [$inst getName]]} {lappend protected $cell}
}
if {[llength $protected]!=[dict size $locked]} {error "Native clock cells do not match STA names"}
#478 RSZ-3017 showed whole-cell dont_touch also prohibits valid D-pin ECOs.
# Keep positions LOCKED and clock nets protected; the three complete audits
# still require exact cell masters/positions and clock wires, failing closed
# if a data optimizer changes any clock cell rather than buffering its data.
set_dont_touch [get_nets [list '''+' '.join('{'+n+'}'for n in sorted(names))+''']]
puts "R166_EXISTING_CLOCK_GEOMETRY; nets=$nc; locked_cells=[dict size $locked]; data_ECO_only=1"
''')
 for phase in ['before-detail','after-detail']:
  text='set here {'+str(physical)+'}\n'
  if phase=='before-detail':
   text+='write_def {'+str(physical/'CLOCK_pre-restore.def')+'}\n'
   text+='puts [exec python3 {'+str(module)+'} precheck --physical {'+str(physical)+'} --def {'+str(physical/'CLOCK_pre-restore.def')+'}]\n'
   text+='read_def -floorplan_initialize {'+str(physical/'CLOCK_FIXED.def')+'}\n'
  text+='write_def {'+str(physical/('CLOCK_'+phase+'.def'))+'}\n'
  text+='puts [exec python3 {'+str(module)+'} audit --physical {'+str(physical)+'} --def {'+str(physical/('CLOCK_'+phase+'.def'))+'} --phase '+phase+']\n'
  if phase=='before-detail':
   text+='''filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
check_placement -verbose
write_db {'''+str(physical/'CLOCK_POST_RESTORE.odb')+'''}
set f [open {'''+str(physical/'PG_PRE_ROUTE.tsv')+'''} w];set pg_failed 0
foreach supply {VDD VSS} {
 set code [catch {check_power_grid -net $supply -error_file $here/${supply}-pre-route.rpt} value]
 set valid [expr {$code==0 && [string is boolean -strict $value] && $value}]
 puts $f "$supply\\t$code\\t$valid";puts "R166_PRE_ROUTE_PG; supply=$supply; code=$code; valid=$valid"
 if {!$valid} {set pg_failed 1}
}
close $f
if {$pg_failed} {error "Original both-supply PG component failed before DRT; immutable checkpoint retained"}
remove_fillers
'''
  (physical/('fixed_clock_'+phase+'.tcl')).write_text(text)
 inputs={str(proof/name):row['sha256']for name,row in r['artifacts'].items()}
 inputs.update({str(proof/'receipt.json'):sha(proof/'receipt.json'),str(source/'CLOCK_ROUTE_BINDING.json'):sha(source/'CLOCK_ROUTE_BINDING.json'),str(source/'CLOCK_AUDIT_final.json'):sha(source/'CLOCK_AUDIT_final.json')})
 previous=json.loads((source/'CLOCK_AUDIT_final.json').read_text());assert previous['passed']and previous['producer_sha256']==sha(module)and previous['def_sha256']==sha(source/'flow/results/nangate45/r166_1024/base/6_final.def')
 (physical/'CONTINUED_CLOCK_PREPARE.json').write_text(json.dumps(dict(inputs=inputs,source=str(source),proof=str(proof),routed_overlay_sha256=sha(physical/'CLOCK_ROUTED.def'),fixed_overlay_sha256=sha(physical/'CLOCK_FIXED.def'),audit_producer_sha256=sha(module),qualification_transferred=False,scope='Source already has FIXED clocks. Independent full native overlays prove both flag states preserve all source geometry, connectivity and cells. Use ROUTED flags only during GRT; restore original exact FIXED clocks before DRT and pass unchanged complete pre/after/final audits.'),indent=2)+'\n')
 return binding
