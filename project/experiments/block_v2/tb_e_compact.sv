module tb_e_compact;
 logic clk=0, reset=1;
 always #5 clk=~clk;
 logic in_valid=0, in_ready, gold_valid=0, gold_ready;
 logic out_ready=0, out_valid, ref_valid, out_error, ref_error, out_sat, ref_sat;
 logic [3:0] op;
 logic [4:0] shift;
 logic [127:0] data, a, b, c, result, expected;

 block_v2_e_compact dut(clk,reset,in_valid,in_ready,op,shift,data,out_valid,out_ready,result,out_error,out_sat);
 block_v2_e reference(clk,reset,gold_valid,gold_ready,op,shift,a,b,c,ref_valid,out_ready,expected,ref_error,ref_sat);

 task automatic send(input logic [127:0] operand);
  @(negedge clk);
  in_valid=1;
  data=operand;
  do @(posedge clk); while (!in_ready);
  @(negedge clk);
  in_valid=0;
 endtask

 initial begin
  repeat(2) @(negedge clk);
  reset=0;
  op=3;
  shift=0;
  send('1);
  reset=1;
  @(negedge clk);
  reset=0;
  for(int i=0;i<512;i++) begin
   @(negedge clk);
   op=4'(i);
   shift=5'(i/16);
   a={$urandom,$urandom,$urandom,$urandom};
   b={$urandom,$urandom,$urandom,$urandom};
   c={$urandom,$urandom,$urandom,$urandom};
   gold_valid=1;
   @(posedge clk);
   if(!gold_ready) $fatal(1,"reference did not accept");
   @(negedge clk);
   gold_valid=0;
   send(a);
   if(op<7 || op==9) send(b);
   if(op==3 || op==6) send(c);
   wait(out_valid && ref_valid);
   repeat(3) begin
    @(negedge clk);
    if(!out_valid || !ref_valid || {out_error,out_sat,result} !== {ref_error,ref_sat,expected})
     $fatal(1,"mismatch at vector %0d opcode %0d shift %0d",i,op,shift);
   end
   out_ready=1;
   @(negedge clk);
   out_ready=0;
  end
  $display("PASS compact E: 512 exact reference results, partial reset and held output");
  $finish;
 end

 initial begin
  #300000;
  $fatal(1,"timeout");
 end
endmodule
