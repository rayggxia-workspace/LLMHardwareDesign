from pathlib import Path
import re,json,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=root/'audit/C-v35-upper-patch-v2';out.mkdir(exist_ok=True);src=root/'cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base'
transforms={'services.engine\\[0\\].element.e32.aperture_data\\[26\\]': [['NEW metal10 ( 4016190 1390800 ) ( * 1459200 )', 'NEW metal10 ( 4016190 1390800 ) ( * 1459360 )'], ['NEW metal10 ( 4009790 1459200 ) ( 4016190 * )', 'NEW metal10 ( 4009790 1459360 ) ( 4016190 * )'], ['NEW metal10 ( 4009790 1459200 ) ( * 1494540 )', 'NEW metal10 ( 4009790 1459360 ) ( * 1494540 )']], '_136204_': [['NEW metal10 ( 4227390 1318540 ) ( * 1353740 )', 'NEW metal10 ( 4227390 1318540 ) ( * 1356740 )'], ['NEW metal9 ( 4227390 1353740 ) ( 4233790 * )', 'NEW metal9 ( 4227390 1356740 ) ( 4233790 * )\n      NEW metal9 ( 4233790 1356740 ) ( * 1356940 )'], ['NEW metal10 ( 4233790 1353740 ) ( * 1356940 )', ''], ['NEW metal9 ( 4227390 1353740 ) via9_0', 'NEW metal9 ( 4227390 1356740 ) via9_0'], ['NEW metal9 ( 4233790 1353740 ) via9_0', ''], ['NEW metal9 ( 4233790 1356940 ) via9_0', '']]}

s=(src/'6_final.def').read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0];nets={x.split()[0]:x for x in re.split(r'(?m)^\s*-(?= )',s)[1:]};cmd=['set b [ord::get_db_block]','set tech [[ord::get_db] getTech]']
for name,replacements in transforms.items():
 body=nets[name].split('+ ROUTED',1)[1].split(';',1)[0]
 for old,new in replacements:
  assert body.count(old)==1,(name,old);body=body.replace(old,new)
 cmd+=['set target [$b findNet {'+name+'}]','if {$target eq "NULL"} {error "missing target net"}','odb::dbWire_destroy [$target getWire]','set w [odb::dbWire_create $target]','set e [odb::new_dbWireEncoder]','$e begin $w']
 for part in re.split(r'\bNEW\s+',body):
  layer,seq=part.strip().split(None,1);cmd+=['$e newPath [$tech findLayer '+layer+'] ROUTED'];prev=None
  for m in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,v=m.groups()
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));cmd+=['$e addPoint %d %d%s'%(pt[0],pt[1],(' '+ext) if ext is not None else '')];prev=pt
   else:cmd+=['set v [$b findVia {'+v+'}]','if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {'+v+'}]}']
 cmd+=['$e end','odb::delete_dbWireEncoder $e']
(out/'hook.tcl').write_text('\n'.join(cmd)+'\n');(out/'plan.json').write_text(json.dumps(dict(source=str(src),replacements=transforms,source_def_sha256=hashlib.sha256((src/'6_final.def').read_bytes()).hexdigest()),indent=2))
(out/'apply.tcl').write_text('set_thread_count 8\nread_db '+str(src/'6_final.odb')+'\nwrite_def '+str(out/'before.def')+'\nwrite_verilog '+str(out/'before.v')+'\nsource '+str(out/'hook.tcl')+'\nwrite_db '+str(out/'patched.odb')+'\nwrite_def '+str(out/'patched.def')+'\nwrite_verilog '+str(out/'patched.v')+'\n')
s=(root/'audit/C-m10-notch-v1/probe.sbatch').read_text().replace(str(root/'audit/C-m10-notch-v1'),str(out)).replace('probe-%j','apply-%j').replace('/probe.tcl','/apply.tcl');(out/'apply.sbatch').write_text(s)
