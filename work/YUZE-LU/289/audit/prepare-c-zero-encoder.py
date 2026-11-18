from pathlib import Path
import re,json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-rcx-zero-normalization-v1';old=p/'reextract-rewire';out=p/'reextract-encoder';out.mkdir(exist_ok=False)
for n in ('geometry-all.tcl','def-material.py','check-import.py'):(out/n).write_bytes((old/n).read_bytes())
receipt=json.loads((p/'edit-receipt.json').read_text());text=(p/'normalized.def').read_text();sec=re.search(r'\nNETS\s+\d+\s*;(.*?)\nEND NETS',text,re.S)[1];bodies={m[1]:m[2] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',sec,re.M|re.S)};widths={s.split('\t')[0] for s in (r/'audit/C-main-clock4-physical-v1/rcx-material-119977/layers.tsv').read_text().splitlines()};vias={s.split('\t')[0] for s in (r/'audit/C-main-clock4-physical-v1/rcx-material-119977/vias.tsv').read_text().splitlines()};cmd=['namespace eval ::c_zero_normalization {','set tech [[ord::get_db] getTech]','set block [ord::get_db_block]']
for net in receipt['target_nets']:
 cmd+=['set target [$block findNet {'+net+'}]','if {$target eq "NULL" || [$target getWire] eq "NULL"} {error "Exact target net/wire missing"}','odb::dbWire_destroy [$target getWire]','set w [odb::dbWire_create $target]','set e [odb::new_dbWireEncoder]','$e begin $w']
 body=bodies[net].split('+ ROUTED',1)[1]
 for part in re.split(r'\bNEW\s+',body):
  layer,seq=part.strip().split(None,1);assert layer in widths;cmd.append('$e newPath [$tech findLayer '+layer+'] ROUTED');prev=None
  for m in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,v=m.groups()
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));cmd.append('$e addPoint %d %d%s'%(pt[0],pt[1],(' '+ext) if ext is not None else ''));prev=pt
   else:
    assert v in vias,('Unknown route token',v);cmd+=['set via [$block findVia {'+v+'}]','if {$via ne "NULL"} {$e addVia $via} else {$e addTechVia [$tech findVia {'+v+'}]}']
 cmd+=['$e end','odb::delete_dbWireEncoder $e']
cmd+=['}'];(out/'wire-hook.tcl').write_text('\n'.join(cmd)+'\n')
s=(old/'extract-consistency.tcl').read_text();start=s.index('set zero_nets');end=s.index('if {[geometry_snapshot imported-geometry.tsv]',start);s=s[:start]+'write_verilog original.v\nsource wire-hook.tcl\n'+s[end:];(out/'extract-consistency.tcl').write_text(s)
s=(p/'reextract-rewire.sbatch').read_text().replace('out=$r/audit/C-rcx-zero-normalization-v1/reextract-rewire','out=$r/audit/C-rcx-zero-normalization-v1/reextract-encoder');(p/'reextract-encoder.sbatch').write_text(s)
