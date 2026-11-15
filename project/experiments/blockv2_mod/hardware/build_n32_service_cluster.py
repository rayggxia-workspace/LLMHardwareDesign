"""Parent control/service assembly; no physical group wrapper or functional macro."""
from pathlib import Path
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
proj=read((ROOT/'rtl/services/n32_service_controller.sv').read_text())
gather=read((ROOT/'rtl/services/indexed_gather_service_controller.sv').read_text())
load=read((ROOT/'rtl/p_services/ddr_s128_load_scope.sv').read_text())
store=read((ROOT/'rtl/p_services/s128_kv_store_scope.sv').read_text())
external=dict(proj)
external.update({n:p for n,p in load.items() if n.startswith('rd_') and n not in external})
external.update({n:p for n,p in store.items() if n.startswith('wr_')})
lines=['// Parent standard cells only. No U/P link or functional macro is instantiated.',
 'module n32_service_cluster #(parameter logic [31:0] TOPOLOGY=0)(',
 ',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items()),');',
 ' wire [3:0] provider_valid,provider_ready,provider_cancel_valid,provider_cancel_ready;',
 ' wire [3:0] provider_done_valid,provider_done_ready;',
 ' wire [127:0] provider_owner;wire [31:0] provider_ticket;wire [1023:0] provider_descriptor;',
 ' wire [511:0] provider_done_owner;wire [127:0] provider_done_ticket;',
 ' wire [63:0] provider_done_status;wire [127:0] provider_done_read_bytes,provider_done_write_bytes;',
 " macro_service_dispatch #(.SLOTS(4),.ROUTES(6),.TOPOLOGY(TOPOLOGY),",
 "  .SCHEMAS({32'h32485447,32'h31535744,32'h314c5244,32'h3156534e,32'h3156534e,32'h3156534e}),",
 "  .ABIS({32'h02504402,32'h02500002,32'h02500002,32'h02504e03,32'h02504e03,32'h02504e03}),",
 "  .OPCODES({16'd1,16'd1,16'd1,16'd3,16'd2,16'd1}),.SLOT_MAP({8'd3,8'd2,8'd1,8'd0,8'd0,8'd0})) dispatch(.*);"]
for prefix,ports in [('p',proj),('l',load),('w',store),('g',gather)]:
 for n,p in ports.items():
  if n in ('clk','reset') or n.startswith('service_'):continue
  if prefix=='p' and (n.startswith('resource_') or n in ('source_failed','quarantine','protocol_faults')):continue
  if prefix=='w' and n.startswith('wr_'):continue
  lines.append(' wire '+p['signed']+p['shape']+prefix+'_'+n+';')
for slot,prefix,ports,module,params in [
 (0,'p',proj,'n32_service_controller',''),
 (3,'g',gather,'indexed_gather_service_controller',''),
 (1,'l',load,'ddr_s128_load_scope',",.PAYLOAD_BYTES(512),.LOCAL_DMA_SEQUENCE(1'b1)"),
 (2,'w',store,'s128_kv_store_scope',",.ACTIVATION_SPAN(1'b1)")]:
 connections=[]
 for n,p in ports.items():
  if n in ('clk','reset'):target=n
  elif n.startswith('service_'):
   target='provider_'+n[len('service_'):]
   if n in ('service_valid','service_ready','service_cancel_valid','service_cancel_ready',
            'service_done_valid','service_done_ready'):target+='['+str(slot)+']'
   elif n.startswith('service_done_'):
    width=128 if n.endswith('owner') else 16 if n.endswith('status') else 32
    target+='['+str(slot*width)+'+:'+str(width)+']'
  elif prefix=='p' and (n.startswith('resource_') or n in ('source_failed','quarantine','protocol_faults')):target=n
  elif prefix=='w' and n.startswith('wr_'):target=n
  else:target=prefix+'_'+n
  connections.append('.'+n+'('+target+')')
 lines.append(' '+module+' #(.TOPOLOGY(TOPOLOGY)'+params+') '+prefix+'('+','.join(connections)+');')
