`timescale 1ns/1ps
// Two bounded DDR response slots, ordered SRAM commit, two writes in flight.
// No storage macro or external interface is added.
module s128_ddr_range_load (
    input logic clk, reset, cancel,
    input logic launch_valid,
    output logic launch_ready,
    input logic [63:0] launch_base,
    input logic [9:0] launch_s_base,
    input logic [8:0] launch_bursts,
    input logic launch_pair, launch_pair_beat, launch_pair_high,
    output logic done_valid, done_error,
    input logic done_ready,
    output logic rd_valid,
    input logic rd_ready,
    output logic [63:0] rd_address, rd_tag,
    input logic rd_rsp_valid, rd_rsp_error,
    output logic rd_rsp_ready,
    input logic [63:0] rd_rsp_tag,
    input logic [511:0] rd_rsp_data,
    output logic s_valid,
    input logic s_ready,
    output logic [9:0] s_address,
    output logic [127:0] s_data,
    output logic [31:0] s_tag,
    input logic s_rsp_valid, s_rsp_error,
    output logic s_rsp_ready,
    input logic [31:0] s_rsp_tag
);
 localparam IDLE=0,ACTIVE=1,REPORT=2;
 reg [1:0] state;
 reg [63:0] base;
 reg [9:0] s_base;
 reg [8:0] issued,retired;
 reg [8:0] bursts;
 reg pair,pair_beat,pair_high,stopped;
 reg read_held,write_held;
 reg [1:0] occupied,returned;
 reg [7:0] identity[0:1];
 reg [511:0] payload[0:1];
 reg [2:0] sent,acked;
 wire slot=retired[0];
 wire [2:0] words=pair?2:4;
 wire keep=!pair||retired[0]==pair_beat;
 wire [11:0] launch_words=launch_pair?12'd2:{1'b0,launch_bursts,2'b0};
 wire [64:0] launch_end={1'b0,launch_base}+{50'd0,launch_bursts,6'd0};
 wire legal=launch_base[5:0]==0&&launch_bursts!=0&&launch_bursts<=256&&launch_end<=(65'd1<<64)&&
  (!launch_pair||launch_bursts==2||(launch_bursts==1&&!launch_pair_beat))&&
  {2'b0,launch_s_base}+launch_words<=1024;
 wire match0=occupied[0]&&!returned[0]&&rd_rsp_tag=={56'd0,identity[0]};
 wire match1=occupied[1]&&!returned[1]&&rd_rsp_tag=={56'd0,identity[1]};
 wire ack=s_rsp_valid&&s_rsp_ready&&s_rsp_tag=={22'h12a000,ack_address};
 assign launch_ready=!reset&&state==IDLE;
 assign done_valid=!reset&&state==REPORT;
 assign rd_valid=!reset&&state==ACTIVE&&(read_held||(!done_error&&!stopped&&!cancel&&issued<bursts&&issued-retired<2));
 assign rd_address=base+{49'd0,issued,6'd0};
 assign rd_tag={55'd0,issued};
 assign rd_rsp_ready=!reset&&state==ACTIVE;
 assign s_valid=!reset&&state==ACTIVE&&(write_held||(occupied[slot]&&returned[slot]&&keep&&
  !done_error&&!stopped&&!cancel&&sent<words&&(sent-acked<2||ack)));
 assign s_address=s_base+(pair?{9'd0,sent[0]}:{retired[7:0],sent[1:0]});
 wire [1:0] lane=pair?{pair_high,sent[0]}:sent[1:0];
 assign s_data=payload[slot][lane*128+:128];
 assign s_tag={22'h12a000,s_address};
 assign s_rsp_ready=!reset&&state==ACTIVE&&acked<sent;
 wire [9:0] ack_address=s_base+(pair?{9'd0,acked[0]}:{retired[7:0],acked[1:0]});
 wire retire=state==ACTIVE&&!write_held&&occupied[slot]&&returned[slot]&&
   ((!keep&&sent==acked)||((done_error||stopped||cancel)&&sent==acked)||(keep&&acked==words));
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;base<=0;s_base<=0;issued<=0;retired<=0;bursts<=0;
   pair<=0;pair_beat<=0;pair_high<=0;occupied<=0;returned<=0;
   sent<=0;acked<=0;done_error<=0;stopped<=0;read_held<=0;write_held<=0;
   identity[0]<=0;identity[1]<=0;payload[0]<=0;payload[1]<=0;
  end else begin
   if(launch_valid&&launch_ready)begin
    base<=launch_base;s_base<=launch_s_base;bursts<=launch_bursts;
    pair<=launch_pair;pair_beat<=launch_pair_beat;pair_high<=launch_pair_high;
    issued<=0;retired<=0;occupied<=0;returned<=0;sent<=0;acked<=0;
    done_error<=!legal;stopped<=cancel;read_held<=0;write_held<=0;state<=legal?ACTIVE:REPORT;
   end
   if(state==ACTIVE&&cancel)stopped<=1;
   if(rd_valid)read_held<=!rd_ready;
   if(s_valid)write_held<=!s_ready;
   if(rd_valid&&rd_ready)begin
    occupied[issued[0]]<=1;returned[issued[0]]<=0;identity[issued[0]]<=issued[7:0];issued<=issued+1;
   end
   if(rd_rsp_valid&&rd_rsp_ready)begin
    if(match0)begin returned[0]<=1;payload[0]<=rd_rsp_data;if(rd_rsp_error)done_error<=1;end
    else if(match1)begin returned[1]<=1;payload[1]<=rd_rsp_data;if(rd_rsp_error)done_error<=1;end
    else done_error<=1; // Never retire an unreturned request on a bad/duplicate tag.
   end
   if(s_valid&&s_ready)sent<=sent+1;
   if(s_rsp_valid&&s_rsp_ready&&!ack)done_error<=1;
   if(ack)begin
    acked<=acked+1;
    if(s_rsp_error)done_error<=1;
   end
   if(retire)begin occupied[slot]<=0;returned[slot]<=0;retired<=retired+1;sent<=0;acked<=0;end
   if(state==ACTIVE&&!read_held&&!write_held&&retired==issued&&((issued==bursts)||done_error||stopped||cancel))state<=REPORT;
   if(done_valid&&done_ready)state<=IDLE;
  end
 end
endmodule
