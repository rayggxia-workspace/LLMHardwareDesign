`timescale 1ns/1ps
module tb_dma_bridge;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,admit=1,protocol_error=0,req=0,wr=1,take=0,desc_ready=0,complete_valid=0,native_valid=0,native_take=0,native_write=1;
 reg [9:0] address=10'd1023;reg [127:0] data=128'hfedcba98765432100123456789abcdef,native_result;
 reg [140:0] context_i={8'h1,2'd1,3'd7,32'hffffffff,32'hfedcba98,32'h87654321,32'h80000001};
 wire ready,valid,desc_valid,desc_write,complete_ready,poison,busy;wire [127:0] result;wire [39:0] desc_address;wire [9:0] desc_local;
 wire [10:0] desc_words;wire [15:0] desc_tag;wire [140:0] context_o;
 reg [1:0] complete_status=0;reg [10:0] complete_words=1;reg [15:0] complete_tag;integer mode=0,n;
 raw16_dma_bridge #(.TAG_LIMIT(16'd2)) dut(.clk(clk),.reset(reset),.admit(admit),.protocol_error(protocol_error),
  .req(req),.wr(wr),.address(address),.data(data),.context_i(context_i),.external_read(40'hfedcba9810),.external_write(40'h8000000020),
  .ready(ready),.valid(valid),.take(take),.result(result),.desc_valid(desc_valid),.desc_ready(desc_ready),.desc_write(desc_write),
  .desc_address(desc_address),.desc_local(desc_local),.desc_words(desc_words),.desc_tag(desc_tag),.complete_valid(complete_valid),
  .complete_ready(complete_ready),.complete_status(complete_status),.complete_words(complete_words),.complete_tag(complete_tag),
  .native_valid(native_valid),.native_take(native_take),.native_write(native_write),.native_result(native_result),.context_o(context_o),.poison(poison),.busy(busy));
 task launch;
  begin
   @(negedge clk);req=1;@(posedge clk);if(!ready)$fatal(1,"bridge admission");@(negedge clk);req=0;
   repeat(5)begin
    if(!desc_valid||desc_local!=1023||desc_words!=1||desc_write==wr||context_o!==context_i||desc_address!==(wr?40'hfedcba9810:40'h8000000020))$fatal(1,"descriptor/context hold");
    @(negedge clk);
   end
   complete_tag=desc_tag;desc_ready=1;@(negedge clk);desc_ready=0;
  end
 endtask
 task native_ack;
  begin native_valid=1;native_take=1;native_write=wr;native_result=data;@(negedge clk);native_valid=0;native_take=0;end
 endtask
 task finish_service;
  begin
   complete_valid=1;@(negedge clk);complete_valid=0;
   repeat(7)begin if(!valid||result!==data||context_o!==context_i||ready)$fatal(1,"held mapped result");@(negedge clk);end
   take=1;@(negedge clk);take=0;
  end
 endtask
 initial begin
  n=$value$plusargs("MODE=%d",mode);repeat(3)@(negedge clk);reset=0;
  if(mode==1)wr=0;
  if(mode==9)begin admit=0;repeat(5)begin if(ready)$fatal(1,"admit gate");@(negedge clk);end admit=1;end
  launch;
  if(mode!=6)native_ack;
  case(mode)
   2:complete_tag=complete_tag+1'b1;
   3:complete_words=0;
   4:complete_status=3;
   5:protocol_error=1;
   7:begin native_ack;end
   default:begin end
  endcase
  if(mode>=2&&mode<=7)begin
   complete_valid=1;repeat(5)@(negedge clk);
   if(!poison||ready||valid||!busy)$fatal(1,"bad completion did not preserve owner and isolate");
  end else begin
   finish_service;
   if(mode==8)begin launch;native_ack;finish_service;req=1;repeat(3)@(negedge clk);if(!poison||ready||valid)$fatal(1,"tag exhaustion wrap");end
   else if(!ready||poison)$fatal(1,"successful service failed to release bridge");
  end
  $display("PASS bridge mode=%0d context=%0h",mode,context_o);$finish;
 end
 initial begin #10000;$fatal(1,"bridge watchdog");end
endmodule
