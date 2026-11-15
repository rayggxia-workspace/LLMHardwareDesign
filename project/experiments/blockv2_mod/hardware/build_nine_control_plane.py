"""Selected parent control assembly, not a P/U hard macro or implicit data graph."""
from pathlib import Path
from hashlib import sha256
import json,re,sys
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project')
MC=BASE/'rtl/mother_control_native/mother_control_native64_transport128.sv'
SW=BASE/'rtl/mother_control_native/mc_lc_packet128_switch.sv'
LC=BASE/'experiments/shared_x_control/rtl/lc_native_scope_controller.sv'
MEM=ROOT/'rtl/control/native_shared_memory_plane.sv'
M=BASE/'rtl/w8a16_v1/m_native_leaf_s32.sv'
owners=('P0','P1','P2','C0','U0','J0','F0','U1','J1')
if len(sys.argv)!=2:raise SystemExit('usage: build_nine_control_plane.py selected-wiring.json')
selection=Path(sys.argv[1])
sel=json.loads(selection.read_text())
selected={r['instance'].split('.')[0] for r in sel['endpoints'].values()}
selected_m={r['instance'].split('.')[0] for r in sel['endpoints'].values() if r['instance'].endswith('.M')}
ep={};decl=[];logic=[];inst=[];links=[];unbound=[];sources={};drives=set()
def width(p):
 s=p['shape'].strip()
 if not s:return 1
 m=re.fullmatch(r'\[(\d+):0\]',s)
 if not m:raise ValueError('unsupported port width '+s)
 return int(m[1])+1
def shape(n):return '' if n==1 else '['+str(n-1)+':0] '
def external(n,p):
 if n in ep:assert ep[n]==p
 ep[n]=p;return n
def wire(n,p):
 if n not in drives:decl.append('wire '+p['shape']+n+';');drives.add(n)
 return n
def assign(lhs,rhs):logic.append('assign '+lhs+'='+rhs+';')
def source(p):sources[str(p)]=sha256(p.read_bytes()).hexdigest();return read(p.read_text())
mp=source(MC);lp=source(LC);sp=source(SW);memory=source(MEM);macro_m=source(M)
external('clk',{'direction':'input','shape':'','signed':''})
external('reset',{'direction':'input','shape':'','signed':''})
# MC ports other than its actual packet transport remain real configuration/control IO.
mc={}
transport={'tx_valid','tx_ready','tx_data','tx_target','tx_sop','tx_eop','tx_credit',
 'rx_valid','rx_ready','rx_data','rx_source','rx_sop','rx_eop'}
for n,p in mp.items():
 if n=='clk_i':mc[n]='clk'
 elif n=='rst_ni':mc[n]='!reset'
 elif n=='transport_drained_i':mc[n]='all_drained'
 elif n in transport:mc[n]=wire('mc_'+n,p)
 else:mc[n]=external('mc_'+n,p)
inst.append('mother_control_native64_transport128 #(.SERVICE_STALL_LIMIT(SERVICE_STALL_LIMIT)) mother('+','.join('.'+n+'('+v+')' for n,v in mc.items())+');')
# The switch is fixed control routing. It does not supply functional data paths.
sw={}
for n,p in sp.items():
 if n in ('clk','reset'):v=n
 elif n=='tx_header_target':v='mc_tx_data[31:24]'
 elif n in ('tx_valid','tx_ready','tx_target','tx_sop','rx_valid','rx_ready','rx_data','rx_source','rx_sop','rx_eop'):v='mc_'+n
 elif n=='transport_idle':v=wire('switch_idle',{'shape':''})
 else:
  # Resolve parameterized nine-way packed widths explicitly.
  w=9*128 if n=='lc_tx_data' else 9*8 if n in ('lc_rx_target','lc_rx_header_target') else 9
  v=wire('switch_'+n,{'shape':shape(w)})
 sw[n]=v
inst.append('mc_lc_packet128_switch #(.ENDPOINTS(9)) control_switch('+','.join('.'+n+'('+v+')' for n,v in sw.items())+');')
wire('owner_idle',{'shape':'[8:0] '});wire('all_drained',{'shape':''})
# The single memory plane contains both reads/writes and all finite ownership.
mem={}
for n,p in memory.items():
 if n in ('clk','reset'):mem[n]=n
 elif n.startswith(('c_','service_','write_')) or n=='transport_idle':
  mem[n]=wire('mem_'+n,p)
 else:mem[n]=external('memory_'+n,p)
