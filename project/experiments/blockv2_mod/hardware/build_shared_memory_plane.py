"""Read/write parent control assembly. Only explicitly selected endpoints connect to services."""
from pathlib import Path
from hashlib import sha256
import json
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'rtl/control/native_shared_read_plane.sv'
s=src.read_text()
s=s.replace('native_shared_read_plane','native_shared_memory_plane')
s=s.replace('native_shared_read_dma #','native_shared_memory_dma #')
s=s.replace('.debug_generation(debug_generation)', '.debug_generation(debug_generation),.transport_idle(transport_idle)')
# Internal packed c_* wires only; the public typed LC/M client interface stays 12.
for old,new in [('[20:0]','[29:0]'),('[1343:0]','[1919:0]'),('[671:0]','[959:0]'),
 ('[104:0]','[149:0]'),('[10751:0]','[15359:0]'),('[188:0]','[269:0]')]:s=s.replace(old,new)
marker='output wire [8:0] service_protocol_fault);'
assert marker in s
extra="""
output wire [8:0] service_protocol_fault,
input wire [8:0] write_req_valid,
output wire [8:0] write_req_ready,
input wire [575:0] write_req_address,write_req_tag,
input wire [4607:0] write_req_data,
output wire [8:0] write_done_valid,
input wire [8:0] write_done_ready,
output wire [575:0] write_done_tag,
output wire [8:0] write_done_error,write_idle,write_protocol_fault,
output wire transport_idle,
output reg [3:0] d_req_write,
output reg [2047:0] d_req_data
);"""
s=s.replace(marker,extra)
end='end\nendmodule\n'
assert s.endswith(end)
writeblock="""
end
// A write owns one 64B payload slot until the matched completion retires.
// Backend returns ACK only after write commit; ACK data bit0 is its error bit.
reg [511:0] write_payload[0:8];
wire [4607:0] write_return_payload;
wire [8:0] write_transport_error;
for(genvar w=0;w<9;w=w+1)begin: write_client
 always @(posedge clk)begin
  if(reset)write_payload[w]<=0;
  else if(write_req_valid[w]&&write_req_ready[w])
   write_payload[w]<=write_req_data[w*512+:512];
 end
 native64_dma_serial_client #(.SERIAL_LIMIT(SERVICE_SERIAL_LIMIT)) serial(
 .clk(clk),.reset(reset),.req_valid(write_req_valid[w]),.req_ready(write_req_ready[w]),
 .req_address(write_req_address[w*64+:64]),.req_tag(write_req_tag[w*64+:64]),
 .rsp_valid(write_done_valid[w]),.rsp_ready(write_done_ready[w]),
 .rsp_tag(write_done_tag[w*64+:64]),.rsp_data(write_return_payload[w*512+:512]),
 .rsp_error(write_transport_error[w]),
 .dma_valid(all_c_req_valid[w+21]),.dma_ready(all_c_req_ready[w+21]),
 .dma_address(all_c_req_address[(w+21)*64+:64]),.dma_tag(all_c_req_tag[(w+21)*32+:32]),
 .dma_rsp_valid(all_c_rsp_valid[w+21]),.dma_rsp_ready(all_c_rsp_ready[w+21]),
 .dma_rsp_tag(all_c_rsp_tag[(w+21)*32+:32]),.dma_rsp_data(all_c_rsp_data[(w+21)*512+:512]),
 .fence_valid(all_c_fence_valid[w+21]),.fence_ready(all_c_fence_ready[w+21]),
 .fence_cookie(all_c_fence_cookie[(w+21)*32+:32]),.fence_epoch(all_c_fence_epoch[(w+21)*9+:9]),
 .fence_done_valid(all_c_fence_done_valid[w+21]),.fence_done_ready(all_c_fence_done_ready[w+21]),
 .fence_done_cookie(all_c_fence_done_cookie[(w+21)*32+:32]),.fence_done_epoch(all_c_fence_done_epoch[(w+21)*9+:9]),
 .idle(write_idle[w]),.protocol_fault(write_protocol_fault[w]));
 assign write_done_error[w]=write_transport_error[w]|write_return_payload[w*512];
 assign all_c_req_channel[w+21]=write_req_address[w*64+11];
 assign all_c_req_record_beats[(w+21)*5+:5]=5'd1;
 assign all_c_close_valid[w+21]=1'b0;
 assign all_c_close_tag_base[(w+21)*32+:32]=32'd0;
 assign all_c_cancel_valid[w+21]=1'b0;
 assign all_c_cancel_tag[(w+21)*32+:32]=32'd0;
 assign all_c_cancel_ack_ready[w+21]=1'b1;
end
always @*begin
 d_req_write=0;d_req_data=0;
 for(integer lane=0;lane<4;lane=lane+1)begin
  for(integer w=0;w<9;w=w+1)begin
   if(d_req_valid[lane]&&d_req_tag[lane*64+5+:5]==5'(w+21))begin
    d_req_write[lane]=1;d_req_data[lane*512+:512]=write_payload[w];
   end
  end
 end
end
endmodule
"""
s=s[:-len(end)]+writeblock
target=ROOT/'rtl/control/native_shared_memory_plane.sv';target.write_text(s)
old=json.loads((ROOT/'hardware/shared-read-plane.json').read_text())
old.update(schema='shared-memory-plane/1')
old['sources'].pop(str(ROOT/'rtl/control/native_shared_read_dma.sv'))
old['sources'].pop(str(src))
for p in (target,ROOT/'rtl/control/native_shared_memory_dma.sv'):
 old['sources'][str(p)]=sha256(p.read_bytes()).hexdigest()
old['instances']={'native_shared_memory_dma':1,'native64_dma_serial_client':18}
old['write_client_map']={o:c+9 for o,c in old['service_client_map'].items()}
old['write_payload_bytes']=9*64
old['write_completion']='backend commit ACK; response payload bit0 carries write error, no early source completion'
old['shared_resource_contract']='read and write share the same 64 entries, 6 return skids and 4/3 issue budget per channel'
old['backend_interface']='four combined read/write lanes; write selector and payload are actual registered-parent signals'
(ROOT/'hardware/shared-memory-plane.json').write_text(json.dumps(old,indent=2)+'\n')
print(target)
