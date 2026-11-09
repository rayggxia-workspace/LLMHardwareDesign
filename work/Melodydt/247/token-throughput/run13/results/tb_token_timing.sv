// Whole native P, identical preloaded S and arithmetic in both schedules.
module tb_token_timing #(parameter integer BANK_RW=0, POLICY=0);
 logic clk=0,reset=1; always #5 clk=~clk;
 logic [1:0] io_req_valid=0,io_req_write=0,io_rsp_ready=0;
 logic [19:0] io_req_addr=0; logic [255:0] io_req_data=0;
 wire [1:0] io_req_ready,io_rsp_valid; wire [255:0] io_rsp_data;
 logic load_valid=0,load_take=0; logic [3:0] load_rows=3; logic [2:0] load_tiles=1; logic load_aw=1,load_bw=0;
 logic [9:0] load_a_base=0,load_b_base=64;
 wire load_ready,load_done,load_error;
 logic cmd_valid=0,cmd_store=0; logic [3:0] cmd_op=0;
 logic [5:0] cmd_index=0; logic [63:0] cmd_data=0; logic [9:0] cmd_dst=512;
 wire cmd_ready,cmd_done,cmd_error,cmd_saturated; wire [127:0] cmd_result;
 pu_p_group #(.S_CONSUMER_PRIORITY(POLICY),.S_BANK_RW(BANK_RW),.M_CONTEXTS(8)) dut(
  .clk,.reset,.io_req_valid,.io_req_write,.io_req_addr,.io_req_data,.io_req_ready,
  .io_rsp_valid,.io_rsp_ready,.io_rsp_data,
  .load_valid,.load_ready,.load_bank(1'b0),.load_rows,.load_tiles,
  .load_a_wide(load_aw),.load_b_wide(load_bw),.load_reuse_b(1'b0),.load_a_base,.load_b_base,
  .load_done,.load_take,.load_error,
  .cmd_valid,.cmd_ready,.cmd_op,.cmd_index,.cmd_data,.cmd_store,
  .cmd_route(1'b0),.cmd_pack16(1'b0),.cmd_dst,.cmd_done,.cmd_take(1'b1),.cmd_error,.cmd_saturated,.cmd_result,
  .gate_valid(1'b0),.gate_route(1'b0),.gate_ready(),.gate_a(10'd0),.gate_b(10'd0),.gate_dst(10'd0),
  .gate_done(),.gate_take(1'b1),.gate_error(),.gate_saturated(),
  .m_to_g_valid(),.m_to_g_data(),.m_to_g_take(1'b1),
  .g_from_m_valid(1'b0),.g_from_m_data(32'd0),.g_from_m_take());
 integer cycle=0,leaf_accept=-1,leaf_response=-1,prior_io_accept=-1,prior_cmd_accept=-1;
 integer a_count=0,b_count=0,wide_count=0,store_count=0,case_id=-1;
 bit previous_m_valid=0;
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(!reset) begin
   if(dut.m_dispatch&&dut.m_ready)leaf_accept=cycle+1;
   if(dut.a_valid&&dut.a_ready)a_count<=a_count+1;
   if(dut.b_valid&&dut.b_ready)b_count<=b_count+1;
   if(dut.store.wide_req&&dut.store.wide_ready)wide_count<=wide_count+1;
   if(dut.store_req&&dut.store_ready&&dut.store_write)store_count<=store_count+1;
  end
  if(cycle>100000)$fatal(1,"timing watchdog");
 end
 always @(negedge clk) begin
  if(dut.m_valid&&!previous_m_valid)leaf_response=cycle;
  previous_m_valid=dut.m_valid;
 end
 task automatic access(input bit wr,input integer addr,input logic [127:0] data,output logic [127:0] result,input bit report_it=0);
  integer accepted;
  @(negedge clk);while(!io_req_ready[0])@(negedge clk);
  io_req_valid=1;io_req_write={1'b0,wr};io_req_addr={10'd0,10'(addr)};io_req_data={128'd0,data};io_rsp_ready=1;
  @(posedge clk);if(!io_req_ready[0])$fatal(1,"IO admission");accepted=cycle+1;
  #1;io_req_valid=0;
  while(!io_rsp_valid[0])begin @(posedge clk);#1;end
  result=io_rsp_data[127:0];
  if(report_it)$display("CAL {\"kind\":\"io\",\"case\":%0d,\"write\":%0d,\"accepted\":%0d,\"done\":%0d,\"latency\":%0d,\"previous_accept\":%0d}",case_id,wr,accepted,cycle,cycle-accepted,prior_io_accept);
  prior_io_accept=accepted;
 endtask
 task automatic command(input integer op,index,input logic [63:0] data,input bit writes,output logic [127:0] result,input integer k=0,n=0,rows=0,aw=0,bw=0);
  integer accepted,before_stores;
  @(negedge clk);while(!cmd_ready)@(negedge clk);
  cmd_op=4'(op);cmd_index=6'(index);cmd_data=data;cmd_store=writes;cmd_valid=1;
  @(posedge clk);if(!cmd_ready)$fatal(1,"command admission");accepted=cycle+1;before_stores=store_count;
  #1;cmd_valid=0;
  while(!cmd_done)begin @(posedge clk);#1;end
  if(cmd_error)$fatal(1,"command error op=%0d index=%0d",op,index);
  result=cmd_result;
  $display("CAL {\"kind\":\"command\",\"case\":%0d,\"op\":%0d,\"index\":%0d,\"data_hex\":\"%016h\",\"scale_shift\":%0d,\"K\":%0d,\"N\":%0d,\"rows\":%0d,\"Awide\":%0d,\"Bwide\":%0d,\"store\":%0d,\"accepted\":%0d,\"done\":%0d,\"latency\":%0d,\"leaf_latency\":%0d,\"previous_accept\":%0d,\"stores\":%0d}",case_id,op,index,data,dut.context_mode.multiply.scale_shift,k,n,rows,aw,bw,writes,accepted,cycle,cycle-accepted,leaf_response-leaf_accept,prior_cmd_accept,store_count-before_stores);
  prior_cmd_accept=accepted;
 endtask
 task automatic load(input integer rows,tiles,input bit bw);
  integer accepted,ac,bc,wc;
  @(negedge clk);while(!load_ready)@(negedge clk);
  load_rows=4'(rows);load_tiles=3'(tiles);load_bw=bw;load_aw=1;load_valid=1;load_take=1;
  @(posedge clk);if(!load_ready)$fatal(1,"LOAD admission");accepted=cycle+1;ac=a_count;bc=b_count;wc=wide_count;
  #1;load_valid=0;
  while(!load_done)begin @(posedge clk);#1;end
  if(load_error)$fatal(1,"LOAD error");
  $display("CAL {\"kind\":\"load\",\"case\":%0d,\"rows\":%0d,\"tiles\":%0d,\"Bwide\":%0d,\"accepted\":%0d,\"done\":%0d,\"latency\":%0d,\"A\":%0d,\"B\":%0d,\"wide\":%0d}",case_id,rows,tiles,bw,accepted,cycle,cycle-accepted,a_count-ac,b_count-bc,wide_count-wc);
 endtask
 function automatic logic [63:0] desc(input integer k,n,rows,input bit bw);
  logic [63:0] x;begin
   x=0;x[0]=1;x[1]=bw;x[2]=1;x[7:4]=4'((k-1)%8+1);x[11:8]=4'(n);x[14:12]=3'((k+7)/8);x[18:15]=4'(rows);return x;
  end
 endfunction
 logic [127:0] word_data,got;
 logic [63:0] descriptor;
 logic signed [63:0] expected;
 integer kval[0:5];integer nval[0:2];integer k,n,tiles;
 initial begin
  kval[0]=1;kval[1]=7;kval[2]=8;kval[3]=9;kval[4]=31;kval[5]=32;
  nval[0]=1;nval[1]=5;nval[2]=8;
  repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);
  // Back-to-back acknowledged ordinary128 IO; every write has real readback.
  for(integer i=0;i<4;i++)begin
   access(1,900+i,128'(i+17),got,1);access(0,900+i,0,got,1);
   if(got!=128'(i+17))$fatal(1,"IO numerical readback");
  end
  // Operand A has three S16 rows (1,2,3) plus a genuine zero fourth slot.
  for(integer t=0;t<4;t++)for(integer r=0;r<4;r++)begin
   word_data=0;if(r<3)for(integer j=0;j<8;j++)word_data[16*j+:16]=16'(r+1);
   access(1,4*t+r,word_data,got);
  end
  for(integer bw=0;bw<2;bw++)begin
   for(integer w=0;w<(bw?32:16);w++)begin
    word_data=0;
    if(bw)for(integer j=0;j<8;j++)word_data[16*j+:16]=16'd1;
    else for(integer j=0;j<16;j++)word_data[8*j+:8]=8'd1;
    access(1,64+w,word_data,got);
   end
   for(integer test=0;test<6;test++)begin
    case_id=bw*6+test;k=kval[test];n=nval[test%3];tiles=(k+7)/8;
    command(6,0,0,0,got);
    load(3,tiles,1'(bw));
    command(4,0,1,0,got);
    command(10,0,desc(k,n,3,1'(bw)),0,got,k,n,3,1,bw);
    for(integer r=0;r<3;r++)for(integer pair=0;pair<4;pair++)begin
     command(3,r*8+pair,0,0,got);
     for(integer lane=0;lane<2;lane++)begin
      expected=pair*2+lane<n?64'(k*(r+1)):0;
      if($signed(got[lane*64+:64])!=expected)$fatal(1,"rows3 raw mismatch");
     end
    end
    command(6,0,0,0,got);load(3,tiles,1'(bw));
    // Three scale-aligned S16 limb executes share each actual B load.
    // All eight contexts remain live until each output is checked and ACKed.
    for(integer c=0;c<8;c++)begin
     if(c!=0)load(0,tiles,1'(bw));
     for(integer limb=0;limb<3;limb++)begin
      command(4,0,64'd1|(64'(15*limb)<<16),0,got);
      descriptor=desc(k,n,0,1'(bw));descriptor[2]=limb==0;descriptor[3]=limb==2;
      descriptor[17:15]=3'(limb);descriptor[33:18]=16'(limb*k);descriptor[49:34]=16'(100+c);
      command(13,c,descriptor,0,got,k,n,1,1,bw);
     end
    end
    for(integer c=0;c<8;c++)begin
     for(integer pair=0;pair<4;pair++)begin
      command(3,c*8+pair,0,0,got);
      for(integer lane=0;lane<2;lane++)begin
       expected=pair*2+lane<n?64'(k)*(64'd1+(64'd2<<15)+(64'd3<<30)):0;
       if($signed(got[lane*64+:64])!=expected)$fatal(1,"scale aligned raw mismatch");
      end
     end
     for(integer half=0;half<2;half++)begin
      cmd_dst=10'(512+c*2+half);command(5,c*8+half,64'h21e,1,got);
      // shift30, S32: lower limbs are <half, so each live result is 3*K.
      for(integer lane=0;lane<4;lane++)
       if($signed(got[lane*32+:32])!=(half*4+lane<n?3*k:0))$fatal(1,"final RNE mismatch");
     end
     command(14,c,64'(100+c)<<1,0,got);
    end
    for(integer c=0;c<8;c++)for(integer half=0;half<2;half++)begin
     access(0,512+c*2+half,0,got);
     for(integer lane=0;lane<4;lane++)
      if($signed(got[lane*32+:32])!=(half*4+lane<n?3*k:0))$fatal(1,"written output readback");
    end
   end
  end
  $display("PASS TOKEN_TIMING actual P, twelve cases, eight contexts, real write ACKs");
  $finish;
 end
endmodule
