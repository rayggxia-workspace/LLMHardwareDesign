from pathlib import Path
import sys
source=Path(sys.argv[2] if len(sys.argv)>2 else 'rtl/control/projection_service_cluster.sv').read_text()
body=source[source.index(' // Four bounded read slots'):].replace('g_rd','p_rd')
ports=['input wire clk,reset']
for prefix in ('p_','l_'):
 ports += [f'input wire {prefix}rd_valid',f'output wire {prefix}rd_ready',f'input wire [63:0] {prefix}rd_address,{prefix}rd_tag',
 f'output wire {prefix}rd_rsp_valid',f'input wire {prefix}rd_rsp_ready',f'output wire [63:0] {prefix}rd_rsp_tag',
 f'output wire [511:0] {prefix}rd_rsp_data',f'output wire {prefix}rd_rsp_error']
ports += ['output wire rd_valid','input wire rd_ready','output wire [63:0] rd_address,rd_tag','input wire rd_rsp_valid',
'output wire rd_rsp_ready','input wire [63:0] rd_rsp_tag','input wire [511:0] rd_rsp_data','input wire rd_rsp_error']
Path(sys.argv[1]).write_text('module projection_read_queue(\n'+',\n'.join(ports)+'\n);\n'+body)
