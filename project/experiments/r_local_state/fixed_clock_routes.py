"""Preserve measured clock geometry and all its cell endpoints during data ECOs."""
from pathlib import Path
import argparse,gzip,hashlib,json,re,shutil,subprocess
from native_interchange import lex
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def records(path,section,names):
 active=False;row=[];out={}
 with path.open()as stream:
  for line in stream:
   if not active:
    if re.match(r'^\s*'+section+r'\s+\d+\s*;',line):active=True
    continue
   if re.match(r'^\s*END\s+'+section+r'\s*$',line):assert not row;break
   for value in lex.findall(line):
    if value.startswith('#'):continue
    row.append(value)
    if value==';':
     assert row[0]=='-'
     if row[1]in names:
      assert row[1]not in out;out[row[1]]=row
     row=[]
 assert active and not row and set(out)==set(names),('Missing/duplicate selected DEF objects',section,sorted(set(names)-set(out))[:5])
 return out

def canonical_net(row,expected):
 at=2;connections=[]
 while row[at]=='(':
  end=row.index(')',at)+1;connections.append(tuple(row[at:end]));at=end
 assert row[at]in ['+',';']
 result=row[:2]+[v for c in sorted(connections)for v in c]+row[at:];flags=0
 for i in range(1,len(result)):
  if result[i]in ['ROUTED','FIXED','COVER','SHIELD']and result[i-1]=='+':
   assert result[i]==expected,('Clock wire type changed',row[1],result[i],expected);result[i]='ROUTED';flags+=1
 assert flags>0
 return result,connections

def canonical_cell(row,expect_fixed):
 result=list(row);count=0
 for i in range(1,len(result)):
  if result[i]in ['PLACED','FIXED','COVER','UNPLACED']and result[i-1]=='+':
   assert result[i]=='FIXED'if expect_fixed else result[i]in ['PLACED','FIXED']
   result[i]='PLACED';count+=1
 assert count==1,('Clock cell is unplaced or has ambiguous status',row[1])
 return result

def prepare(physical,source,proof):
 r=json.loads((proof/'receipt.json').read_text());assert r['passed']and r['source_odb']==str(source/'flow/results/nangate45/r166_1024/base/6_final.odb')and r['source_odb_sha256']==sha(Path(r['source_odb']))
 for name,row in r['artifacts'].items():assert sha(proof/name)==row['sha256']and(proof/name).stat().st_size==row['bytes']
 name_rows=[line.split('\t')[0]for line in(proof/'clock-nets.tsv').read_text().splitlines()]
 names=set(name_rows)
 # Each independently mapped source has its own measured clock tree.
 #392 has5041 nets;404 has5091. Require the complete unique native inventory
 # and its exact successful overlay proof, rather than another source's count.
 assert len(name_rows)==len(names)==r['clock_nets']==r['route_flag_changes']and len(names)>0
 nets=records(proof/'before.def','NETS',names);cells=set();normalized={}
 for name,row in nets.items():
  normalized[name],connections=canonical_net(row,'ROUTED')
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
 binding=dict(proof=str(proof),proof_receipt_sha256=sha(proof/'receipt.json'),source_odb=r['source_odb'],source_odb_sha256=r['source_odb_sha256'],baseline_sha256=sha(physical/'CLOCK_BASELINE.json.gz'),overlay_sha256=sha(physical/'CLOCK_FIXED.def'),native_names_sha256=sha(physical/'CLOCK_NATIVE_NAMES.tsv'),native_names_script_sha256=sha(inventory),clock_nets=len(names),clock_cells=len(cells),qualification_transferred=False,scope='Keep existing clock wires ROUTED through GRT, lock all clock cells and DFF endpoints, then mark exact wires FIXED before DRT. Audit geometry/connectivity/cell master and position before DRT, after DRT and in final DEF. Every original final gate remains mandatory.')
 (physical/'CLOCK_ROUTE_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
 module=Path(__file__).resolve()
 (physical/'fixed_clock_prepare.tcl').write_text('''set locked [dict create];set nc 0
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
  text='set here {'+str(physical)+'}\nwrite_def {'+str(physical/('CLOCK_'+phase+'.def'))+'}\n'
  text+='puts [exec python3 {'+str(module)+'} audit --physical {'+str(physical)+'} --def {'+str(physical/('CLOCK_'+phase+'.def'))+'} --phase '+phase+']\n'
  if phase=='before-detail':text+='read_def -floorplan_initialize {'+str(physical/'CLOCK_FIXED.def')+'}\n'
  (physical/('fixed_clock_'+phase+'.tcl')).write_text(text)
 return binding

def audit(physical,defile,phase):
 binding=json.loads((physical/'CLOCK_ROUTE_BINDING.json').read_text());assert binding['qualification_transferred']is False
 assert sha(physical/'CLOCK_BASELINE.json.gz')==binding['baseline_sha256']and sha(physical/'CLOCK_FIXED.def')==binding['overlay_sha256']
 assert sha(physical/'CLOCK_NATIVE_NAMES.tsv')==binding['native_names_sha256']and sha(physical/'clock_source_names.tcl')==binding['native_names_script_sha256']
 baseline=json.loads(gzip.decompress((physical/'CLOCK_BASELINE.json.gz').read_bytes()))
 locked_rows=(physical/'CLOCK_LOCKED_CELLS.tsv').read_text().splitlines();locked=set(locked_rows);assert len(locked_rows)==len(locked)and locked==set(baseline['native_cells'].values())
 nets=records(defile,'NETS',baseline['nets']);cells=records(defile,'COMPONENTS',baseline['cells'])
 for name,row in nets.items():assert canonical_net(row,'ROUTED'if phase=='before-detail'else'FIXED')[0]==baseline['nets'][name],('Clock routing/connectivity changed',phase,name)
 for name,row in cells.items():assert canonical_cell(row,True)==baseline['cells'][name],('Clock cell master/position/attributes changed',phase,name)
 result=dict(passed=True,phase=phase,def_path=str(defile),def_sha256=sha(defile),binding_sha256=sha(physical/'CLOCK_ROUTE_BINDING.json'),baseline_sha256=binding['baseline_sha256'],clock_nets=len(nets),clock_cells=len(cells),producer_sha256=sha(Path(__file__)),scope='All clock wire geometry, complete terminal records, cell masters/positions/orientations/attributes unchanged. Only explicit fixed-placement/route flags and unordered terminal order normalized; no final qualification transfer.')
 (physical/('CLOCK_AUDIT_'+phase+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['audit']);p.add_argument('--physical',type=Path,required=True);p.add_argument('--def',dest='defile',type=Path,required=True);p.add_argument('--phase',choices=['before-detail','after-detail','final'],required=True);a=p.parse_args();audit(a.physical,a.defile,a.phase)
