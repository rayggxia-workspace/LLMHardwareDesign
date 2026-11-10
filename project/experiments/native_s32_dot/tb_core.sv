`timescale 1ns/1ps
module tb_core;
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset=1;
 reg in_valid=0;wire in_ready;
 reg [1:0] in_kind;reg [127:0] in_key;reg [31:0] in_tag;
 reg [15:0] in_full_k,in_k;reg in_group;reg [3:0] in_n;reg [5:0] in_shift;
 reg signed [31:0] in_a;reg [127:0] in_b;
 wire out_valid;reg out_ready;wire [1:0] out_kind;wire [127:0] out_key;
 wire [31:0] out_tag;wire out_error,out_done;wire [255:0] out_data;
 dot_s32_core dut(.*);
 reg [1:0] expected_kind[0:150000];reg [127:0] expected_key[0:150000];
 reg [31:0] expected_tag[0:150000];reg expected_error[0:150000],expected_done[0:150000];
 reg [255:0] expected_data[0:150000];
 integer tail,head,total_accept,total_response,held,cancel_wait,flushed,cycle;
 reg prior_held;reg [419:0] prior_packet;
 initial begin tail=0;head=0;total_accept=0;total_response=0;held=0;cancel_wait=0;flushed=0;cycle=0;prior_held=0;end
 reg source_error,source_done;reg [255:0] source_result;
 wire [419:0] packet={out_kind,out_key,out_tag,out_error,out_done,out_data};
 always @(negedge clk)begin out_ready=!reset && $urandom_range(0,3)!=0;end
 always @(posedge clk)begin
  cycle=cycle+1;
  if(reset)begin flushed=flushed+(tail-head);tail=0;head=0;prior_held=0;end
  else begin
   if(prior_held && (!out_valid || packet!==prior_packet))$fatal(1,"response changed under backpressure");
   prior_held=out_valid && !out_ready;prior_packet=packet;if(prior_held)held=held+1;
   if(in_valid && !in_ready && in_kind==2)cancel_wait=cancel_wait+1;
   if(in_valid && in_ready)begin
    expected_kind[tail]=in_kind;expected_key[tail]=in_key;expected_tag[tail]=in_tag;
    expected_error[tail]=source_error;expected_done[tail]=source_done;expected_data[tail]=source_result;
    tail=tail+1;total_accept=total_accept+1;
   end
   if(out_valid && out_ready)begin
    if(head>=tail || out_kind!==expected_kind[head] || out_key!==expected_key[head] ||
       out_tag!==expected_tag[head] || out_error!==expected_error[head] ||
       out_done!==expected_done[head] || out_data!==expected_data[head])begin
     $display("MISMATCH cycle=%0d index=%0d tag=%0d kind=%0d error=%0d done=%0d result=%064h expected=%064h",
       cycle,head,out_tag,out_kind,out_error,out_done,out_data,expected_data[head]);$fatal(1,"independent exact dot mismatch");
    end
    head=head+1;total_response=total_response+1;
   end
  end
 end
 string path;integer fd,got,action;reg [127:0] key;reg [31:0] tag,full,k,group,n,shift,a;
 reg [127:0] b;reg [31:0] error,done;reg [255:0] result;
 initial begin
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"vectors missing");
  fd=$fopen(path,"r");if(fd==0)$fatal(1,"vectors unreadable");
  repeat(4)@(negedge clk);reset=0;@(posedge clk);#1;
  while(!$feof(fd))begin
   got=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h\n",
     action,key,tag,full,k,group,n,shift,a,b,error,done,result);if(got!=13)$fatal(1,"vector format");
   if(full>65535 || k>65535 || group>1 || n>15 || shift>63 || error>1 || done>1)$fatal(1,"vector width");
   if(action==4)begin
    in_valid=0;reset=1;repeat(2)@(negedge clk);reset=0;@(posedge clk);#1;
   end else begin
    repeat($urandom_range(0,2))begin @(posedge clk);#1;end
    in_kind=2'(action);in_key=key;in_tag=tag;in_full_k=full[15:0];in_k=k[15:0];
    in_group=group[0];in_n=n[3:0];in_shift=shift[5:0];in_a=a;in_b=b;
    source_error=error[0];source_done=done[0];source_result=result;in_valid=1;
    do @(posedge clk);while(!in_ready);#1;in_valid=0;
   end
  end
  while(head!=tail || out_valid)begin @(posedge clk);#1;end
  if(flushed==0 || held==0 || cancel_wait==0)$fatal(1,"reset/held/cancel coverage missing");
  if(total_accept-total_response!=flushed)$fatal(1,"response conservation");
  $display("PASS native32 core accepted=%0d returned=%0d flushed=%0d held=%0d cancel_wait=%0d cycles=%0d",
    total_accept,total_response,flushed,held,cancel_wait,cycle);$finish;
 end
 initial begin #1000000000;$fatal(1,"core watchdog");end
endmodule
