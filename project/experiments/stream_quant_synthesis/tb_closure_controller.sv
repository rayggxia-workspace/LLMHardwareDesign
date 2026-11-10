module tb_closure_controller;
 reg clk; initial clk=0;
 reg reset=1,cmd_valid=0,part_valid=0,done_ready=0;
 wire cmd_ready,part_ready,rd_valid,rd_rsp_ready,wr_valid,wr_ack_ready,done_valid,done_error,fault;
 reg [13:0] cmd_address=0;reg [15:0] cmd_generation=0,part_generation=0;
 reg cmd_first=0;reg [3:0] cmd_count=0;reg [87:0] cmd_mantissa=0;reg [55:0] cmd_shift=0;reg [319:0] part_data=0;
 wire rd_ready,rd_rsp_valid;reg [15:0] rd_rsp_generation;reg [1023:0] rd_rsp_data;
 wire wr_ready,wr_ack_valid;reg [15:0] wr_ack_generation;
 wire [13:0] rd_address,wr_address;wire [15:0] rd_generation,wr_generation,done_generation;wire [1023:0] wr_data;
 reg [1023:0] memory[0:127];
 closure_psum_controller dut(.*);
 always #5 clk=~clk;
 integer tick,read_wait,write_wait,writes;
 assign rd_ready=!reset&&(tick%5!=0);assign wr_ready=!reset&&(tick%7!=0);
 assign rd_rsp_valid=!reset&&read_wait==0;assign wr_ack_valid=!reset&&write_wait==0;
 always @(posedge clk)begin
  if(reset)begin tick<=0;read_wait<=-1;write_wait<=-1;writes<=0;rd_rsp_data<=0;rd_rsp_generation<=0;wr_ack_generation<=0;end
  else begin
   tick<=tick+1;
   if(read_wait>0)read_wait<=read_wait-1;
   if(write_wait>0)write_wait<=write_wait-1;
   if(rd_valid&&rd_ready)begin
    if(rd_address[6:0]!=0)$fatal(1,"read alignment");
    rd_rsp_data<=memory[rd_address[13:7]];rd_rsp_generation<=rd_generation;read_wait<=3+tick%8;
   end
   if(rd_rsp_valid&&rd_rsp_ready)read_wait<=-1;
   if(wr_valid&&wr_ready)begin
    if(wr_address[6:0]!=0)$fatal(1,"write alignment");
    memory[wr_address[13:7]]<=wr_data;wr_ack_generation<=wr_generation;write_wait<=3+tick%9;writes<=writes+1;
   end
   if(wr_ack_valid&&wr_ack_ready)write_wait<=-1;
  end
 end
 integer fd,rc,count,error,checks=0,start,minimum=99999,maximum=0,writes_before;
 reg [319:0] partial;reg [87:0] mantissa;reg [55:0] shift;reg [1023:0] previous,expected;
 initial begin
  repeat(3)@(negedge clk);reset=0;
  fd=$fopen("partial-vectors.txt","r");if(fd==0)$fatal(1,"vectors");
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %h %h %h %h %h %d\n",count,partial,mantissa,shift,previous,expected,error);
   if(rc!=7||count<1||count>8||(error!=0&&error!=1))$fatal(1,"format");
   @(negedge clk);cmd_address=14'(128*(checks%86));memory[checks%86]=previous;
   cmd_generation=16'(checks+1);cmd_count=4'(count);cmd_mantissa=mantissa;cmd_shift=shift;cmd_valid=1;
   start=tick;writes_before=writes;
   do @(posedge clk);while(!cmd_ready);
   @(negedge clk);cmd_valid=0;
   repeat(checks%11)@(negedge clk);
   part_data=partial;part_generation=cmd_generation;part_valid=1;
   do @(posedge clk);while(!part_ready);
   @(negedge clk);part_valid=0;
   do @(negedge clk);while(!done_valid);
   if(done_error!==1'(error)||done_generation!==cmd_generation)$fatal(1,"completion %0d",checks);
   if(error==0&&(memory[checks%86]!==expected||writes!=writes_before+1))$fatal(1,"stored result %0d",checks);
   if(error!=0&&(!fault||writes!=writes_before))$fatal(1,"fault committed %0d",checks);
   if(tick-start<minimum)minimum=tick-start;if(tick-start>maximum)maximum=tick-start;
   repeat(checks%4+1)begin
    if(!done_valid||cmd_ready)$fatal(1,"ownership released before done ACK");@(negedge clk);
   end
   done_ready=1;@(posedge clk);@(negedge clk);done_ready=0;
   if(error!=0)begin reset=1;repeat(3)@(negedge clk);reset=0;end
   checks=checks+1;
  end
  $display("PSUM_CONTROLLER_PASS checks=%0d min=%0d max=%0d",checks,minimum,maximum);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
