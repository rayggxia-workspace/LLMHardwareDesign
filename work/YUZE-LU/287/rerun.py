import pathlib,re,concurrent.futures,subprocess,json,csv
P=pathlib.Path;root=P(__file__).resolve().parent
platform='/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/'
config=P('/public/home/yuzelu/project-circuit/issue250-c-frame-data-boot-cap-eco-20261112-03/parent/config.mk').read_text()
lefs=[platform+'NangateOpenCellLibrary.tech.lef',platform+'NangateOpenCellLibrary.macro.mod.lef']+re.search(r'^export ADDITIONAL_LEFS = (.*)$',config,re.M)[1].split()+['/public/home/yuzelu/project-circuit/issue252-native32-20261111-side-n32-compact-boundary01/boundary-view/n_s32_softmax_s128-boundary.lef']
dest=root/'v4';dest.mkdir(exist_ok=True)
decl=['input clk'];inst=[]
for role in ('C','U'):
 v=(root/(role+'-v2')/'exported.v').read_text();top=re.search(r'module\s+(\S+)\s*\(',v)[1];con=[]
 for direction,width,name in re.findall(r'^\s*(input|output|inout)\s*(\[[^\]]+\])?\s*(\\\S+|\w+)\s*;',v,re.M):
  if name=='clk_i':expr='clk'
  elif (role,name) in [('C','native_tx_data_o'),('U','native_rx_data_i')]:expr='link_data'
  else:expr=role+'_'+name;decl.append(f'{direction} {width} {expr}')
  con.append(f'.{name}({expr})')
 inst.append(f'{top} {role} (\n'+',\n'.join(con)+'\n);')
(dest/'harness.v').write_text('module cu_replay(\n'+',\n'.join(decl)+'\n);\nwire [127:0] link_data;\n'+'\n'.join(inst)+'\nendmodule\n')
for p in root.glob('*.spef'):(dest/p.name).write_text(p.read_text().replace('C:outgoing_data[','C:native_tx_data_o[').replace('U:incoming_data[','U:native_rx_data_i['))
rows=list(csv.DictReader((root/'C-v2/ports.tsv').open(),delimiter='\t'))
pinmap={r['port']:'C/'+r['cell']+'/'+r['pin'] for r in rows if r['pin_direction']=='OUTPUT'}
removed={}
for role in ('C','U'):
 original=(root/(role+'-v2')/'exported.v').read_text()
 pattern=r'^\s*(?:\w*FILLCELL\w*|TAPCELL_X1)\s+\S+\s*\(\s*\);\s*$'
 removed[role]=re.findall(pattern,original,re.M)
 (dest/(role+'.v')).write_text(re.sub(pattern,'',original,flags=re.M))
(dest/'physical-only-removed.json').write_text(json.dumps(removed,indent=2))
jobs=[]
for old in sorted(root.glob('*-[23]00/run.tcl')):
 out=dest/old.parent.name;out.mkdir(exist_ok=True)
 t='\n'.join('read_lef {'+f+'}' for f in lefs)+'\n'+old.read_text()
 for role in ('C','U'):t=t.replace(str(root/(role+'-v2')/'exported.v'),str(dest/(role+'.v')))
 t=t.replace(str(root/'harness.v'),str(dest/'harness.v'))
 for p in root.glob('*.spef'):t=t.replace(str(p),str(dest/p.name))
 for bit in range(128):t=t.replace('{'+pinmap[f'outgoing_data[{bit}]']+'}','{'+pinmap[f'native_tx_data_o[{bit}]']+'}')
 (out/'run.tcl').write_text(t);jobs.append(out/'run.tcl')
def one(p):
 with (p.parent/'run.log').open('w') as f:
  rc=subprocess.call(['openroad','-no_init','-threads','2','-exit',str(p)],cwd=p.parent,stdout=f,stderr=subprocess.STDOUT)
 return {'case':p.parent.name,'exit':rc}
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:result=list(pool.map(one,jobs))
(dest/'run-status.json').write_text(json.dumps(result,indent=2))
assert all(x['exit']==0 for x in result),result
