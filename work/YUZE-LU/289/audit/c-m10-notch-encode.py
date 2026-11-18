from pathlib import Path
import re
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1');s=(p/'patch.def').read_text();body=s.split('+ ROUTED',1)[1].split(';',1)[0]
cmd=['set tech [[ord::get_db] getTech]','set b [ord::get_db_block]','set count 0',r'foreach n [$b getNets] {if {[$n getName] eq {dma_s_rsp_data\[52\]}} {set target $n;incr count}}','if {$count != 1} {error "nonunique target"}','odb::dbWire_destroy [$target getWire]','set w [odb::dbWire_create $target]','set e [odb::new_dbWireEncoder]','$e begin $w']
for part in re.split(r'\bNEW\s+',body):
 layer,seq=part.strip().split(None,1);cmd.append('$e newPath [$tech findLayer '+layer+'] ROUTED');prev=None
 for m in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
  x,y,ext,v=m.groups()
  if x is not None:
   pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));cmd.append('$e addPoint %d %d%s'%(pt[0],pt[1],(' '+ext) if ext is not None else ''));prev=pt
  else:
   cmd.append('set v [$b findVia {'+v+'}]');cmd.append('if {$v ne "NULL"} {$e addVia $v} else {$e addTechVia [$tech findVia {'+v+'}]}')
cmd+=['$e end','odb::delete_dbWireEncoder $e']
(p/'hook.tcl').write_text('\n'.join(cmd)+'\n')
s=(p/'patch.tcl').read_text();s=s[:s.index('set b [ord::get_db_block]')]+'source '+str(p/'hook.tcl')+'\n'+s[s.index('write_db '):]
(p/'encode-patch.tcl').write_text(s)
s=(p/'patch.sbatch').read_text().replace('patch-%j','encode-%j').replace('/patch.tcl','/encode-patch.tcl');(p/'encode.sbatch').write_text(s)