inst.append('native_shared_memory_plane memory('+','.join('.'+n+'('+v+')' for n,v in mem.items())+');')
assign('all_drained','switch_idle&&(&owner_idle)&&mem_transport_idle&&(&mem_service_idle)&&(&mem_write_idle)')
# One LC/service implementation per owner; only selected owners acquire data links.
for i,owner in enumerate(owners):
 family='p' if owner.startswith('P') else 'n' if owner.startswith('U') else 'e'
 path=ROOT/'rtl/control'/('native_'+family+'_owner_control.sv');ports=source(path);mapping={}
 for n,p in ports.items():
  if n in ('clk','reset'):v=n
  elif n=='lc_transport_drained':v='all_drained'
  elif n=='lc_idle':v='owner_idle['+str(i)+']'
  elif n.startswith('lc_mc_'):
   c='c_'+n[len('lc_mc_'):];assert c in memory
   w=width(p);v='mem_'+c+'['+str(i*w)+'+:'+str(w)+']'
  elif n.startswith('lc_rx_'):
   q=n[len('lc_'):]
   if q in ('rx_data','rx_sop','rx_eop'):v='mc_tx_'+q[3:]
   elif q=='rx_target':v='switch_lc_rx_target['+str(i*8)+'+:8]'
   else:v='switch_lc_'+q+'['+str(i)+']'
  elif n.startswith('lc_tx_'):
   q=n[len('lc_'):]
   if q=='tx_source':v=external('observe_'+owner+'_source',p)
   elif q=='tx_data':v='switch_lc_tx_data['+str(i*128)+'+:128]'
   else:v='switch_lc_'+q+'['+str(i)+']'
  elif n.startswith('service_rd_') or n.startswith('service_wr_'):
   q=n[len('service_'):]
   if q.startswith('rd_'):target='service_'+('req_'+q[3:] if not q.startswith('rd_rsp_') else q[3:])
   else:target='write_'+('req_'+q[3:] if not q.startswith('wr_done_') else q[3:])
   # rd_valid/ready/address/tag use req names; response names are already rsp_*.
   assert target in memory,(n,target)
   w=width(p);v=wire(owner+'_'+n,p)
   lane='mem_'+target+'['+str(i*w)+'+:'+str(w)+']'
   if owner in selected:
    if p['direction']=='output':assign(lane,v)
    else:assign(v,lane)
    links.append({'owner':owner,'service_pin':q,'memory_pin':target,'lane':i,'width':w,'class':'candidate_selected'})
   else:
    if p['direction']=='input':assign(v,"'0")
    else:assign(lane,"'0")
  elif n.startswith('lc_'):v=external(n,dict(p,shape=shape(width(p)*9)))+'['+str(i*width(p))+'+:'+str(width(p))+']'
  else:
   v=external(owner+'_'+n,p);unbound.append({'owner':owner,'port':n,'external':v,'direction':p['direction'],'width':width(p)})
  mapping[n]=v
 inst.append('if(1)begin:'+owner+'\n native_'+family+'_owner_control #(.TARGET(8\'d'+str(i)+'),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control('+','.join('.'+n+'('+v+')' for n,v in mapping.items())+');\nend')
 # LC scopes do not use fabric cancellation or namespace-fence commands.
 for n,p in memory.items():
  if not n.startswith('c_') or p['direction']!='input':continue
  if 'mc_'+n[2:] in lp:continue
  w=width(p)//12
  assign('mem_'+n+'['+str(i*w)+'+:'+str(w)+']',"'1" if n.endswith('_ready') else "'0")
# M weight links use the actual M leaf pin names, with no fictitious cancel ports.
for i,owner in enumerate(owners[:3]):
 for n,p in memory.items():
  if not n.startswith('c_'):continue
  actual='mc_'+n[2:]
  if actual.startswith('mc_fence_') and not actual.startswith('mc_fence_done_'):
   actual=actual.replace('mc_fence_','mc_fence_req_')
  w=width(p)//12;lane='mem_'+n+'['+str((9+i)*w)+'+:'+str(w)+']'
  if actual in macro_m and owner in selected_m:
   q=macro_m[actual];assert width(q)==w and q['direction']!=p['direction']
   v=external(owner+'_M_'+actual,dict(q,direction=p['direction']))
   assign(lane,v) if p['direction']=='input' else assign(v,lane)
   links.append({'owner':owner,'macro_pin':actual,'memory_pin':n,'lane':9+i,'width':w,'class':'candidate_selected'})
  elif p['direction']=='input':assign(lane,"'1" if n.endswith('_ready') else "'0")
lines=['// Parent RTL assembly only: never export as a composite hard block.',
'module native_nine_control_plane #(parameter logic [31:0] TOPOLOGY=18503, LC_IMAGE_ID=25001,',
'parameter integer unsigned SERVICE_STALL_LIMIT=100000000)(',
',\n'.join(p['direction']+' wire '+p['shape']+n for n,p in ep.items()),');']
lines+=decl+logic+inst+['endmodule']
target=ROOT/'rtl/control/native_nine_control_plane.sv';target.write_text('\n'.join(lines)+'\n')
sources[str(target)]=sha256(target.read_bytes()).hexdigest()
manifest={'schema':'nine-control-plane/1','hard_boundary':False,'plan_sha256':sel['plan_sha256'],
 'owners':list(owners),'selected_data_owners':sorted(selected),'selected_M_owners':sorted(selected_m),
 'sources':sources,'selected_memory_links':links,'unbound_functional_macro_ports':unbound,
 'PM_capacity_bytes':{'mother':16384,'each_local':1024},'MC_service_stall_limit':100000000,
 'switch_revision':{'old_profile':'switch03','new_RTL':'mc_lc_packet128_switch ENDPOINTS=9','physical_acceptance':False},
 'scope':'actual MC, nine LC/service controls, switch and shared transport; functional macro endpoint assembly pending',
 'whole_base_accepted':False,'numerical_execution_accepted':False}
(ROOT/'hardware/nine-control-plane.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'sources':len(sources),'memory_links':len(links),'unbound_macro_ports':len(unbound)}))
