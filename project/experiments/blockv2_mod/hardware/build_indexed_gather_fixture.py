from pathlib import Path
from build_projection_local_contract import ports,ROOT,BASE
service=ports(ROOT/'rtl/services/indexed_gather_service_controller.sv')
external={n:p for n,p in service.items() if not n.startswith(('s_req_','s_rsp_'))}
lines=['module indexed_gather_fixture #(parameter logic [31:0] TOPOLOGY=18503)(',
 ',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items()),');']
for n,p in service.items():
 if n not in external:lines.append(' wire '+p['signed']+p['shape']+n+';')
lines += [" assign s_rsp_error=0;",' indexed_gather_service_controller #(.TOPOLOGY(TOPOLOGY)) control(.*);',
 ' local_s_base S(.clk,.reset,.req_valid(s_req_valid),.req_write(s_req_write),.req_addr(s_req_address),.req_data(s_req_data),.req_ready(s_req_ready),.rsp_valid(s_rsp_valid),.rsp_ready(s_rsp_ready),.rsp_data(s_rsp_data));','endmodule']
(ROOT/'evidence/architecture-revision-185/indexed_gather_fixture.sv').write_text('\n'.join(lines)+'\n')
