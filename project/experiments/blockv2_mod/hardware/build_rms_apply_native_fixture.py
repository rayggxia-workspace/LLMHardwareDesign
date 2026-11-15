from pathlib import Path
from build_projection_local_contract import ports,ROOT,BASE
service=ports(ROOT/'rtl/services/rms_apply_native_service_controller.sv')
macro=ports(ROOT/'rtl/macros/e_s32_mac_ap64.sv')
ram=ports(BASE/'rtl/s_sram/local_s_base.sv')
external={n:p for n,p in service.items() if not n.startswith(('resource_e_','s_req_','s_rsp_'))}
lines=['// Selected E/S_base connectivity fixture. No physical control-group boundary.',
 'module rms_apply_native_fixture #(parameter logic [31:0] TOPOLOGY=18503)(',
 ',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items()),');']
for n,p in service.items():
 if n not in external:lines.append(' wire '+p['signed']+p['shape']+n+';')
for n,p in macro.items():
 if n not in ('clk','reset'):lines.append(' wire '+p['signed']+p['shape']+'macro_'+n+';')
lines+=[" assign s_rsp_error=1'b0;",' rms_apply_native_service_controller #(.TOPOLOGY(TOPOLOGY)) control(.*);',
 ' wire [3:0] c_ready,c_valid,c_error;wire [3:0][63:0] c_data;wire [3:0][3:0] c_clipped;wire busy;',
 ' assign resource_e_in_ready=c_ready[2];assign resource_e_out_valid=c_valid[2];',
 ' assign resource_e_out_data=c_data[2];assign resource_e_out_clipped=c_clipped[2];assign resource_e_out_error=c_error[2];',
 """ e32_service_selector #(.CLIENTS(4),.MAC_CONTEXT(1'b1)) selector(
 .clk,.reset,.client_in_valid({1'd0,resource_e_in_valid,2'd0}),.client_in_ready(c_ready),
 .client_in_data({64'd0,resource_e_in_data,128'd0}),.client_in_op({4'd0,resource_e_in_op,8'd0}),
 .client_in_mask({4'd0,resource_e_in_mask,8'd0}),.client_in_shift({8'd0,resource_e_in_shift,16'd0}),
 .client_in_minus({3'd0,resource_e_in_minus,6'd0}),.client_out_valid(c_valid),
 .client_out_ready({1'd0,resource_e_out_ready,2'd0}),.client_out_data(c_data),
 .client_out_clipped(c_clipped),.client_out_error(c_error),
 .macro_in_valid,.macro_in_ready,.macro_in_data,.macro_in_op,.macro_in_mask,.macro_in_shift,.macro_in_minus,
 .macro_out_valid,.macro_out_ready,.macro_out_data,.macro_out_clipped,.macro_out_error,.busy);"""]
connections=['.'+n+'('+ (n if n in ('clk','reset') else 'macro_'+n)+')' for n in macro]
lines.append(' e_s32_mac_ap64 E('+','.join(connections)+');')
mapping={'req_valid':'s_req_valid','req_write':'s_req_write','req_addr':'s_req_address','req_data':'s_req_data',
 'req_ready':'s_req_ready','rsp_valid':'s_rsp_valid','rsp_ready':'s_rsp_ready','rsp_data':'s_rsp_data'}
connections=[]
for n in ram:
 assert n in ('clk','reset') or n in mapping,n
 connections.append('.'+n+'('+mapping.get(n,n)+')')
lines+=[' local_s_base S('+','.join(connections)+');','endmodule']
(ROOT/'evidence/architecture-revision-185/rms_apply_native_fixture.sv').write_text('\n'.join(lines)+'\n')
