// Independent scalar integer oracle for both native M implementations.
module tb_a32_m #(parameter integer WORDS=2, CONTEXTS=8);
 logic clk=0,reset=1;always #5 clk=~clk;
 logic [WORDS-1:0] a_valid=0;
 wire a_ready;logic a_bank=0,a_wide=0;
 logic [3*WORDS-1:0] a_row=0;logic [2*WORDS-1:0] a_tile=0;
 logic [128*WORDS-1:0] a_data=0;
 logic b_valid=0,b_bank=0,b_wide=0,b_half=0;wire b_ready;
 logic [1:0] b_tile=0;logic [511:0] b_data=0;
 logic cmd_valid=0;wire cmd_ready;logic [3:0] cmd_op=0;
 logic [5:0] cmd_index=0;logic [63:0] cmd_data=0;
 wire rsp_valid;logic rsp_ready=0;wire [127:0] rsp_data;
 wire rsp_error,rsp_saturated,busy;
 wire [8191:0] operand_view;wire [127:0] tag_view;wire operand_locked;
 if(CONTEXTS==0)begin: plain
  block_v2_m #(.A_WORDS_PER_BEAT(WORDS)) dut(.*);
  for(genvar i=0;i<512;i++)assign operand_view[i*16+:16]=dut.aa[i];
  assign tag_view={dut.av,dut.af};assign operand_locked=dut.locked;
 end else begin: contextual
  block_v2_m_context #(.CONTEXTS(CONTEXTS),.A_WORDS_PER_BEAT(WORDS)) dut(.*);
  for(genvar i=0;i<512;i++)assign operand_view[i*16+:16]=dut.aa[i];
  assign tag_view={dut.av,dut.af};assign operand_locked=dut.locked;
 end
 integer cycle=0,seed=247,shape=0,nrows=1,ntiles=1,lastk=1;
 integer numeric=0,invalid_masks=0,duplicate_tags=0,busy_stalls=0,a_words=0,a_beats=0;
 integer shapes=0,compute_cycles=0,feed_cycles=0;
 bit aw=0,bw=0;
 always @(posedge clk)begin cycle<=cycle+1;if(cycle>1000000)$fatal(1,"M watchdog");end
 function automatic integer aval(input integer row,k);
  if(aw&&k%13==0)return -32768;
  if(aw&&k%13==1)return 32767;
  return ((row*7+k*3+shape*5)%23-11)*(aw?313:1);
 endfunction
 function automatic integer bval(input integer col,k);
  if(bw&&k%17==0)return -32768;
  if(bw&&k%17==1)return 32767;
  return ((col*5+k*7+shape*3)%19-9)*(bw?211:1);
 endfunction
 function automatic [127:0] aword(input integer row,tile);
  logic [127:0] value;
  begin value=0;for(integer k=0;k<8;k++)begin
   if(aw)value[16*k+:16]=16'(aval(row,tile*8+k));else value[8*k+:8]=8'(aval(row,tile*8+k));
  end return value;end
 endfunction
 function automatic longint signed expected(input integer row,col);
  longint signed total;
  begin total=0;for(integer k=0;k<(ntiles-1)*8+lastk;k++)total+=64'(aval(row,k))*64'(bval(col,k));return total;end
 endfunction
 task automatic command(input integer op,index,input logic [63:0] data,input bit reject,output logic [127:0] got);
  logic [127:0] held;logic [8191:0] before_operands;logic [127:0] before_tags;
  integer start_cycle;
  begin
   @(negedge clk);cmd_op=4'(op);cmd_index=6'(index);cmd_data=data;cmd_valid=1;
   do @(posedge clk);while(!cmd_ready);
   @(negedge clk);cmd_valid=0;start_cycle=cycle;
   if(op==10||op==13)begin
    before_operands=operand_view;before_tags=tag_view;
    a_valid=WORDS'(1);a_bank=0;a_row=0;a_tile=0;a_data='1;
   end
   while(!rsp_valid)begin
    @(negedge clk);
    if((op==10||op==13)&&operand_locked)begin
     if(a_ready||operand_view!==before_operands||tag_view!==before_tags)$fatal(1,"busy A bank changed");busy_stalls++;
    end
   end
   a_valid=0;
   if(rsp_error!==reject||rsp_saturated)$fatal(1,"M command status op=%0d err=%0d",op,rsp_error);
   if(op==10||op==13)compute_cycles+=cycle-start_cycle;
   held=rsp_data;
   repeat(2)begin @(negedge clk);if(!rsp_valid||rsp_data!==held||rsp_error!==reject)$fatal(1,"M held response changed");end
   got=held;rsp_ready=1;@(negedge clk);rsp_ready=0;
  end
 endtask
 task automatic illegal_beats;
  logic [8191:0] before_operands;logic [127:0] before_tags;
  begin
   if(WORDS==2)begin
    @(negedge clk);before_operands=operand_view;before_tags=tag_view;
    a_valid=WORDS'(2);a_row=(3*WORDS)'({3'd7,3'd6});a_tile=(2*WORDS)'({2'd3,2'd2});a_data='1;
    repeat(3)begin @(posedge clk);if(a_ready)$fatal(1,"high-only mask accepted");@(negedge clk);
     if(operand_view!==before_operands||tag_view!==before_tags)$fatal(1,"invalid mask partially wrote bank");end
    invalid_masks++;a_valid=WORDS'(3);a_row=0;a_tile=0;
    repeat(3)begin @(posedge clk);if(a_ready)$fatal(1,"duplicate tag accepted");@(negedge clk);
     if(operand_view!==before_operands||tag_view!==before_tags)$fatal(1,"duplicate tag partially wrote bank");end
    duplicate_tags++;a_valid=0;
   end
  end
 endtask
 task automatic feed;
  integer seq,count,mark;logic [127:0] ignored;
  begin
   mark=cycle;a_bank=0;a_wide=aw;seq=0;
   while(seq<nrows*ntiles)begin
    count=(nrows*ntiles-seq)<WORDS?(nrows*ntiles-seq):WORDS;
    @(negedge clk);a_valid=WORDS'((1<<count)-1);a_row=0;a_tile=0;a_data=0;
    for(integer lane=0;lane<count;lane++)begin
     a_row[lane*3+:3]=3'((seq+lane)%nrows);a_tile[lane*2+:2]=2'((seq+lane)/nrows);
     a_data[lane*128+:128]=aword((seq+lane)%nrows,(seq+lane)/nrows);
    end
    do @(posedge clk);while(!a_ready);
    @(negedge clk);a_valid=0;seq+=count;a_words+=count;a_beats++;
   end
   feed_cycles+=cycle-mark;
   for(integer t=0;t<ntiles;t++)for(integer half=0;half<(bw?2:1);half++)begin
    @(negedge clk);b_valid=1;b_bank=0;b_wide=bw;b_half=1'(half);b_tile=2'(t);b_data=0;
    for(integer e=0;e<(bw?32:64);e++)begin
     if(bw)b_data[16*e+:16]=16'(bval((e+half*32)/8,t*8+e%8));
     else b_data[8*e+:8]=8'(bval(e/8,t*8+e%8));
    end
    do @(posedge clk);while(!b_ready);
    @(negedge clk);b_valid=0;
   end
   illegal_beats();
   // Bad beats must neither destroy initialized operands nor make tags appear.
   command(4,0,64'd1,0,ignored);
  end
 endtask
 initial begin
  logic [63:0] desc;logic [127:0] got;longint signed want;
  if($value$plusargs("SEED=%d",seed))begin end
  repeat(4)@(negedge clk);reset=0;
  for(integer fmt=0;fmt<4;fmt++)for(integer ri=0;ri<4;ri++)for(integer nt=1;nt<=4;nt++)begin
   shape=fmt*16+ri*4+nt;aw=1'(fmt/2);bw=1'(fmt%2);
   nrows=ri==0?1:ri==1?3:ri==2?7:8;ntiles=nt;lastk=shape%8+1;
   command(6,0,0,0,got);feed();
   if(CONTEXTS==0)begin
    desc=0;desc[0]=aw;desc[1]=bw;desc[2]=1;desc[7:4]=4'(lastk);desc[11:8]=8;desc[14:12]=3'(ntiles);desc[18:15]=4'(nrows);
    command(10,0,desc,0,got);
   end
   for(integer row=0;row<nrows;row++)begin
    if(CONTEXTS!=0)begin
     desc=0;desc[0]=aw;desc[1]=bw;desc[2]=1;desc[3]=1;desc[7:4]=4'(lastk);desc[11:8]=8;desc[14:12]=3'(ntiles);
     desc[17:15]=3'(row);desc[49:34]=16'(shape);command(13,row,desc,0,got);
    end
    for(integer pair_id=0;pair_id<4;pair_id++)begin
     command(3,row*8+pair_id,0,0,got);
     for(integer lane=0;lane<2;lane++)begin
      want=expected(row,pair_id*2+lane);
      if($signed(got[lane*64+:64])!==want)$fatal(1,"M scalar mismatch shape=%0d row=%0d col=%0d",shape,row,pair_id*2+lane);numeric++;
     end
    end
    if(CONTEXTS!=0)begin command(14,row,64'(shape)<<1,0,got);command(3,row*8,0,1,got);end
   end
   shapes++;
  end
  // Reset discards all operand-valid tags; no stale successful dot is allowed.
  @(negedge clk);reset=1;repeat(3)@(negedge clk);reset=0;
  if(tag_view!==0)$fatal(1,"reset retained A tags");
  command(10,0,64'h0000000000009154,1,got);
  if(shapes!=64||numeric!=2432||busy_stalls==0||(WORDS==2&&(invalid_masks!=64||duplicate_tags!=64)))$fatal(1,"M coverage count");
  $display("A32_M_MEASURE cycles=%0d words=%0d contexts=%0d shapes=%0d numeric=%0d feed_cycles=%0d compute_cycles=%0d a_words=%0d a_beats=%0d invalid_masks=%0d duplicate_tags=%0d busy_stalls=%0d",cycle,WORDS,CONTEXTS,shapes,numeric,feed_cycles,compute_cycles,a_words,a_beats,invalid_masks,duplicate_tags,busy_stalls);
  $display("A32_M_PASS numeric=%0d shapes=%0d seed=%0d",numeric,shapes,seed);$finish;
 end
endmodule
