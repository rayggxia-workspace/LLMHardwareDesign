from pathlib import Path
import re,json,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=root/'audit/C-v28-upper-patch-v2';out.mkdir(exist_ok=True);src=root/'cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base'
transforms={'net118438': [['NEW metal9 ( 3771390 979340 ) ( 3779100 * )', 'NEW metal9 ( 3771390 979340 ) ( 3779390 * )'], ['NEW metal9 ( 3779100 979340 ) ( * 982540 )', 'NEW metal9 ( 3779390 979340 ) ( * 982540 )'], ['NEW metal9 ( 3779100 982540 ) ( 3830590 * )', 'NEW metal9 ( 3779390 982540 ) ( 3830590 * )']], 'net73253': [['NEW metal9 ( 2784190 1350540 ) ( 2787300 * )', 'NEW metal9 ( 2784190 1350540 ) ( 2787390 * )'], ['NEW metal9 ( 2787300 1350540 ) ( * 1353740 )', 'NEW metal9 ( 2787390 1350540 ) ( * 1353740 )'], ['NEW metal9 ( 2787300 1353740 ) ( 2801790 * )', 'NEW metal9 ( 2787390 1353740 ) ( 2801790 * )']], 'services.engine\\[0\\].element.e32.aperture_data\\[68\\]': [['NEW metal9 ( 4051390 1660940 ) ( 4052700 * )', 'NEW metal9 ( 4051390 1660940 ) ( 4052990 * )'], ['NEW metal9 ( 4048190 1667340 ) ( 4052700 * )', 'NEW metal9 ( 4048190 1667340 ) ( 4052990 * )'], ['NEW metal9 ( 4052700 1660940 ) ( * 1667340 )', 'NEW metal9 ( 4052990 1660940 ) ( * 1667340 )']], 'services.engine\\[0\\].element.arithmetic.out_data\\[62\\]': [['NEW metal10 ( 2748990 1820940 ) ( * 1824140 )', 'NEW metal10 ( 2748990 1820940 ) ( * 1824340 )'], ['NEW metal9 ( 2748990 1824140 ) via9_0', 'NEW metal9 ( 2748990 1824340 ) via9_0\n      NEW metal9 ( 2748990 1824140 ) ( * 1824340 )']]}

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
