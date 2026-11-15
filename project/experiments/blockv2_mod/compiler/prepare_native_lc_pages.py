"""Generate full-package LC session/fetch/terminal RTL replay with service peers."""
import json,re,sys,zlib
from pathlib import Path
package,out,source=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=False)
m=json.loads((package/'manifest.json').read_text())
calls=json.loads((package/'calls.json').read_text());targets=sorted({c['target'] for c in calls})
local=(package/'local-kernel.bin').read_bytes();desc=(package/'descriptors.bin').read_bytes()
(out/'local.hex').write_text(''.join(local[i:i+16][::-1].hex()+'\n' for i in range(0,len(local),16)))
(out/'descriptors.hex').write_text(''.join(desc[i:i+128][::-1].hex()+'\n' for i in range(0,len(desc),128)))
(out/'targets.hex').write_text(''.join(f"{c['target']:02x}\n" for c in calls))
header=(source/'lc_native_scope_controller.sv').read_text().split(');',1)[0]
header=re.sub(r',\s*(?=(?:input|output)\s+logic)', '\n', header)
ports=[]
for direction,width,names in re.findall(r'(input|output)\s+logic\s*(\[[^\]]+\])?\s*([^\n]+)',header):
    for name in names.strip().rstrip(',').split(','):
        ports.append((direction,width,name.strip()))
decl='\n'.join(f'logic {width} {name};' for _,width,name in ports)
gated={'session_valid','cfg_valid','rx_valid','mc_rsp_valid','service_done_valid','cfg_rsp_ready','tx_ready'}
instances=[]
for t in targets:
    con=[]
    for direction,width,name in ports:
        if direction=='output':
            instances.append(f'logic {width} t{t}_{name};')
            con.append(f'.{name}(t{t}_{name})')
        else:con.append(f'.{name}({name}'+(f' && selected=={t}' if name in gated else '')+')')
    instances.append(f'lc_native_scope_controller #(.TARGET(8\'d{t})) lc{t}('+','.join(con)+');')
for direction,width,name in ports:
    if direction=='output':
        mux=' : '.join(f'selected=={t} ? t{t}_{name}' for t in targets)+" : '0"
        instances.append(f'assign {name}={mux};')
init='\n'.join(f'{name}=0;' for direction,_,name in ports if direction=='input' and name!='clk')
sessions=[]
for page_i,page in enumerate(m['mother_pages']):
    sessions += [f'page_generation={page_i+1};']
    for t in targets:
        sessions += [f'selected={t};session_generation=page_generation;session_valid=1;',
                     'do @(posedge clk);while(!session_ready);@(negedge clk);session_valid=0;']
    sessions += [f'for(current_call={page["first_call"]};current_call<{page["first_call"]+page["call_count"]};current_call++) replay_call();']
boot=[]
for t in targets:
    boot += [f'selected={t};cfg_generation=1;cfg_send(0);',
             f'for(integer j=0;j<{len(local)//16};j++)begin cfg_address=14\'(j*16);cfg_data=image[j];cfg_send(1);end',
             f'cfg_crc=32\'d{zlib.crc32(local)};cfg_send(2);assert(certified);']
