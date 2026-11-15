from pathlib import Path
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'rtl/services/projection_stream_controller.sv'
ports=read(src.read_text())
service=[n for n in ports if n.startswith('service_')]
macro=[n for n in ports if n.startswith(('lc_','lr_','a_')) and not n.startswith(('a_load_','a_source_'))]
# Only actual M-native command, response and A-input pins are resource endpoints.
expected={'lc_valid','lc_ready','lc_sop','lc_eop','lc_data','lr_valid','lr_ready','lr_sop','lr_eop','lr_data',
          'a_valid','a_ready','a_data','a_session','a_beat'}
assert set(macro)==expected
lines=['// Parent service controller. No M/S macro or U/P product connection is instantiated.',
       'module projection_local_service_controller #(parameter logic [31:0] TOPOLOGY=0)(',
       ' input wire clk,reset,']
for n in service:
 p=ports[n];lines.append(' '+p['direction']+' wire '+p['signed']+p['shape']+n+',')
for n in macro:
 p=ports[n];lines.append(' '+p['direction']+' wire '+p['signed']+p['shape']+'resource_m_'+n+',')
lines+=[' output wire s_req_valid,s_req_write,input wire s_req_ready,',
 ' output wire [9:0] s_req_address,output wire [127:0] s_req_data,',
 ' input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,input wire s_rsp_error,',
 ' output wire rd_valid,input wire rd_ready,output wire [63:0] rd_address,rd_tag,',
 ' input wire rd_rsp_valid,output wire rd_rsp_ready,input wire [63:0] rd_rsp_tag,',
 ' input wire [511:0] rd_rsp_data,input wire rd_rsp_error,',
 ' output wire source_failed,output wire quarantine,output wire [31:0] protocol_faults',
 ');']
body=(ROOT/'hardware/projection_local_service_body.svh.in').read_text()
assert body.lstrip().startswith('wire ') and body.rstrip().endswith('endmodule')
(ROOT/'rtl/services/projection_local_service_controller.sv').write_text('\n'.join(lines)+body)
