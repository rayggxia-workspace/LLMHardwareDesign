"""Join LC and service controls; this hierarchy is not a physical block."""
from pathlib import Path
from hashlib import sha256
import json
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
LC=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/shared_x_control/rtl/lc_native_scope_controller.sv')
lp=read(LC.read_text())
result=[]
for family,service in [('p','projection_service_cluster'),('n','n32_service_cluster'),('e','e32_service_cluster')]:
 path=ROOT/'rtl/control'/(service+'.sv');sp=read(path.read_text())
 shared={n for n in lp if n.startswith('service_')}
 assert shared=={n for n in sp if n.startswith('service_')}
 for n in shared:
  assert lp[n]['shape']==sp[n]['shape'] and lp[n]['direction']!=sp[n]['direction'],n
 external={};lc_links={};svc_links={}
 for n,p in lp.items():
  target=n if n in ('clk','reset') or n in shared else 'lc_'+n
  lc_links[n]=target
  if n not in shared:external[target]=p
 for n,p in sp.items():
  target=n if n in ('clk','reset') or n in shared else 'service_'+n
  svc_links[n]=target
  if n not in shared:
   if target in external:assert external[target]==p
   external[target]=p
 module='native_'+family+'_owner_control'
 lines=['// Parent standard cells only. Not a hard macro, physical block, or selected product interconnect.',
 'module '+module+' #(parameter logic [7:0] TARGET=0, parameter logic [31:0] TOPOLOGY=18503, IMAGE_ID=25001)(',
 ',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items()),');']
 for n in sorted(shared):
  p=lp[n];lines.append(' wire '+p['signed']+p['shape']+n+';')
 lines.append(' lc_native_scope_controller #(.TARGET(TARGET),.IMAGE_ID(IMAGE_ID)) lc('+','.join('.'+n+'('+target+')' for n,target in lc_links.items())+');')
 lines.append(' '+service+' #(.TOPOLOGY(TOPOLOGY)) services('+','.join('.'+n+'('+target+')' for n,target in svc_links.items())+');')
 lines.append('endmodule')
 target=ROOT/'rtl/control'/(module+'.sv');target.write_text('\n'.join(lines)+'\n')
 result.append({'family':family,'module':module,'hard_boundary':False,'source':str(target.relative_to(ROOT)),
 'sha256':sha256(target.read_bytes()).hexdigest(),'lc_source':str(LC),'lc_sha256':sha256(LC.read_bytes()).hexdigest(),
 'service_source':str(path.relative_to(ROOT)),'service_sha256':sha256(path.read_bytes()).hexdigest(),
 'internal_service_connections':[{'lc_pin':n,'service_pin':n,'shape':lp[n]['shape']} for n in sorted(shared)],
 'external_ports':external,
 'pending':['LC scope DMA and service read DMA sharing/format adaptation','shared write DMA',
 'MC switch/config/session wiring','selected macro/SRAM endpoints','joined execution'],
 'whole_base_accepted':False})
(ROOT/'hardware/native-owner-controls.json').write_text(json.dumps({'schema':'native-owner-controls/1','controls':result},indent=2)+'\n')
print([(x['module'],len(x['internal_service_connections']),len(x['external_ports'])) for x in result])
