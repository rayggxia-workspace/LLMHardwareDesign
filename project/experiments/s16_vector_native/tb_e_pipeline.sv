module tb_e_pipeline #(parameter integer PIPE=1);
 reg clk=0,reset=1;always #5 clk=~clk;
 reg iv=0,ready_out=0;wire ready_in,ov,oe,os;
 reg [3:0] op=0;reg [4:0] shift=0;reg [127:0] a=0,b=0,c=0;
 wire [127:0] result;
 generate if(PIPE!=0)begin: candidate
  block_v2_e_pipeline dut(.clk,.reset,.in_valid(iv),.in_ready(ready_in),.in_op(op),.in_shift(shift),
   .in_a(a),.in_b(b),.in_c(c),.out_valid(ov),.out_ready(ready_out),.out_data(result),.out_error(oe),.out_saturated(os));
 end else begin: baseline
  block_v2_e dut(.clk,.reset,.in_valid(iv),.in_ready(ready_in),.in_op(op),.in_shift(shift),
   .in_a(a),.in_b(b),.in_c(c),.out_valid(ov),.out_ready(ready_out),.out_data(result),.out_error(oe),.out_saturated(os));
 end endgenerate
 reg [522:0] vectors[0:4095];string path;
 integer sent=0,received=0,ticks=0,start_tick=0,last_tick=-1,max_live=0,stalls=0;
 integer consecutive=0,stage=0,epoch=0;
 reg active=0,held=0,accepted_input=0;reg [129:0] held_value;
 always @(posedge clk)begin
  ticks=ticks+1;
  accepted_input=!reset&&iv&&ready_in;
  if(!reset&&active)begin
   if(iv&&ready_in)begin
    if(last_tick>=0&&ticks-last_tick==1)consecutive++;
    last_tick=ticks;sent++;
   end
   if(held&&(!ov||{oe,os,result}!==held_value))$fatal(1,"held output changed");
   if(ov&&ready_out)begin
    if(received>=sent||{oe,os,result}!==vectors[received][129:0])
     $fatal(1,"numeric/order mismatch pipe=%0d idx=%0d got=%h expected=%h",PIPE,received,{oe,os,result},vectors[received][129:0]);
    received++;
   end
   held=ov&&!ready_out;held_value={oe,os,result};
   if(held)stalls++;
   if(sent-received>max_live)max_live=sent-received;
  end
 end
 initial begin
  if(!$value$plusargs("VECTORS=%s",path))$fatal(1,"missing vector file");
  $readmemh(path,vectors);
  repeat(4)@(negedge clk);reset=0;
  // Abort work in flight; no scoreboard entry may survive reset.
  iv=1;ready_out=0;op=2;a=128'hffff;b=128'h1234;
  do @(posedge clk);while(!ready_in);
  @(negedge clk);iv=0;repeat(2)@(negedge clk);reset=1;
  repeat(3)@(negedge clk);reset=0;ready_out=1;
  repeat(8)begin @(negedge clk);if(ov)$fatal(1,"ghost result after reset");end
  for(epoch=0;epoch<2;epoch++)begin
   sent=0;received=0;max_live=0;consecutive=0;last_tick=-1;stalls=0;held=0;start_tick=ticks;active=1;
   while(received<4096)begin
    // Drive at negative edges; preserve a stalled input until handshake.
    if(!iv||accepted_input)begin
     iv=sent<4096&&(epoch==0||ticks%7!=3);
     if(sent<4096)begin
      shift=vectors[sent][522:518];op=vectors[sent][517:514];
      a=vectors[sent][513:386];b=vectors[sent][385:258];c=vectors[sent][257:130];
     end
    end
    ready_out=epoch==0||(ticks%11>=4);
    @(negedge clk);
    if(ticks-start_tick>100000)$fatal(1,"pipeline timeout");
   end
   iv=0;active=0;ready_out=1;
   if(PIPE!=0&&epoch==0&&(consecutive!=4095||max_live!=4))$fatal(1,"II1/four-entry proof missing");
   if(epoch==1&&stalls==0)$fatal(1,"backpressure not exercised");
   $display("E_PIPE_MEASURE pipe=%0d epoch=%0d commands=%0d values=%0d cycles=%0d consecutive=%0d peak=%0d stalls=%0d",PIPE,epoch,received,received*8,ticks-start_tick,consecutive,max_live,stalls);
   repeat(5)begin @(negedge clk);if(ov)$fatal(1,"extra result after drain");end
  end
  $display("E_PIPE_PASS commands=8192 values=65536 reset=1");$finish;
 end
 initial begin #3000000;$fatal(1,"E watchdog");end
endmodule
