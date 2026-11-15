"""Materialize explicit selected RTL edges with all thirty PR185 leaf instances.

The resulting module is a product verification assembly, never a composite hard
macro. Inactive-input ties belong to this product fixture, not base prewiring.
"""
from pathlib import Path
from hashlib import sha256
import json,sys
from build_projection_local_contract import ports,ROOT,BASE
from native_selected_endpoint_bindings import SOURCES
sources=dict(SOURCES)
sources.update({
 'block_v2_e_compact':BASE/'rtl/block_v2/block_v2_e_compact.sv',
 'block_v2_g':BASE/'rtl/block_v2/block_v2_g.sv',
 'r_stream_local':BASE/'rtl/r_local_state/r_stream_local.sv',
 'transaction6k':BASE/'rtl/block_v1/transaction6k.sv'})
if len(sys.argv)!=3:raise SystemExit('usage: build_selected_nine_assembly.py selected-wiring.json hardware.json')
hardware=json.loads(Path(sys.argv[2]).read_text())
binding=json.loads(Path(sys.argv[1]).read_text())
control=json.loads((ROOT/'hardware/nine-control-plane.json').read_text())
cp=ROOT/'rtl/control/native_nine_control_plane.sv';control_ports=ports(cp)
unbound={r['external'] for r in control['unbound_functional_macro_ports']}
macros=hardware['macro_instances'];pinmap={};nets={};links=[];constants=[];inactive=[]
source_hashes={str(cp):sha256(cp.read_bytes()).hexdigest()}
def parent_port(ep):
 if ep['instance'].endswith('.control.services'):return ep['instance'].split('.')[0]+'_service_'+ep['pin']
 raise ValueError('unrecognized selected parent endpoint')
def pin(key):
 ep=binding['endpoints'][key]
 if ep['kind']=='functional_macro':return (ep['instance'],ep['pin'])
 return ('controls',parent_port(ep))
for row in binding['connections']:
 a,b=pin(row['driver']),pin(row['sink'])
 if a not in pinmap:
  name='selected_'+str(len(nets));nets[name]=row['shape'];pinmap[a]=name
 name=pinmap[a]
 if b in pinmap and pinmap[b]!=name:raise ValueError('multiple selected drivers')
 pinmap[b]=name
 links.append({'driver':a,'sink':b,'net':name,'shape':row['shape'],'selection':'same-plan data edge'})
for row in binding['constants']:
 key=pin(row['sink'])
 if key in pinmap:raise ValueError('constant overwrites selected driver')
 pinmap[key]="'0" if row['value']==0 else "'1"
 constants.append({'endpoint':key,'value':row['value'],'reason':row['reason']})
# Bind the previously explicit M transport ports to each selected real M pin.
for row in control['selected_memory_links']:
 if 'macro_pin' not in row:continue
 inst=row['owner']+'.M';p=row['macro_pin'];external=row['owner']+'_M_'+p
 assert external in control_ports
 q=('controls',external);m=(inst,p)
 if q in pinmap or m in pinmap:raise ValueError('duplicate M DMA binding')
 n='selected_'+str(len(nets));nets[n]=control_ports[external]['shape']
 pinmap[q]=pinmap[m]=n;unbound.add(external)
 links.append({'endpoints':[q,m],'net':n,'shape':nets[n],'selection':'same-plan M DMA edge'})
# No unregistered selected functional input may silently become a constant.
selected={ep['instance'] for ep in binding['endpoints'].values() if ep['kind']=='functional_macro'}
declarations=['wire '+s+n+';' for n,s in nets.items()]
outer={};controller={}
for n,p in control_ports.items():
 key=('controls',n)
 if key in pinmap:v=pinmap[key]
 elif n in unbound:
  v="'0" if p['direction']=='input' else ''
  inactive.append({'endpoint':key,'reason':'no selected product edge','value':0 if v else None})
 else:v=n;outer[n]=p
 controller[n]=v
instances=['native_nine_control_plane #(.TOPOLOGY(TOPOLOGY),.LC_IMAGE_ID(LC_IMAGE_ID),.SERVICE_STALL_LIMIT(SERVICE_STALL_LIMIT)) controls('+','.join('.'+n+'('+v+')' for n,v in controller.items())+');']
for owner in hardware['control_groups']:
 instances.append('if(1)begin:'+owner)
 for name in hardware['control_groups'][owner]['macros']:
  spec=macros[name];path=sources[spec['master']];source_hashes[str(path)]=sha256(path.read_bytes()).hexdigest()
  native=ports(path);mapping={}
  for n,p in native.items():
   key=(name,n)
   if n in ('clk','clk_i'):v='clk'
   elif n in ('reset','rst_i'):v='reset'
   elif n in ('rst_n','rst_ni'):v='!reset'
   elif key in pinmap:
    v=pinmap[key]
    if v in nets and nets[v]!=p['shape']:raise ValueError('macro width mismatch '+name+'.'+n)
   elif p['direction']=='input':
    if name in selected:raise ValueError('selected functional input has no explicit edge: '+name+'.'+n)
    v="'0";inactive.append({'endpoint':key,'value':0,'reason':'inactive macro in this product plan; not a fixed base edge'})
   elif p['direction']=='output':v=''
   else:raise ValueError('unresolved functional inout '+name+'.'+n)
   mapping[n]=v
  instances.append(spec['master']+' '+spec['role']+'('+','.join('.'+n+'('+v+')' for n,v in mapping.items())+');')
 instances.append('end')
lines=['// Product RTL verification assembly: thirty independent functional macros and parent controls.',
 '// Not a hard macro; no group exterior or these top-level ports define physical placement.',
 'module native_selected_nine_assembly #(parameter logic [31:0] TOPOLOGY=18503, LC_IMAGE_ID=25001,',
 'parameter integer unsigned SERVICE_STALL_LIMIT=100000000)(',
 ',\n'.join(p['direction']+' wire '+p['shape']+n for n,p in outer.items()),');']
lines+=declarations+instances+['endmodule']
target=ROOT/'rtl/native_selected_nine_assembly.sv';target.write_text('\n'.join(lines)+'\n')
source_hashes[str(target)]=sha256(target.read_bytes()).hexdigest()
manifest={'schema':'selected-nine-RTL-assembly/1','hard_boundary':False,
 'base_id':hardware.get('base_id'),'plan_sha256':binding['plan_sha256'],'functional_instances':{n:m['master'] for n,m in macros.items()},
 'sources':source_hashes,'selected_data_connections':links,'declared_constants':constants,
 'inactive_product_inputs':inactive,'parent_assembly':control,
 'physical_hierarchy':'only functional macro instances are hard boundaries; controls are parent standard cells',
 'selection_scope':'union of explicit prefill/decode candidate edges; no inferred inter-owner data connection',
 'whole_base_accepted':False,'elaboration_accepted':False,'numerical_execution_accepted':False}
(ROOT/'hardware/selected-nine-assembly.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'functional_macros':len(macros),'selected_links':len(links),'external_control_ports':len(outer)}))
