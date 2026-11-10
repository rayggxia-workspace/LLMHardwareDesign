module tb_closure_banks #(parameter integer BANKS=4);
 reg clk;initial clk=0;always #5 clk=~clk;
 reg reset=1,cmd_valid=0,cmd_release=0,cmd_long=0,fill_valid=0,read_valid=0,out_ready=0;
 reg [2:0] cmd_bank=0,fill_bank=0,read_bank=0,read_index=0;
 reg [15:0] cmd_generation=0,fill_generation=0,read_generation=0;
 reg [4:0] fill_index=0;reg [511:0] fill_data=0;
 wire cmd_ready,fill_ready,read_ready,out_valid,fault;
 wire [1023:0] out_data;wire [1023:0] out_scales;wire [2:0] out_bank,out_index;wire [15:0] out_generation;
 closure_weight_banks #(.BANKS(BANKS)) dut(.*);
 function automatic [511:0] pattern(input integer bank_id,beat_id,gen);
  for(integer w=0;w<16;w=w+1)pattern[w*32+:32]=32'(gen*100000+bank_id*1000+beat_id*16+w);
 endfunction
 integer checks=0;
 initial begin
  repeat(3)@(negedge clk);reset=0;
  for(integer gen=1;gen<=3;gen=gen+1)begin
   for(integer b=0;b<BANKS;b=b+1)begin
    cmd_bank=3'(b);cmd_generation=16'(gen);cmd_long=1'(gen%2);cmd_valid=1;@(posedge clk);
    if(!cmd_ready)$fatal(1,"allocation backpressure");@(negedge clk);cmd_valid=0;
   end
   // Deliberately interleave record fills across all finite banks.
   for(integer i=(gen%2!=0?17:16);i>=0;i=i-1)for(integer b=0;b<BANKS;b=b+1)begin
    fill_bank=3'(b);fill_generation=16'(gen);fill_index=5'(i);fill_data=pattern(b,i,gen);fill_valid=1;
    @(posedge clk);if(!fill_ready)$fatal(1,"fill");@(negedge clk);fill_valid=0;
    if(i%3==0)@(negedge clk);
   end
   for(integer i=0;i<8;i=i+1)for(integer b=0;b<BANKS;b=b+1)begin
    read_bank=3'(b);read_generation=16'(gen);read_index=3'(i);read_valid=1;
    @(posedge clk);if(!read_ready)$fatal(1,"read");@(negedge clk);read_valid=0;
    repeat((i+b)%4+1)begin
     if(!out_valid||out_data!=={pattern(b,2*i+1,gen),pattern(b,2*i,gen)}||
        out_scales!=={gen%2!=0?pattern(b,17,gen):512'd0,pattern(b,16,gen)}||out_bank!==3'(b)||out_index!==3'(i)||out_generation!==16'(gen)||fault)$fatal(1,"read payload/hold");
     @(negedge clk);
    end
    out_ready=1;@(posedge clk);@(negedge clk);out_ready=0;checks=checks+1;
   end
   for(integer b=0;b<BANKS;b=b+1)begin
    cmd_bank=3'(b);cmd_generation=16'(gen);cmd_release=1;cmd_valid=1;
    @(posedge clk);@(negedge clk);cmd_valid=0;cmd_release=0;if(fault)$fatal(1,"release");
   end
  end
  // A late response into a retired record must be rejected.
  fill_valid=1;@(posedge clk);@(negedge clk);fill_valid=0;if(!fault)$fatal(1,"late fill accepted");
  reset=1;repeat(3)@(negedge clk);reset=0;if(fault||out_valid)$fatal(1,"reset");
  $display("WEIGHT_BANK_PASS banks=%0d checks=%0d",BANKS,checks);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