lines+=["""

 wire [3:0] c_ready,c_valid;
 wire [127:0] c_tag,c_data;
 wire [1:0] owners;
 native_s128_mux4 sram_arbiter(.clk,.reset,
  .c_valid({g_s_req_valid,w_s_req_valid,l_s_valid,p_s_req_valid}),
  .c_write({g_s_req_write,1'b0,1'b1,p_s_req_write}),
  .c_address({g_s_req_address,w_s_req_address,l_s_address,p_s_req_address}),
  .c_data({g_s_req_data,128'd0,l_s_data,p_s_req_data}),
  .c_tag({32'd0,32'd0,l_s_tag,32'd0}),.c_ready,
  .c_response_valid(c_valid),.c_response_ready({g_s_rsp_ready,w_s_rsp_ready,l_s_rsp_ready,p_s_rsp_ready}),
  .c_response_data(c_data),.c_response_tag(c_tag),.owners_occupied(owners),
  .req_valid(s_req_valid),.req_write(s_req_write),.req_address(s_req_address),.req_data(s_req_data),
  .req_ready(s_req_ready),.rsp_valid(s_rsp_valid),.rsp_ready(s_rsp_ready),.rsp_data(s_rsp_data));
 assign p_s_req_ready=c_ready[0];assign l_s_ready=c_ready[1];assign w_s_req_ready=c_ready[2];
 assign p_s_rsp_valid=c_valid[0];assign l_s_rsp_valid=c_valid[1];assign w_s_rsp_valid=c_valid[2];
 assign p_s_rsp_data=c_data;assign w_s_rsp_data=c_data;assign l_s_rsp_tag=c_tag[63:32];
 assign p_s_rsp_error=s_rsp_error;assign l_s_rsp_error=s_rsp_error;assign w_s_rsp_error=s_rsp_error;
 assign g_s_req_ready=c_ready[3];assign g_s_rsp_valid=c_valid[3];
 assign g_s_rsp_data=c_data;assign g_s_rsp_error=s_rsp_error;
 // Four bounded read slots retain original tags and owners across reordered returns.
 reg [3:0] read_used,read_sent;
 reg [1:0] read_tail,read_issue;
 reg [63:0] read_sequence;
 reg [63:0] read_original[0:3],read_token[0:3],read_address[0:3];
 reg [3:0] read_owner;
 wire choose_load=!g_rd_valid;
 wire accept_read=!reset&&!read_used[read_tail];
 assign g_rd_ready=accept_read&&!choose_load;
 assign l_rd_ready=accept_read&&choose_load;
 assign rd_valid=!reset&&read_used[read_issue]&&!read_sent[read_issue];
 assign rd_address=read_address[read_issue];
 assign rd_tag=read_token[read_issue];
 reg response_match;reg [1:0] response_slot;
 integer ri;
 always @*begin
  response_match=0;response_slot=0;
  for(integer j=0;j<4;j=j+1)
   if(read_used[j]&&read_sent[j]&&read_token[j]==rd_rsp_tag)begin response_match=1;response_slot=j;end
 end
 assign g_rd_rsp_valid=!reset&&rd_rsp_valid&&response_match&&!read_owner[response_slot];
 assign l_rd_rsp_valid=!reset&&rd_rsp_valid&&response_match&&read_owner[response_slot];
 assign g_rd_rsp_tag=read_original[response_slot];assign l_rd_rsp_tag=read_original[response_slot];
 assign g_rd_rsp_data=rd_rsp_data;assign l_rd_rsp_data=rd_rsp_data;
 assign g_rd_rsp_error=rd_rsp_error;assign l_rd_rsp_error=rd_rsp_error;
 assign rd_rsp_ready=!reset&&response_match&&(read_owner[response_slot]?l_rd_rsp_ready:g_rd_rsp_ready);
 always @(posedge clk)begin
  if(reset)begin
   read_used<=0;read_sent<=0;read_tail<=0;read_issue<=0;read_sequence<=0;read_owner<=0;
   for(ri=0;ri<4;ri=ri+1)begin read_original[ri]<=0;read_token[ri]<=0;read_address[ri]<=0;end
  end else begin
   if((g_rd_valid&&g_rd_ready)||(l_rd_valid&&l_rd_ready))begin
    read_used[read_tail]<=1;read_sent[read_tail]<=0;read_owner[read_tail]<=choose_load;
    read_original[read_tail]<=choose_load?l_rd_tag:g_rd_tag;
    read_address[read_tail]<=choose_load?l_rd_address:g_rd_address;
    read_token[read_tail]<=read_sequence;read_sequence<=read_sequence+1;read_tail<=read_tail+1;
   end
   if(rd_valid&&rd_ready)begin read_sent[read_issue]<=1;read_issue<=read_issue+1;end
   if(rd_rsp_valid&&rd_rsp_ready)begin read_used[response_slot]<=0;read_sent[response_slot]<=0;end
  end
 end
endmodule
"""]
(ROOT/'rtl/control/n32_service_cluster.sv').write_text('\n'.join(lines)+'\n')
