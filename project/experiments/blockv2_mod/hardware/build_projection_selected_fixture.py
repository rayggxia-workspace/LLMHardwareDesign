"""Elaboration fixture for selected M/S_P bindings, never a physical P wrapper."""
from pathlib import Path
from build_projection_local_contract import ports,ROOT,BASE
s=ports(ROOT/'rtl/services/projection_local_service_controller.sv')
m=ports(BASE/'rtl/w8a16_v1/m_native_leaf_s32.sv')
ram=ports(BASE/'rtl/s_sram/local_s_p.sv')
external={n:p for n,p in s.items() if not n.startswith(('resource_m_','s_req_','s_rsp_'))}
for n,p in m.items():
    if n.startswith('mc_') or n=='fault_interrupt':external['m_'+n]=p
lines=['// Selected connectivity test fixture only; not a hard P block or an Algo1 chosen plan.',
       'module projection_selected_fixture #(parameter logic [31:0] TOPOLOGY=18503)(']
lines.append(',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items()))
lines.append(');')
for n,p in s.items():
    if n not in external:lines.append(' wire '+p['signed']+p['shape']+n+';')
lines.append(" assign s_rsp_error=1'b0;")
lines.extend([
 ' wire [0:0] provider_valid,provider_ready,provider_cancel_valid,provider_cancel_ready;',
 ' wire [0:0] provider_done_valid,provider_done_ready;',
 ' wire [127:0] provider_owner,provider_done_owner;',
 ' wire [31:0] provider_ticket,provider_done_ticket,provider_done_read_bytes,provider_done_write_bytes;',
 ' wire [1023:0] provider_descriptor;wire [15:0] provider_done_status;',
 " macro_service_dispatch #(.TOPOLOGY(TOPOLOGY),.SCHEMAS(32'h3152504d),.ABIS(32'h02504d03),.OPCODES(16'd2)) dispatch(.*);"])
connections=[]
for n in s:
 target='provider_'+n[len('service_'):] if n.startswith('service_') else n
 connections.append('.'+n+'('+target+')')
lines.append(' projection_local_service_controller #(.TOPOLOGY(TOPOLOGY)) control('+','.join(connections)+');')
connections=[]
for n in m:
    target=n if n in ('clk','reset') else 'm_'+n if n.startswith('mc_') or n=='fault_interrupt' else 'resource_m_'+n
    assert target in s or target in external
    connections.append('.'+n+'('+target+')')
lines.append(' m_native_leaf_s32 M('+','.join(connections)+');')
mapping={'req_valid':'s_req_valid','req_write':'s_req_write','req_addr':'s_req_address',
 'req_data':'s_req_data','req_ready':'s_req_ready','rsp_valid':'s_rsp_valid',
 'rsp_ready':'s_rsp_ready','rsp_data':'s_rsp_data'}
connections=[]
for n,p in ram.items():
    target=n if n in ('clk','reset') else mapping[n] if n in mapping else "'0" if p['direction']=='input' else ''
    connections.append('.'+n+'('+target+')')
lines.append(' local_s_p S('+','.join(connections)+');')
lines.append('endmodule')
out=ROOT/'evidence/architecture-revision-185/projection_selected_fixture.sv'
out.write_text('\n'.join(lines)+'\n')
print(out)
