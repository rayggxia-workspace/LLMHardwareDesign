"""Resolve selected compute/SRAM requirements to actual RTL port contracts.

No physical block endpoints, implicit inter-owner links, or invented DMA bridge.
Unresolved external interfaces remain explicit and prevent completeness.
"""
from pathlib import Path
from hashlib import sha256
import json,sys
from build_projection_local_contract import ports,ROOT,BASE
SOURCES={
 'm_native_leaf_s32':BASE/'rtl/w8a16_v1/m_native_leaf_s32.sv',
 'g_s32':BASE/'rtl/w8a16_v1/g_s32.sv',
 'e_s32_mac_ap64':ROOT/'rtl/macros/e_s32_mac_ap64.sv',
 'n_s32_mod':ROOT/'rtl/macros/n_s32_mod.sv',
 'local_s_p':BASE/'rtl/s_sram/local_s_p.sv',
 'local_s_base':BASE/'rtl/s_sram/local_s_base.sv'}
def build(plan):
 actual=sha256(json.dumps({k:v for k,v in plan.items() if k!='plan_sha256'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 if actual!=plan['plan_sha256']:raise ValueError('plan content hash mismatch')
 hw=plan['hardware'];owners=sorted({c['group'] for c in plan['calls']})
 targets={t['group']:t for t in hw['native_dispatch_overlay']['targets']}
 endpoints={};connections=[];constants=[];unresolved=[];sources={};unused=[]
 schemas={owner:{int.from_bytes(bytes.fromhex(c['descriptor_hex'])[:4],'little') for c in plan['calls'] if c['group']==owner} for owner in owners}
 role_schemas={'m':{0x3152504d},'g':{0x314d5347},'n':{0x3156534e},'e':{0x31444d45,3,0x31455052,0x31414d52}}
 def endpoint(instance,pin,p,kind):
  key=instance+'.'+pin
  row={'instance':instance,'pin':pin,'direction':p['direction'],'shape':p['shape'],'kind':kind}
  if key in endpoints:assert endpoints[key]==row
  endpoints[key]=row;return key
 def connect(a,b):
  x,y=endpoints[a],endpoints[b]
  if x['shape']!=y['shape'] or x['direction']==y['direction']:raise ValueError('incompatible RTL ports '+a+' '+b)
  driver,sink=(a,b) if x['direction']=='output' else (b,a)
  connections.append({'driver':driver,'sink':sink,'shape':x['shape'],'physical_binding':None})
 for owner in owners:
  module=targets[owner]['rtl_module'];source=ROOT/'rtl/control'/(module+'.sv')
  sp=ports(source);sources[str(source)]=sha256(source.read_bytes()).hexdigest()
  if sources[str(source)]!=targets[owner]['rtl_sha256']:raise ValueError('service RTL differs from selected plan')
  parent=owner+'.control.services'
  for role in ('m','g','e','n'):
   prefix='resource_'+role+'_';selected=[n for n in sp if n.startswith(prefix)]
   if not selected:continue
   if not schemas[owner]&role_schemas[role]:
    unused.append({'instance':parent,'ports':selected,'role':role,
     'reason':'no selected instruction uses this macro service; no product connection inferred'})
    continue
   required={'m':'m_native_leaf_s32','g':'g_s32','e':'e_s32_mac_ap64','n':'n_s32_mod'}[role]
   matches=[hw['macro_instances'][n] for n in hw['control_groups'][owner]['macros'] if hw['macro_instances'][n]['master']==required]
   if len(matches)!=1:raise ValueError('ambiguous actual macro for '+owner+' '+role)
   macro=matches[0];path=SOURCES[required];mp=ports(path);sources[str(path)]=sha256(path.read_bytes()).hexdigest()
   for n in selected:
    pin=n[len(prefix):]
    connect(endpoint(parent,n,sp[n],'parent_standard_cells'),
            endpoint(macro['instance'],pin,mp[pin],'functional_macro'))
   if role=='m':
    unresolved.append({'instance':macro['instance'],'kind':'typed_weight_DMA',
      'pins':[n for n in mp if n.startswith('mc_')],'reason':'bind actual typed record/fence client, not generic 64B service DMA'})
  site=hw['control_groups'][owner]['private_sram'];macro=hw['macro_instances'][site]
  path=SOURCES[macro['master']];mp=ports(path);sources[str(path)]=sha256(path.read_bytes()).hexdigest()
  mapping={'s_req_valid':'req_valid','s_req_write':'req_write','s_req_ready':'req_ready',
   's_req_address':'req_addr','s_req_data':'req_data','s_rsp_valid':'rsp_valid','s_rsp_ready':'rsp_ready','s_rsp_data':'rsp_data'}
  for n,pin in mapping.items():
   connect(endpoint(parent,n,sp[n],'parent_standard_cells'),endpoint(site,pin,mp[pin],'functional_macro'))
  constants.append({'sink':endpoint(parent,'s_rsp_error',sp['s_rsp_error'],'parent_standard_cells'),
   'value':0,'reason':'selected SRAM macro exposes no error response pin'})
  for n,p in mp.items():
   if n not in mapping.values() and n not in ('clk','reset') and p['direction']=='input':
    constants.append({'sink':endpoint(site,n,p,'functional_macro'),'value':0,
     'reason':'unused SRAM feeder interface in ordinary-port-only selected implementation'})
  unresolved += [
   {'instance':parent,'kind':'service_DDR_read_write','pins':[n for n in sp if n.startswith(('rd_','wr_'))],
    'reason':'requires real shared DMA adapters, arbitration and completion/error paths'},
   {'instance':owner+'.control.lc','kind':'LC_control_and_scope_DMA',
    'reason':'bind MC switch/config/session plus typed descriptor DMA with live owner/close semantics'}]
 sinks=[c['sink'] for c in connections]+[c['sink'] for c in constants]
 if len(sinks)!=len(set(sinks)):raise ValueError('multiple drivers for selected endpoint')
 if any(ep['instance'] in hw['control_groups'] for ep in endpoints.values()):raise ValueError('opaque group endpoint')
 return {'schema':'selected-native-endpoint-bindings/1','plan_sha256':plan['plan_sha256'],
  'graph_sha256':plan['graph_sha256'],'base_id':hw.get('base_id'),'base_rtl_contract_sha256':hw.get('base_rtl_contract_sha256'),'control_owners':owners,'endpoints':endpoints,
  'connections':connections,'constants':constants,'unresolved':unresolved,'sources':sources,
  'unused_service_interfaces':unused,'physical_binding_complete':False,'scope':'checked selected RTL compute/SRAM ports; full DMA/control and physical wiring pending'}
if __name__=='__main__':
 plan=json.loads(Path(sys.argv[1]).read_text());result=build(plan)
 Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'owners':len(result['control_owners']),'connections':len(result['connections']),
  'constants':len(result['constants']),'unresolved_interfaces':len(result['unresolved'])}))
