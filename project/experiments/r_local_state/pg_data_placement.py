"""Bind a measured PG-safe data-only placement ECO to its exact GRT source."""
from pathlib import Path
import hashlib,json
from fixed_clock_routes import records
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def measured_plan(source,probe):
 r=json.loads((probe/'receipt.json').read_text())
 assert r['passed']is True and r['native_exit']==0 and r['qualification']is False
 assert r['clock_audit']['passed']is True and r['clock_audit']['producer_sha256']==sha(Path(__file__).with_name('fixed_clock_routes.py'))
 for name,digest in r['inputs'].items():assert sha(Path(name))==digest
 for name,row in r['artifacts'].items():assert sha(probe/name)==row['sha256']and(probe/name).stat().st_size==row['bytes']
 failed=Path(r['physical']);resume=json.loads((failed/'GRT_RESUME.json').read_text())
 assert resume['source']==str(source)and resume['qualification_transferred']is False
 checkpoint=source/'flow/results/nangate45/r166_1024/base/5_1_grt.odb'
 assert resume['checkpoint_sha256']==sha(checkpoint)
 clock=set((source/'CLOCK_NATIVE_NAMES.tsv').read_text().splitlines());moves={}
 for line in(probe/'moves.tsv').read_text().splitlines():
  name,master,x,y,nx,ny,orient,pitch=line.split('\t')
  assert name not in moves and name not in clock and not master.startswith('FILLCELL')
  assert name in r['selected_cells']and r['selected_cells'][name]==dict(master=master,location=x+' '+y,orient=orient)
  assert not any(c in name for c in '{}\n\r')and int(pitch)>0
  moves[name]=dict(master=master,before=[int(x),int(y)],after=[int(nx),int(ny)],orient=orient)
 assert 0<len(moves)<=64 and set(moves)==set(r['selected_cells'])and all(v['before']!=v['after']for v in moves.values())
 inputs={str(f):sha(f)for f in [probe/'receipt.json',probe/'moves.tsv',failed/'GRT_RESUME.json',failed/'receipt.json',checkpoint]}
 inputs.update(r['inputs'])
 return dict(source=str(source),probe=str(probe),probe_receipt_sha256=sha(probe/'receipt.json'),inputs=inputs,moves=moves,qualification_transferred=False,post_eco_grt_timing_qualified=False,scope='Apply only exact measured data-buffer positions to the matching GRT checkpoint. Pre-ECO GRT timing is not post-ECO timing. Fresh DRT, final extracted timing/electrical/PG/DRC/function and all original clock audits remain mandatory.')

def prepare(physical,source,probe):
 plan=measured_plan(source,probe);text='set block [ord::get_db_block]\nset pg_before [dict create]\nforeach inst [$block getInsts] {dict set pg_before [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]}\n'
 for name,row in sorted(plan['moves'].items()):
  text+='set inst [$block findInst {'+name+'}]\n'
  text+='if {$inst eq "NULL" || [[$inst getMaster] getName] ne {'+row['master']+'} || [$inst getLocation] ne {'+' '.join(map(str,row['before']))+'} || [$inst getOrient] ne {'+row['orient']+'}} {error "Measured PG data buffer differs from GRT checkpoint"}\n'
  text+='$inst setPlacementStatus PLACED\n$inst setLocation '+' '.join(map(str,row['after']))+'\n$inst setPlacementStatus LOCKED\n'
 text+='''check_placement -verbose
foreach inst [$block getInsts] {
 set name [$inst getName];set now [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
 if {$now ne [dict get $pg_before $name] && [lsearch -exact {'''+ ' '.join(sorted(plan['moves']))+'''} $name]<0} {error "Unselected original cell changed during PG placement ECO"}
}
puts "R166_MEASURED_PG_DATA_PLACEMENT; moved='''+str(len(plan['moves']))+'''; other_cells_unchanged=1; post_eco_timing_qualified=0"
'''
 (physical/'pg_data_placement.tcl').write_text(text)
 plan['hook_sha256']=sha(physical/'pg_data_placement.tcl')
 (physical/'PG_DATA_PLACEMENT.json').write_text(json.dumps(plan,indent=2)+'\n')
 return plan

def verify_final(physical,defile):
 plan=json.loads((physical/'PG_DATA_PLACEMENT.json').read_text());expected=measured_plan(Path(plan['source']),Path(plan['probe']))
 assert {k:v for k,v in plan.items()if k!='hook_sha256'}==expected
 assert sha(physical/'pg_data_placement.tcl')==plan['hook_sha256']
 for name,row in records(defile,'COMPONENTS',plan['moves']).items():
  v=plan['moves'][name];assert row[2]==v['master'];i=row.index('FIXED');assert row[i+1:i+6]==['(',str(v['after'][0]),str(v['after'][1]),')',{'R0':'N','MX':'FS'}[v['orient']]]
 return plan
