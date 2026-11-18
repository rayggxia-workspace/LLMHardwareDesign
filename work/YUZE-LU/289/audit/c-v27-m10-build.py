from pathlib import Path
import re,json,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=root/'audit/C-v27-m10/patch-v1';out.mkdir(exist_ok=True);src=root/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base'
adds={r'dma_s_rsp_data\[71\]':['NEW metal10 ( 2310590 511340 ) ( * 513000 )'],r'services.engine\[2\].a\[114\]':['NEW metal10 ( 368190 2092940 ) ( 370500 * )','NEW metal10 ( 368190 2093200 ) ( 370500 * )']}
s=(src/'6_final.def').read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0];nets={x.split()[0]:x for x in re.split(r'(?m)^\s*-(?= )',s)[1:]};cmd=['set b [ord::get_db_block]','set tech [[ord::get_db] getTech]']
for name,new in adds.items():
 body=nets[name].split('+ ROUTED',1)[1].split(';',1)[0]+'\n'+'\n'.join(new)
 cmd+=['set target [$b findNet {'+name+'}]','if {$target eq "NULL"} {error "missing target net"}','odb::dbWire_destroy [$target getWire]','set w [odb::dbWire_create $target]','set e [odb::new_dbWireEncoder]','$e begin $w']
 for part in re.split(r'\bNEW\s+',body):
  layer,seq=part.strip().split(None,1);cmd+=['$e newPath [$tech findLayer '+layer+'] ROUTED'];prev=None
  for m in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,v=m.groups()
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));cmd+=['$e addPoint %d %d%s'%(pt[0],pt[1],(' '+ext) if ext is not None else '')];prev=pt
   else:cmd+=['set v [$b findVia {'+v+'}]','if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {'+v+'}]}']
 cmd+=['$e end','odb::delete_dbWireEncoder $e']
(out/'hook.tcl').write_text('\n'.join(cmd)+'\n');(out/'plan.json').write_text(json.dumps(dict(source=str(src),additions=adds,source_def_sha256=hashlib.sha256((src/'6_final.def').read_bytes()).hexdigest()),indent=2))
(out/'apply.tcl').write_text('set_thread_count 8\nread_db '+str(src/'6_final.odb')+'\nwrite_def '+str(out/'before.def')+'\nwrite_verilog '+str(out/'before.v')+'\nsource '+str(out/'hook.tcl')+'\nwrite_db '+str(out/'patched.odb')+'\nwrite_def '+str(out/'patched.def')+'\nwrite_verilog '+str(out/'patched.v')+'\n')
s=(root/'audit/C-m10-notch-v1/probe.sbatch').read_text().replace(str(root/'audit/C-m10-notch-v1'),str(out)).replace('probe-%j','apply-%j').replace('/probe.tcl','/apply.tcl');(out/'apply.sbatch').write_text(s)
