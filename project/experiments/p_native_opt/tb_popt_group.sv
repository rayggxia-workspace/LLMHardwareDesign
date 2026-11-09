// Whole native P, identical preloaded S and arithmetic in both schedules.
module tb_popt_group #(parameter integer OPT=1, BANK_RW=0, SEGMENTS=2);
 logic clk=0,reset=1; always #5 clk=~clk;
 logic [1:0] io_req_valid=0,io_req_write=0,io_rsp_ready=0;
 logic [19:0] io_req_addr=0; logic [255:0] io_req_data=0;
 wire [1:0] io_req_ready,io_rsp_valid; wire [255:0] io_rsp_data;
 logic load_valid=0,load_take=0; logic [3:0] load_rows=1;
 logic [9:0] load_a_base=0,load_b_base=64;
 wire load_ready,load_done,load_error;
 logic cmd_valid=0,cmd_store=0; logic [3:0] cmd_op=0;
 logic [5:0] cmd_index=0; logic [63:0] cmd_data=0; logic [9:0] cmd_dst=512;
 wire cmd_ready,cmd_done,cmd_error,cmd_saturated; wire [127:0] cmd_result;
 pu_p_group #(.S_CONSUMER_PRIORITY(OPT),.S_BANK_RW(BANK_RW),.M_CONTEXTS(OPT?8:0)) dut(
  .clk,.reset,.io_req_valid,.io_req_write,.io_req_addr,.io_req_data,.io_req_ready,
  .io_rsp_valid,.io_rsp_ready,.io_rsp_data,
  .load_valid,.load_ready,.load_bank(1'b0),.load_rows,.load_tiles(3'd1),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base,.load_b_base,
  .load_done,.load_take,.load_error,
  .cmd_valid,.cmd_ready,.cmd_op,.cmd_index,.cmd_data,.cmd_store,
  .cmd_route(1'b0),.cmd_pack16(1'b0),.cmd_dst,.cmd_done,.cmd_take(1'b1),.cmd_error,.cmd_saturated,.cmd_result,
  .gate_valid(1'b0),.gate_route(1'b0),.gate_ready(),.gate_a(10'd0),.gate_b(10'd0),.gate_dst(10'd0),
  .gate_done(),.gate_take(1'b1),.gate_error(),.gate_saturated(),
  .m_to_g_valid(),.m_to_g_data(),.m_to_g_take(1'b1),
  .g_from_m_valid(1'b0),.g_from_m_data(32'd0),.g_from_m_take());
 integer cycle=0,a_count=0,b_count=0,wide_count=0,write_count=0,overlap_writes=0;
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(!reset) begin
   if(dut.a_valid&&dut.a_ready)a_count<=a_count+1;
   if(dut.b_valid&&dut.b_ready)b_count<=b_count+1;
   if(dut.store.wide_req&&dut.store.wide_ready)wide_count<=wide_count+1;
   if(dut.store_req&&dut.store_ready&&dut.store_write)write_count<=write_count+1;
   if(dut.store_req&&dut.store_ready&&dut.store_write&&dut.store_control.feeder_active)
    overlap_writes<=overlap_writes+1;
  end
  if(cycle>50000)$fatal(1,"group watchdog");
 end
 function automatic integer aval(input integer segment,k);
  return (segment*5+k)%13-6;
 endfunction
 function automatic integer bval(input integer group_id,n,k);
  return (group_id*3+n*2+k)%15-7;
 endfunction
 function automatic integer gold(input integer group_id,n);
  integer total,q,r; begin
   total=0;
   if(n<5)begin
    for(integer s=0;s<SEGMENTS;s++)
     for(integer k=0;k<(s==SEGMENTS-1?3:8);k++)total+=aval(s,k)*bval(group_id,n,k);
   end
   q=total>>>2;r=total-q*4;
   if(r>2||(r==2&&(q&1)))q++;
   return q;
  end
 endfunction
 task automatic access(input bit wr,input integer addr,input logic [127:0] data,output logic [127:0] result);
  @(negedge clk);io_req_valid=1;io_req_write={1'b0,wr};io_req_addr={10'd0,10'(addr)};io_req_data={128'd0,data};
  do @(posedge clk);while(!io_req_ready[0]);
  @(negedge clk);io_req_valid=0;
  repeat(2)@(negedge clk);io_rsp_ready=1;
  do @(posedge clk);while(!io_rsp_valid[0]);
  result=io_rsp_data[127:0];
  @(negedge clk);io_rsp_ready=0;
 endtask
 task automatic load(input integer segment,group_id,input bit reuse_a,input bit expect_error=0);
  @(negedge clk);load_a_base=10'(segment*4);load_b_base=10'(64+segment*32+group_id*4);
  load_rows=reuse_a?0:1;load_valid=1;
  do @(posedge clk);while(!load_ready);
  @(negedge clk);load_valid=0;
  do @(posedge clk);while(!load_done);
  if(load_error!==expect_error)$fatal(1,"LOAD error rows=%0d",load_rows);
  repeat(2)@(negedge clk);load_take=1;
  @(negedge clk);load_take=0;
 endtask
 task automatic command(input integer op,index,input logic [63:0] data,input bit writes=0,input bit expect_error=0);
  @(negedge clk);cmd_op=4'(op);cmd_index=6'(index);cmd_data=data;cmd_store=writes;cmd_valid=1;
  do @(posedge clk);while(!cmd_ready);
  @(negedge clk);cmd_valid=0;
  do @(posedge clk);while(!cmd_done);
  if(cmd_error!==expect_error)$fatal(1,"command error op=%0d index=%0d data=%h",op,index,data);
 endtask
 task automatic segment_run(input integer segment,group_id);
  logic [63:0] desc;
  begin
   desc=0;desc[7:4]=segment==SEGMENTS-1?3:8;desc[11:8]=5;desc[14:12]=1;desc[2]=segment==0;
   if(OPT)begin
    desc[3]=segment==SEGMENTS-1;desc[33:18]=16'(segment*8);desc[49:34]=16'(100+group_id);
    command(13,group_id,desc);
   end else begin desc[18:15]=1;command(10,0,desc);end
  end
 endtask
 logic [127:0] word_data,got;
 integer start_cycle,start_writes,overlap_before,output_cycles;
 task automatic output_group(input integer g);
  for(integer half=0;half<2;half++)begin
   cmd_dst=10'(512+g*2+half);
   command(5,(OPT?g*8:0)+half,64'h102,1);
  end
 endtask
 initial begin
  repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);
  // Same S contents, addresses and native B work in both schedules.
  if(SEGMENTS!=2&&SEGMENTS!=8)$fatal(1,"supported paired segment counts are 2 and 8");
  for(integer s=0;s<SEGMENTS;s++)begin
   for(integer part=0;part<4;part++)begin
    word_data=0;
    if(part==0)for(integer k=0;k<8;k++)word_data[8*k+:8]=8'(aval(s,k));
    access(1,s*4+part,word_data,got);
   end
   for(integer g=0;g<8;g++)for(integer part=0;part<4;part++)begin
    word_data=0;
    for(integer n=0;n<2;n++)for(integer k=0;k<8;k++)
     word_data[8*(n*8+k)+:8]=8'(bval(g,part*2+n,k));
    access(1,64+s*32+g*4+part,word_data,got);
   end
  end
  start_cycle=cycle;start_writes=write_count;
  if(OPT)begin
   for(integer s=0;s<SEGMENTS;s++)for(integer g=0;g<8;g++)begin load(s,g,g!=0);segment_run(s,g);end
   for(integer g=0;g<8;g++)output_group(g);
  end else begin
   for(integer g=0;g<8;g++)begin
    for(integer s=0;s<SEGMENTS;s++)begin load(s,g,0);segment_run(s,g);end
    output_group(g);
   end
  end
  output_cycles=cycle-start_cycle;
  // Context ownership is not reusable until release. Include its actual
  // P command/response cost in the headline measurement, separately from
  // the useful prefix ending at the last real S write ACK.
  if(OPT)for(integer g=0;g<8;g++)command(14,g,64'(100+g)<<1);
  $display("METRIC P_GROUP opt=%0d bank_rw=%0d segments=%0d cycles=%0d output_cycles=%0d release_cycles=%0d A=%0d B=%0d wide=%0d stores=%0d",OPT,BANK_RW,SEGMENTS,cycle-start_cycle,output_cycles,cycle-start_cycle-output_cycles,a_count,b_count,wide_count,write_count-start_writes);
  if(a_count!=(OPT?SEGMENTS:SEGMENTS*8)||b_count!=SEGMENTS*8||wide_count!=(OPT?SEGMENTS*9:SEGMENTS*16)||write_count-start_writes!=16)
   $fatal(1,"native work accounting");
  for(integer g=0;g<8;g++)for(integer half=0;half<2;half++)begin
   access(0,512+g*2+half,0,got);
   for(integer lane=0;lane<4;lane++)
    if($signed(got[32*lane+:32])!=gold(g,half*4+lane))
     $fatal(1,"gold mismatch g=%0d lane=%0d got=%h expected=%0d",g,half*4+lane,got,gold(g,half*4+lane));
  end
  if(OPT)begin
   command(3,0,0,0,1); // Released data is not readable.
  end else begin
   load(0,0,1,1); // Optional B-only encoding remains illegal by default.
   command(13,0,0,0,1);
  end
  // Verify the outer P/store-control wiring, separately from the matched
  // arithmetic timing above. Use eight A rows to sustain the feeder lease.
  overlap_before=overlap_writes;
  fork
   begin
    @(negedge clk);load_rows=8;load_a_base=0;load_b_base=64;load_valid=1;
    do @(posedge clk);while(!load_ready);
    @(negedge clk);load_valid=0;
    do @(posedge clk);while(!load_done);
    if(load_error)$fatal(1,"overlap probe LOAD failed");
    @(negedge clk);load_take=1;
    @(negedge clk);load_take=0;
   end
   begin
    wait(dut.store_control.feeder_active);
    for(integer q=0;q<8;q++)access(1,700+q,128'(1000+q),got);
   end
  join
  if((BANK_RW&&overlap_writes==overlap_before)||(!BANK_RW&&overlap_writes!=overlap_before))
   $fatal(1,"outer P concurrent admission mismatch");
  for(integer q=0;q<8;q++)begin
   access(0,700+q,0,got);
   if(got!==128'(1000+q))$fatal(1,"overlap probe readback");
  end
  $display("P_GROUP_OVERLAP bank_rw=%0d accepted_while_feeder_active=%0d",BANK_RW,overlap_writes-overlap_before);
  @(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;repeat(8)@(negedge clk);
  if(io_rsp_valid||load_done||cmd_done)$fatal(1,"stale event after reset");
  command(3,0,0,0,1);
  $display("PASS P_GROUP native S, B-only, context/legacy, final RNE, S write ACK/readback, reset");$finish;
 end
endmodule
