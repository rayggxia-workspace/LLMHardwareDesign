`timescale 1ns/1ps
module tb_a_frontend #(parameter CANCEL=0);
reg  clk=0;
reg  reset=0;
reg  halt=0;
reg  flush=0;
reg  abort_valid=0;
wire  abort_ready;
reg  abort_transport_drained=0;
reg [127:0] abort_key=0;
reg  abort_slot=0;
reg [15:0] abort_generation=0;
reg [15:0] abort_kk=0;
reg [15:0] abort_use_sequence=0;
reg  cmd_valid=0;
wire  cmd_ready;
reg  cmd_slot=0;
reg [15:0] cmd_generation=0;
reg [15:0] cmd_kk=0;
reg [15:0] cmd_planned_uses=0;
reg [127:0] cmd_key=0;
reg [9:0] cmd_S_base=0;
reg [9:0] cmd_copy_offset=0;
reg [127:0] copy_key=0;
reg [10:0] copy_committed_prefix=0;
wire  load_done_valid;
reg  load_done_ready=0;
wire  load_done_slot;
wire  load_done_error;
wire [15:0] load_done_generation;
wire [127:0] load_done_key;
wire  s_valid;
reg  s_ready=0;
wire [9:0] s_address;
wire [31:0] s_tag;
reg  response_valid=0;
wire  response_ready;
reg [31:0] response_tag=0;
reg [127:0] response_data=0;
reg  w_valid=0;
wire  w_ready;
reg  w_slot=0;
reg [15:0] w_generation=0;
reg [15:0] w_kk=0;
reg [15:0] w_use_sequence=0;
reg [127:0] w_key=0;
reg [31:0] w_record=0;
reg  use_valid=0;
wire  use_ready;
reg  use_slot=0;
reg [15:0] use_generation=0;
reg [15:0] use_kk=0;
reg [15:0] use_sequence=0;
reg [127:0] use_key=0;
wire  a_valid;
reg  a_ready=0;
wire [255:0] a_data;
wire [2:0] a_step;
wire [31:0] a_weight_record;
wire [127:0] a_key;
wire  a_slot;
wire [15:0] a_generation;
wire [15:0] a_kk;
wire [15:0] a_use_sequence;
reg  close_valid=0;
wire  close_ready;
reg  close_slot=0;
reg [15:0] close_generation=0;
reg  release_valid=0;
wire  release_ready;
reg  release_slot=0;
reg [15:0] release_generation=0;
wire  quiescent;
wire  source_reads_drained;
wire [1:0] live_slots;
wire [31:0] fault_cycles;
always #5 clk=~clk;
private_a_tile_abort_frontend dut(.clk,.reset,.halt,.flush,.abort_valid,.abort_ready,.abort_transport_drained,.abort_key,.abort_slot,.abort_generation,.abort_kk,.abort_use_sequence,.cmd_valid,.cmd_ready,.cmd_slot,.cmd_generation,.cmd_kk,.cmd_planned_uses,.cmd_key,.cmd_S_base,.cmd_copy_offset,.copy_key,.copy_committed_prefix,.load_done_valid,.load_done_ready,.load_done_slot,.load_done_error,.load_done_generation,.load_done_key,.s_valid,.s_ready,.s_address,.s_tag,.response_valid,.response_ready,.response_tag,.response_data,.w_valid,.w_ready,.w_slot,.w_generation,.w_kk,.w_use_sequence,.w_key,.w_record,.use_valid,.use_ready,.use_slot,.use_generation,.use_kk,.use_sequence,.use_key,.a_valid,.a_ready,.a_data,.a_step,.a_weight_record,.a_key,.a_slot,.a_generation,.a_kk,.a_use_sequence,.close_valid,.close_ready,.close_slot,.close_generation,.release_valid,.release_ready,.release_slot,.release_generation,.quiescent,.source_reads_drained,.live_slots,.fault_cycles);

integer cycle=0,issued_count=0,return_count=0,peak=0,stream_count=0;
reg [15:0] pending=0;reg [31:0] tags[0:15];integer dates[0:15];
integer selected=-1,oldest=0;reg injected=0,bad_offer=0;
always @(posedge clk)if(!reset)begin
 cycle=cycle+1;
 if(cmd_valid&&cmd_ready)cmd_valid<=0;
 if(s_valid&&s_ready)begin
  if(pending[s_tag[14:11]])$fatal(1,"duplicate issue");
  pending[s_tag[14:11]]=1;tags[s_tag[14:11]]=s_tag;dates[s_tag[14:11]]=cycle;
  issued_count=issued_count+1;
 end
 if(response_valid&&response_ready)begin
  if(!bad_offer)begin
   if(!CANCEL&&return_count==0&&selected!=1)$fatal(1,"test did not reorder");
   pending[selected]=0;return_count=return_count+1;end
  else injected=1;
 end
 if($countones(pending)>peak)peak=$countones(pending);
 if($countones(pending)>2)$fatal(1,"more than two");
 if(source_reads_drained&&pending!=0)$fatal(1,"premature drain");
 if(load_done_valid)begin
  if(CANCEL)begin
   if(!load_done_error||pending!=0||issued_count!=return_count||peak!=2)$fatal(1,"cancel drain");
   $display("PASS A two-credit cancel drained mode=%0d",CANCEL);$finish;
  end
  if(!CANCEL && (load_done_error||return_count!=16||peak!=2||fault_cycles!=1))$fatal(1,"load completion");
 end
 if(w_valid&&w_ready)w_valid<=0;
 if(use_valid&&use_ready)use_valid<=0;
 if(a_valid&&a_ready)begin
  if(a_data!={{4{32'(2*a_step+1)}},{4{32'(2*a_step)}}})$fatal(1,"A data order");
  stream_count=stream_count+1;
  if(stream_count==8)begin
   $display("PASS A two-credit reordered payload, bad tag quarantine and stream backpressure");$finish;
  end
 end
 if(cycle>3000)$fatal(1,"timeout pending=%h",pending);
end
always @(negedge clk)if(!reset)begin
 s_ready=cycle%4!=0;
 if(CANCEL==2&&issued_count==1&&!halt)s_ready=0;
 response_valid=0;bad_offer=0;selected=-1;
 oldest=cycle;
 for(integer n=0;n<16;n++)if(pending[n]&&dates[n]<oldest)oldest=dates[n];
 if(cycle-oldest>8)for(integer n=0;n<16;n++)if(pending[n])selected=n;
 if(selected>=0)begin
  response_valid=1;response_tag=tags[selected];response_data={4{32'(selected)}};
  if(!injected&&!CANCEL)begin response_tag=response_tag^(32'd1<<16);bad_offer=1;end
 end
 if(CANCEL==1&&issued_count>=2)halt=1;
 if(CANCEL==2&&issued_count==1&&s_valid)halt=1;
 if(!CANCEL&&load_done_valid)begin w_valid=1;use_valid=1;end
 a_ready=cycle%5!=0;
end
initial begin
 reset=1;repeat(3)@(negedge clk);reset=0;cmd_valid=1;
 cmd_generation=1;cmd_planned_uses=1;cmd_key=1;cmd_S_base=880;copy_key=1;copy_committed_prefix=16;
 load_done_ready=1;w_generation=1;w_key=1;w_use_sequence=1;use_generation=1;use_key=1;use_sequence=1;
end
endmodule
