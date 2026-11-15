from pathlib import Path
from build_projection_local_contract import ports,ROOT,BASE
s=ports(ROOT/'rtl/control/projection_service_cluster.sv')
m=ports(BASE/'rtl/w8a16_v1/m_native_leaf_s32.sv')
ram=ports(BASE/'rtl/s_sram/local_s_p.sv')
g=ports(BASE/'rtl/w8a16_v1/g_s32.sv')
external={n:p for n,p in s.items() if not n.startswith(('resource_m_','resource_g_','s_req_','s_rsp_'))}
for n,p in m.items():
 if n.startswith('mc_') or n=='fault_interrupt':external['m_'+n]=p
lines=['// Verification of selected parent connectivity; not a physical P block.',
 'module projection_cluster_fixture #(parameter logic [31:0] TOPOLOGY=18503)(',
 ',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items()),');']
for n,p in s.items():
 if n not in external:lines.append(' wire '+p['signed']+p['shape']+n+';')
lines+=[" assign s_rsp_error=1'b0;"," projection_service_cluster #(.TOPOLOGY(TOPOLOGY)) control(.*);"]
connections=[]
for n in m:
 target=n if n in ('clk','reset') else 'm_'+n if n.startswith('mc_') or n=='fault_interrupt' else 'resource_m_'+n
 assert target in s or target in external
 connections.append('.'+n+'('+target+')')
lines.append(' m_native_leaf_s32 M('+','.join(connections)+');')
connections=[]
for n in g:
 target=n if n in ('clk','reset') else 'resource_g_'+n
 assert target in s
 connections.append('.'+n+'('+target+')')
lines.append(' g_s32 G('+','.join(connections)+');')
mapping={'req_valid':'s_req_valid','req_write':'s_req_write','req_addr':'s_req_address',
 'req_data':'s_req_data','req_ready':'s_req_ready','rsp_valid':'s_rsp_valid',
 'rsp_ready':'s_rsp_ready','rsp_data':'s_rsp_data'}
connections=[]
for n,p in ram.items():
 target=n if n in ('clk','reset') else mapping[n] if n in mapping else "'0" if p['direction']=='input' else ''
 connections.append('.'+n+'('+target+')')
lines+=[' local_s_p S('+','.join(connections)+');','endmodule']
(ROOT/'evidence/architecture-revision-185/projection_cluster_fixture.sv').write_text('\n'.join(lines)+'\n')