s=r"""
`timescale 1ns/1ps
module tb_native_lc_pages;
DECL
integer selected=0,current_call=0,page_generation=0;
integer sequences[0:8],call_count=0,service_count=0,ddr_count=0,boot_count=0;
logic [127:0] image[0:21];
logic [1023:0] descriptors[0:CALLS-1];
logic [7:0] targets[0:CALLS-1];
logic [511:0] active_packet,terminal_packet;
logic [1:0] pending;
logic [31:0] tags[0:1];
integer delay_ticks[0:1],response_slot,service_delay;
logic [511:0] pending_data[0:1];
logic service_pending;
INSTANCES
initial clk=0;always #5 clk=~clk;
task automatic cfg_send(input logic [1:0] operation);
 cfg_op=operation;cfg_valid=1;
 do @(posedge clk);while(!cfg_ready);@(negedge clk);cfg_valid=0;
 while(!cfg_rsp_valid)@(negedge clk);
 assert(cfg_status==0)else $fatal(1,"LC boot rejected");
 cfg_rsp_ready=1;@(negedge clk);cfg_rsp_ready=0;
 if(operation==2)boot_count++;
endtask
task automatic replay_call();
 selected=int'(targets[current_call]);sequences[selected]++;
 assert(idle&&pending==0&&!mc_rsp_valid&&!service_pending&&!service_done_valid);
 active_packet=0;active_packet[0+:16]=2;active_packet[24+:8]=8'(selected);
 active_packet[32+:32]=1;active_packet[64+:32]=1;active_packet[96+:32]=32'(sequences[selected]);
 active_packet[136+:8]=8'(selected);active_packet[160+:32]=25001;
 active_packet[192+:32]=25001;active_packet[224+:32]=32'(page_generation);
 active_packet[256+:64]=64'dBASE+64'(current_call)*128;
 active_packet[320+:32]=32'h00010080;active_packet[352+:32]=32'h02510001;
 active_packet[384+:32]=25001;active_packet[416+:32]=32'h02500002;
 rx_target=8'(selected);
 for(integer w=0;w<4;w++)begin
  rx_valid=1;rx_data=active_packet[128*w+:128];rx_sop=w==0;rx_eop=w==3;
  do @(posedge clk);while(!rx_ready);@(negedge clk);rx_valid=0;
 end
 rx_sop=0;rx_eop=0;terminal_packet=0;
 for(integer w=0;w<4;w++)begin
  while(!tx_valid)@(negedge clk);
  assert(tx_sop==(w==0)&&tx_eop==(w==3)&&tx_source==8'(selected));
  terminal_packet[128*w+:128]=tx_data;
  tx_ready=1;@(negedge clk);tx_ready=0;
 end
 assert(terminal_packet[16+:8]==2&&terminal_packet[144+:16]==0);
 assert(terminal_packet[32+:96]==active_packet[32+:96]);
 assert(terminal_packet[128+:8]==8'(selected));
 assert(terminal_packet[352+:32]==32'(page_generation)&&terminal_packet[384+:32]==25001);
 assert(terminal_packet[192+:32]==128&&terminal_packet[224+:32]==0);
 @(negedge clk);
 assert(idle&&protocol_fault_cycles==0&&retired_instructions==3);
 call_count++;
endtask
assign mc_req_ready=!pending[mc_req_tag[0]]&&!mc_rsp_valid;
assign mc_close_ready=1;
assign service_ready=!service_pending&&!service_done_valid;
assign service_cancel_ready=1;
always @(posedge clk)begin
 if(reset)begin
  pending<=0;mc_rsp_valid<=0;mc_rsp_tag<=0;mc_rsp_data<=0;response_slot<=0;
  service_pending<=0;service_done_valid<=0;service_delay<=0;
  service_done_owner<=0;service_done_ticket<=0;service_done_status<=0;
  service_done_read_bytes<=0;service_done_write_bytes<=0;
  for(integer i=0;i<2;i++)begin tags[i]<=0;delay_ticks[i]<=0;pending_data[i]<=0;end
 end else begin
  if(mc_req_valid&&mc_req_ready)begin
   assert(mc_req_address==active_packet[256+:64]+(mc_req_tag[0]?64:0));
   assert(mc_req_channel==active_packet[267]&&mc_req_record_beats==2);
   pending[mc_req_tag[0]]<=1;tags[mc_req_tag[0]]<=mc_req_tag;
   pending_data[mc_req_tag[0]]<=descriptors[current_call][512*int'(mc_req_tag[0])+:512];
   delay_ticks[mc_req_tag[0]]<=mc_req_tag[0]?2:5;ddr_count<=ddr_count+1;
  end
  for(integer i=0;i<2;i++)if(pending[i]&&delay_ticks[i]>0)delay_ticks[i]<=delay_ticks[i]-1;
  if(mc_rsp_valid&&mc_rsp_ready)begin mc_rsp_valid<=0;pending[response_slot]<=0;end
  if(!mc_rsp_valid)begin
   for(integer i=0;i<2;i++)if(pending[i]&&delay_ticks[i]==0)begin
    mc_rsp_valid<=1;response_slot<=i;mc_rsp_tag<=tags[i];mc_rsp_data<=pending_data[i];
   end
  end
  if(service_valid&&service_ready)begin
   assert(service_descriptor===descriptors[current_call]);
   assert(service_owner=={32'(page_generation),32'd1,32'd1,32'(sequences[selected])});
   assert(service_ticket==32'(sequences[selected]));
   service_pending<=1;service_delay<=7;service_done_owner<=service_owner;service_done_ticket<=service_ticket;
   service_count<=service_count+1;
  end
  if(service_pending&&service_delay>0)service_delay<=service_delay-1;
  if(service_pending&&service_delay==0&&!service_done_valid)begin service_done_valid<=1;service_pending<=0;end
  if(service_done_valid&&service_done_ready)service_done_valid<=0;
  assert(!service_cancel_valid);
 end
end
initial begin
INIT
 reset=1;transport_drained=1;session_topology=25001;
 cfg_abi=32'h02500002;cfg_capacity=32'h02510001;cfg_bytes=352;
 for(integer i=0;i<9;i++)sequences[i]=0;
 $readmemh("OUT/local.hex",image);
 $readmemh("OUT/descriptors.hex",descriptors);
 $readmemh("OUT/targets.hex",targets);
 repeat(3)@(negedge clk);reset=0;
BOOT
SESSIONS
 assert(call_count==CALLS&&service_count==CALLS&&ddr_count==2*CALLS&&boot_count==TARGET_COUNT);
 $display("PASS whole-package LC calls=%0d services=%0d DDR_beats=%0d fixed_kernel_boots=%0d sessions=PAGES",call_count,service_count,ddr_count,boot_count);
 $finish;
end
initial begin #2000000000;$fatal(1,"LC replay watchdog");end
endmodule
"""
# Peer-driven signals are assigned only by the fixture, not the initializer.
peer={'mc_req_ready','mc_close_ready','service_ready','service_cancel_ready','mc_rsp_valid','mc_rsp_tag','mc_rsp_data',
      'service_done_valid','service_done_owner','service_done_ticket','service_done_status','service_done_read_bytes','service_done_write_bytes'}
init='\n'.join(f'{name}=0;' for direction,_,name in ports if direction=='input' and name not in peer|{'clk'})
for k,v in {'DECL':decl,'INSTANCES':'\n'.join(instances),'INIT':init,'BOOT':'\n'.join(boot),
            'SESSIONS':'\n'.join(sessions),'OUT':str(out.resolve()),'CALLS':str(len(calls)),
            'BASE':str(m['descriptor_base']),'TARGET_COUNT':str(len(targets)),'PAGES':str(len(m['mother_pages']))}.items():
    s=s.replace(k,v)
(out/'tb_native_lc_pages.sv').write_text(s)
