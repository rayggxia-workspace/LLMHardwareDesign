// Directed control races for the two-word A ingress. No arithmetic surrogate.
module tb_a32_control #(parameter integer CONTEXTS=8);
 logic clk=0,reset=1;always #5 clk=~clk;
 logic [1:0] a_valid=0;wire a_ready;logic a_bank=0,a_wide=0;
 logic [5:0] a_row=0;logic [3:0] a_tile=0;logic [255:0] a_data=0;
 logic b_valid=0,b_bank=0,b_wide=0,b_half=0;wire b_ready;
 logic [1:0] b_tile=0;logic [511:0] b_data=0;
 logic cmd_valid=0;wire cmd_ready;logic [3:0] cmd_op=0;
 logic [5:0] cmd_index=0;logic [63:0] cmd_data=0;
 wire rsp_valid;logic rsp_ready=0;wire [127:0] rsp_data;
 wire rsp_error,rsp_saturated,busy;
 wire [8191:0] operand_view;wire [63:0] valid_view,format_view;wire operand_locked;
 if(CONTEXTS==0)begin: plain
  block_v2_m #(.A_WORDS_PER_BEAT(2)) dut(.*);
  for(genvar i=0;i<512;i++)assign operand_view[i*16+:16]=dut.aa[i];
  assign valid_view=dut.av;assign format_view=dut.af;assign operand_locked=dut.locked;
 end else begin: contextual
  block_v2_m_context #(.CONTEXTS(CONTEXTS),.A_WORDS_PER_BEAT(2)) dut(.*);
  for(genvar i=0;i<512;i++)assign operand_view[i*16+:16]=dut.aa[i];
  assign valid_view=dut.av;assign format_view=dut.af;assign operand_locked=dut.locked;
 end
 integer cycle=0,seed=247,clear_all=0,clear_same=0,clear_other=0,start_same=0;
 integer busy_other=0,tail_garbage=0,reset_clear=0,legal_pairs=0;
 always @(posedge clk)begin cycle<=cycle+1;if(cycle>4000)$fatal(1,"A32 control watchdog");end
 function automatic integer sample(input bit wide,input integer lane,k);
  return (wide?-1000:-70)+(seed%17)+lane*19+k*3;
 endfunction
 function automatic [127:0] container(input bit wide,input integer lane);
  logic [127:0] value;
  begin value=0;for(integer k=0;k<8;k++)begin
   if(wide)value[k*16+:16]=16'(sample(wide,lane,k));
   else value[k*8+:8]=8'(sample(wide,lane,k));
  end return value;end
 endfunction
 task automatic drive_a(input bit bank,wide,input integer r0,t0,r1,t1,input logic [1:0] mask);
  begin
   a_valid=mask;a_bank=bank;a_wide=wide;
   a_row={3'(r1),3'(r0)};a_tile={2'(t1),2'(t0)};
   a_data={container(wide,1),container(wide,0)};
  end
 endtask
 task automatic check_a(input bit bank,wide,input integer r0,t0,r1,t1,input logic [1:0] mask);
  integer tag;logic signed [15:0] want;
  begin for(integer lane=0;lane<2;lane++)if(mask[lane])begin
   tag=int'(bank)*32+(lane==0?r0:r1)*4+(lane==0?t0:t1);
   if(!valid_view[tag]||format_view[tag]!==wide)$fatal(1,"A32 control tag write");
   for(integer k=0;k<8;k++)begin
    want=16'(sample(wide,lane,k));
    if($signed(operand_view[(tag*8+k)*16+:16])!==want)$fatal(1,"A32 control payload write");
   end
  end end
 endtask
 task automatic write_pair(input bit bank,wide,input integer r0,t0,r1,t1,input bit while_busy);
  begin
   @(negedge clk);drive_a(bank,wide,r0,t0,r1,t1,2'b11);
   @(posedge clk);
   if(!a_ready||(while_busy&&(!busy||!operand_locked)))$fatal(1,"legal pair/busy-other not accepted");
   @(negedge clk);a_valid=0;check_a(bank,wide,r0,t0,r1,t1,2'b11);legal_pairs++;
   if(while_busy)busy_other++;
  end
 endtask
 task automatic finish_response(input bit error_expected);
  logic [127:0] held;
  begin
   while(!rsp_valid)@(negedge clk);
   if(rsp_error!==error_expected||rsp_saturated)$fatal(1,"control response status");
   held=rsp_data;
   repeat(2)begin @(negedge clk);if(!rsp_valid||rsp_error!==error_expected||rsp_data!==held)$fatal(1,"control response unstable");end
   rsp_ready=1;@(negedge clk);rsp_ready=0;
  end
 endtask
 task automatic clear_race(input integer op,index,input bit write_bank,allow_write);
  logic [8191:0] before_data;logic [63:0] before_valid,before_format,expected_valid;
  begin
   @(negedge clk);before_data=operand_view;before_valid=valid_view;before_format=format_view;
   cmd_valid=1;cmd_op=4'(op);cmd_index=6'(index);cmd_data=0;
   drive_a(write_bank,1,0,1,1,2,2'b11);
   @(posedge clk);if(!cmd_ready||a_ready!==allow_write)$fatal(1,"clear race handshake");
   @(negedge clk);cmd_valid=0;a_valid=0;
   expected_valid=op==6?64'd0:before_valid&~(64'hffffffff<<(32*(index&1)));
   if(allow_write)begin
    expected_valid[32*int'(write_bank)+1]=1;expected_valid[32*int'(write_bank)+6]=1;
    check_a(write_bank,1,0,1,1,2,2'b11);clear_other++;
   end else begin
    if(operand_view!==before_data||format_view!==before_format)$fatal(1,"clear race partially wrote A");
    if(op==6)clear_all++;else clear_same++;
   end
   if(valid_view!==expected_valid)$fatal(1,"clear race valid-bank corruption");
   finish_response(0);
  end
 endtask
 initial begin
  logic [8191:0] before_data;logic [63:0] before_valid,before_format;logic [63:0] desc;
  if($value$plusargs("SEED=%d",seed))begin end
  repeat(4)@(negedge clk);reset=0;
  write_pair(1,0,1,0,2,3,0);write_pair(1,1,3,1,4,2,0);write_pair(0,0,0,0,1,0,0);
  // A 01 tail ignores the second lane even if its tags and data are nonzero.
  @(negedge clk);before_data=operand_view;before_valid=valid_view;before_format=format_view;
  drive_a(1,0,6,1,7,2,2'b01);a_data[255:128]='1;
  @(posedge clk);if(!a_ready)$fatal(1,"01 tail rejected");
  @(negedge clk);a_valid=0;check_a(1,0,6,1,7,2,2'b01);
  if(valid_view[62]!==before_valid[62]||format_view[62]!==before_format[62]||
     operand_view[62*128+:128]!==before_data[62*128+:128])$fatal(1,"invalid high lane wrote garbage");tail_garbage++;
  clear_race(11,0,0,0);clear_race(11,0,1,1);clear_race(6,0,1,0);
  // A real legal START overlaps a rejected write to its execution bank.
  write_pair(0,0,0,0,1,0,0);
  @(negedge clk);b_valid=1;b_bank=0;b_wide=0;b_half=0;b_tile=0;b_data={64{8'd1}};
  @(posedge clk);if(!b_ready)$fatal(1,"control B setup blocked");
  @(negedge clk);b_valid=0;
  desc=0;desc[2]=1;desc[7:4]=1;desc[11:8]=8;desc[14:12]=1;desc[18:15]=1;
  before_data=operand_view;before_valid=valid_view;before_format=format_view;
  cmd_valid=1;cmd_op=10;cmd_index=0;cmd_data=desc;drive_a(0,1,2,0,3,0,2'b11);
  @(posedge clk);if(!cmd_ready||a_ready)$fatal(1,"START same-bank handshake");
  @(negedge clk);cmd_valid=0;a_valid=0;
  if(operand_view!==before_data||valid_view!==before_valid||format_view!==before_format)$fatal(1,"START same-bank partial write");start_same++;
  write_pair(1,1,4,0,5,1,1);finish_response(0);
  // Reset dominates an otherwise valid dual write and invalidates every tag.
  @(negedge clk);reset=1;drive_a(1,1,6,2,7,3,2'b11);
  @(posedge clk);if(a_ready||cmd_ready)$fatal(1,"reset accepted ingress");
  @(negedge clk);a_valid=0;
  if(valid_view!==0||format_view!==0)$fatal(1,"reset left stale A tags");reset_clear++;
  reset=0;cmd_valid=1;cmd_op=10;cmd_index=0;cmd_data=desc;
  @(posedge clk);if(!cmd_ready)$fatal(1,"post-reset command blocked");
  @(negedge clk);cmd_valid=0;finish_response(1);
  if(clear_all!=1||clear_same!=1||clear_other!=1||start_same!=1||busy_other!=1||tail_garbage!=1||reset_clear!=1||legal_pairs!=5)$fatal(1,"A32 control coverage");
  $display("A32_CONTROL_MEASURE cycles=%0d contexts=%0d seed=%0d clear_all=%0d clear_same=%0d clear_other=%0d start_same=%0d busy_other=%0d tail_garbage=%0d reset_clear=%0d legal_pairs=%0d",cycle,CONTEXTS,seed,clear_all,clear_same,clear_other,start_same,busy_other,tail_garbage,reset_clear,legal_pairs);
  $display("A32_CONTROL_PASS contexts=%0d seed=%0d",CONTEXTS,seed);
  $finish;
 end
endmodule
