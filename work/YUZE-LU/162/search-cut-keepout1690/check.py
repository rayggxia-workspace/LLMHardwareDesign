from pathlib import Path
import ast,subprocess,json,math
b=Path(r'D:\Data\电路实验');r=b/'LLMHardwareDesign-worktrees/issue-162-control';p=r/'project/experiments/control_v1/openroad_router_probe.py';old=subprocess.check_output(['git','show','HEAD:project/experiments/control_v1/openroad_router_probe.py'],cwd=r).decode();new=p.read_text(encoding='utf-8');ot,nt=ast.parse(old),ast.parse(new)
oldline=[n.value for n in ast.walk(ot)if isinstance(n,ast.Constant)and isinstance(n.value,str)and n.value.startswith(' odb::dbObstruction_create $block $cut_layer')];newline=[n for n in ast.walk(nt)if isinstance(n,ast.JoinedStr)and ast.unparse(n).find('odb::dbObstruction_create $block $cut_layer')!=-1];assert len(oldline)==len(newline)==1
assert eval(compile(ast.Expression(newline[0]),'<default cut Tcl>','eval'),{'cut_guard_dbu':1})==oldline[0]
for value in [False,True]:
 texts=[]
 for tree in [ot,nt]:
  f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='landing_markers');ns={};exec(compile(ast.Module(body=[f],type_ignores=[]),'<marker function>','exec'),ns);texts.append(ns['landing_markers'](value))
 assert texts[0]==texts[1]
tech=json.loads((r/'project/experiments/block_v1/technology-2um-v1.json').read_bytes())['geometry_um'];assert tech['cut_width']==2 and tech['cut_spacing']==2.2 and tech['pitch']==4
clearances=[]
for x,y in [(0,0),(4,4)]:
 distances=[]
 for a in range(-4,5):
  for c in range(-4,5):
   if(a+c)%2==0:continue
   dx=max(0,abs(x-4*a)-1-.5);dy=max(0,abs(y-4*c)-1-.5);distances.append(math.hypot(dx,dy))
 assert min(distances)==2.5 and min(distances)>tech['cut_spacing'];clearances.append(min(distances))
compile(new,str(p),'exec');out=b/'control162-local1690';assert not out.exists();out.mkdir();(out/'receipt.json').write_text(json.dumps(dict(passed=True,legacy_tcl_byteexact=True,legacy_and_parity_marker_lefs_byteexact=True,technology_unchanged=True,minimum_legal_via_clearance_um=clearances,original_cut_spacing_um=2.2,whole_system_qualified=False,scope='Local search-only keepout geometry proof. Paritymode global oddguard halfwidth.5um plus1um viahalfwidth leaves2.5um clearance at nearest legal4um gridcenter. All original legal checkerboard centers preserved, odd centers remain forbidden. Existing oddmaster1DBU OBS unchanged. Actual5fixture EDA preflight not yet executed; no fullroute/physical qualification.'),indent=2));print(json.dumps(dict(passed=True,legacy_byteexact=True,legal_center_clearance_um=2.5)))
