// Dedicated fixed8x512 SiLU/whole-row quantization. All arithmetic/control is RTL.
module vprep97(input wire clk,reset,start,ack,input wire [31:0] gateup_address,
 output wire busy,done,output reg [7:0] status,output wire [7:0] debug_state,
 output wire ereq,output wire [31:0] eaddr,input wire eready,evalid,output wire etake,input wire [127:0] edata,
 output wire sreq,swr,output wire [9:0] saddr,output wire [127:0] sdata,input wire sready,svalid,output wire stake,input wire [127:0] sdout,
 output wire mul_req,output wire signed [31:0] mul_a,mul_b,input wire mul_ready,mul_valid,output wire mul_take,input wire signed [63:0] mul_value,
 output reg [127:0] deltas,output reg [7:0] expert_valid,
 output reg [63:0] cycles,output reg [31:0] gate_reads,up_reads,lut_reads,store_reads,store_writes,
 output reg obs_mid_valid,obs_a_valid,output reg [11:0] obs_index,output reg signed [31:0] obs_mid,output reg signed [7:0] obs_a);
 localparam IDLE=0,GR=1,GW=2,UR=3,UW=4,LOOK=5,LR=6,LW=7,MR=8,MW=9,MSTORE=10,MSWAIT=11,SCALE=12,QR=13,QW=14,QUANT=15,ASTORE=16,ASWAIT=17,DONE=18;
 reg [7:0] state;reg [31:0] base;reg [2:0] rank;reg [8:0] index;reg [4:0] delta;
 reg [127:0] gline,uline,midline,qline,aline;reg signed [31:0] activated;reg [14:0] lut_index;reg [31:0] absmax;
 wire signed [31:0] gate=gline[32*index[1:0]+:32],up=uline[32*index[1:0]+:32],mid=qline[32*index[1:0]+:32];
 wire [31:0] grid=$unsigned(gate)+32'd131072;wire [31:0] lut_rounded=(grid>>4)+((grid[3:0]>8)||((grid[3:0]==8)&&grid[4]));
 function signed [63:0] rne(input signed [63:0] v,input [5:0] shift);
 reg [63:0] mag,q,rem,half;
 begin mag=v[63]?-v:v;if(shift==0)rne=v;else begin q=mag>>shift;rem=mag-(q<<shift);half=64'd1<<(shift-1);q=q+((rem>half)||((rem==half)&&q[0]));rne=v[63]?-$signed(q):$signed(q);end end endfunction
 wire signed [63:0] mid64=rne(mul_value,6'd12),probe=rne($signed({32'b0,absmax}),{1'b0,delta}),a64=rne({{32{mid[31]}},mid},{1'b0,delta});
 wire [31:0] midmag=mid64[31]?-mid64[31:0]:mid64[31:0];
 assign busy=state!=IDLE;assign done=state==DONE;assign debug_state=state;
 assign ereq=state==GR||state==UR||state==LR;assign etake=state==GW||state==UW||state==LW;
 assign eaddr=state==LR?32'h02000000+{15'b0,lut_index[14:2],4'b0}:base+{17'b0,rank,12'b0}+(state==UR?32'd2048:0)+{21'b0,index[8:2],4'b0};
 assign sreq=state==MSTORE||state==QR||state==ASTORE;assign swr=state!=QR;
 assign saddr=state==ASTORE?10'd768+{2'b0,rank,5'b0}+{5'b0,index[8:4]}:{3'b0,index[8:2]};
 assign sdata=state==ASTORE?aline:midline;assign stake=state==MSWAIT||state==QW||state==ASWAIT;
 assign mul_req=state==MR;assign mul_a=activated;assign mul_b=up;assign mul_take=state==MW;
 always @(posedge clk)begin
 if(reset)begin state<=IDLE;status<=0;base<=0;rank<=0;index<=0;delta<=0;gline<=0;uline<=0;midline<=0;qline<=0;aline<=0;activated<=0;lut_index<=0;absmax<=0;deltas<=0;expert_valid<=0;cycles<=0;gate_reads<=0;up_reads<=0;lut_reads<=0;store_reads<=0;store_writes<=0;obs_mid_valid<=0;obs_a_valid<=0;obs_index<=0;obs_mid<=0;obs_a<=0;end
 else begin
 obs_mid_valid<=0;obs_a_valid<=0;if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
 case(state)
 IDLE:if(start)begin state<=GR;status<=0;base<=gateup_address;rank<=0;index<=0;delta<=0;absmax<=0;deltas<=0;expert_valid<=0;cycles<=0;gate_reads<=0;up_reads<=0;lut_reads<=0;store_reads<=0;store_writes<=0;end
 GR:if(eready)begin gate_reads<=gate_reads+1;state<=GW;end
 GW:if(evalid)begin gline<=edata;state<=UR;end
 UR:if(eready)begin up_reads<=up_reads+1;state<=UW;end
 UW:if(evalid)begin uline<=edata;state<=LOOK;end
 LOOK:if(gate< -32'sd131072)begin activated<=0;state<=MR;end else if(gate>32'sd131072)begin activated<=gate;state<=MR;end else if(lut_rounded>16384)begin status<=32;state<=DONE;end else begin lut_index<=lut_rounded[14:0];state<=LR;end
 LR:if(eready)begin lut_reads<=lut_reads+1;state<=LW;end
 LW:if(evalid)begin activated<=edata[32*lut_index[1:0]+:32];state<=MR;end
 MR:if(mul_ready)state<=MW;
 MW:if(mul_valid)begin
  if(mid64>64'sd2147483647||mid64< -64'sd2147483648)begin status<=33;state<=DONE;end
  else begin midline[32*index[1:0]+:32]<=mid64[31:0];if(midmag>absmax)absmax<=midmag;obs_mid_valid<=1;obs_mid<=mid64[31:0];obs_index<={rank,index};if(index[1:0]==3)state<=MSTORE;else begin index<=index+1;state<=LOOK;end end
 end
 MSTORE:if(sready)begin store_writes<=store_writes+1;state<=MSWAIT;end
 MSWAIT:if(svalid)begin if(index==511)begin delta<=0;state<=SCALE;end else begin index<=index+1;state<=GR;end end
 SCALE:if(probe<=127)begin index<=0;state<=QR;end else if(delta==25)begin status<=34;state<=DONE;end else delta<=delta+1;
 QR:if(sready)begin store_reads<=store_reads+1;state<=QW;end
 QW:if(svalid)begin qline<=sdout;state<=QUANT;end
 QUANT:if(a64>127||a64< -127)begin status<=35;state<=DONE;end else begin aline[8*index[3:0]+:8]<=a64[7:0];obs_a_valid<=1;obs_a<=a64[7:0];obs_index<={rank,index};if(index[3:0]==15)state<=ASTORE;else begin index<=index+1;state<=index[1:0]==3?QR:QUANT;end end
 ASTORE:if(sready)begin store_writes<=store_writes+1;state<=ASWAIT;end
 ASWAIT:if(svalid)begin if(index==511)begin deltas[16*rank+:16]<={11'b0,delta};expert_valid[rank]<=1;if(rank==7)state<=DONE;else begin rank<=rank+1;index<=0;absmax<=0;delta<=0;state<=GR;end end else begin index<=index+1;state<=QR;end end
 DONE:if(ack)state<=IDLE;
 default:begin status<=255;state<=DONE;end
 endcase end end
endmodule
