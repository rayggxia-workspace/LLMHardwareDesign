from pathlib import Path
import re,sys
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');gs=root/'gs';src=Path(sys.argv[1]).resolve();out=src.with_name(src.name+'-notch');out.mkdir();(out/'config.mk').write_bytes((src/'config.mk').read_bytes())
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(src/'config.mk').read_text(),re.M)[1].split();old=(gs/'f-eco-v4.tcl').read_text();defs=old[old.index('proc boundary {}'):old.index('# DEF encodes')]
body='set_thread_count 8\nset platform /OpenROAD-flow-scripts/flow/platforms/nangate45\nread_liberty $platform/lib/NangateOpenCellLibrary_typical.lib\n'+''.join('read_liberty {'+p+'}\n' for p in libs)+f'read_db {{{src}/candidate.odb}}\nread_sdc {{{src}/candidate.sdc}}\nset_propagated_clock [all_clocks]\nset block [ord::get_db_block]\n'+defs+'set old_boundary [boundary]\nset old_macros [macro_positions]\nset encoder [odb::dbWireEncoder]\n'
patches=[]
for kind,sources,x0,y0,x1,y1,layer in re.findall(r'violation type: (.*?)\n\s*srcs: (.*?)\n\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)',(src/'native-drc.rpt').read_text()):
 names=re.findall(r'net:(\S+)',sources)
 if kind!='Metal Spacing' or len(names)!=1 or 'inst:' in sources or layer not in ['metal2','metal3']:continue
 rect=[round(float(x)*2000) for x in [x0,y0,x1,y1]];a,b,c,d=rect
 assert 0<c-a<=140 and 0<d-b<=140
 n=names[0];assert '{' not in n and '}' not in n
 patches.append([n,layer,rect]);body+=f'set net [$block findNet {{{n}}}]\nif {{$net eq "NULL"}} {{error "Missing notch net"}}\nset wire [$net getWire]\nif {{$wire eq "NULL"}} {{error "Unrouted notch net"}}\n$encoder append $wire\n$encoder newPath [[ord::get_db_tech] findLayer {layer}] ROUTED\n$encoder addPoint {a} {b}\n$encoder addRect 0 0 {c-a} {d-b}\n$encoder end\n'
assert patches
(out/'patches.json').write_text(__import__('json').dumps(patches,indent=2))
body+=old[old.index('if {[boundary] ne $old_boundary || [macro_positions] ne $old_macros}'):]
(out/'repair.tcl').write_text(body)
print(out)
