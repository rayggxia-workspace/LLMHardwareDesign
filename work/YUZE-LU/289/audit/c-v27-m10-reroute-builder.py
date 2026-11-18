from pathlib import Path
import re,json,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=root/'audit/C-v27-m10/reroute-v2';out.mkdir(exist_ok=True);src=root/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base'
transforms={r'dma_s_rsp_data\[71\]':[
 ['NEW metal10 ( 2313790 512140 0 ) ( * 513000 )','NEW metal10 ( 2313790 512140 0 ) ( * 514600 )'],
 ['NEW metal10 ( 2307390 512140 ) ( * 513000 )','NEW metal10 ( 2307390 512140 ) ( * 514600 )'],
 ['NEW metal10 ( 2307390 513000 ) ( 2313790 * )','NEW metal10 ( 2307390 514600 ) ( 2313790 * )']],
 r'services.engine\[2\].a\[114\]':[
 ['NEW metal10 ( 369790 2096140 0 ) ( 370500 * )','NEW metal10 ( 369790 2094800 0 ) ( 371390 * )'],
 ['NEW metal10 ( 371390 2089740 ) ( * 2092940 )','NEW metal10 ( 371390 2089740 ) ( * 2094800 )'],
 ['NEW metal10 ( 370500 2092940 ) ( 371390 * )',''],
 ['NEW metal10 ( 370500 2092940 ) ( * 2096140 )','']]}

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
