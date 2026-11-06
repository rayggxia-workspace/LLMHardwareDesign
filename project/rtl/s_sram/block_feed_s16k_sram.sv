// Alternative to block_feed_s16k. Four real 256x128 1RW SRAM instances.
// Requests sample on rising edge K; SRAM finishes in the following low phase;
// the response is registered on rising edge K+1. Each response channel reserves
// two slots INCLUDING its in-flight operation. No SRAM response can be dropped.
module block_feed_s16k_sram #(
 parameter bit ECHO_WRITE_DATA=1'b1
) (
 input wire clk,reset,
 input wire req,wr,input wire [9:0] addr,input wire [127:0] din,
 output wire ready,valid,input wire take,output wire [127:0] dout,
 input wire wide_req,input wire [7:0] wide_addr,output wire wide_ready,
 output wire wide_valid,input wire wide_take,output wire [511:0] wide_dout
`ifdef USE_POWER_PINS
 ,inout wire vdd,gnd
`endif
);
 reg [127:0] narrow_q[0:1];reg [511:0] wide_q[0:1];
 reg nh,nt,wh,wt;reg [1:0] nc,wc;
 reg pending,p_wide,p_write;reg [1:0] p_bank;reg [127:0] p_data;
 assign valid=!reset&&(nc!=0);
 assign wide_valid=!reset&&(wc!=0);
 assign dout=narrow_q[nh];assign wide_dout=wide_q[wh];
 wire n_pop=valid&&take,w_pop=wide_valid&&wide_take;
 // The previous command returns unconditionally at this edge, even if the
 // downstream is stalled. Reserve capacity before accepting the command.
 wire [2:0] n_reserved={1'b0,nc}+{2'b0,(pending&&!p_wide)};
 wire [2:0] w_reserved={1'b0,wc}+{2'b0,(pending&&p_wide)};
 assign wide_ready=!reset&&((w_reserved<3'd2)||w_pop);
 wire w_fire=wide_req&&wide_ready;
 assign ready=!reset&&!w_fire&&((n_reserved<3'd2)||n_pop);
 wire n_fire=req&&ready;
 wire [7:0] bank_addr=w_fire?wide_addr:addr[9:2];
 wire [511:0] bank_dout;
 genvar bank;
 generate for(bank=0;bank<4;bank=bank+1)begin: banks
  wire selected=w_fire||(n_fire&&(addr[1:0]==2'(bank)));
  s_sram_256x128_freepdk45 memory(
   .clk0(clk),.csb0(!selected),.web0(!(n_fire&&wr)),
   .addr0(bank_addr),.din0(din),.dout0(bank_dout[128*bank+:128])
`ifdef USE_POWER_PINS
   ,.vdd(vdd),.gnd(gnd)
`endif
  );
 end endgenerate
 wire n_push=pending&&!p_wide,w_push=pending&&p_wide;
 always @(posedge clk)begin
  if(reset)begin
   nh<=0;nt<=0;wh<=0;wt<=0;nc<=0;wc<=0;
   pending<=0;p_wide<=0;p_write<=0;p_bank<=0;p_data<=0;
  end else begin
   if(n_push)begin
    narrow_q[nt]<=p_write?(ECHO_WRITE_DATA?p_data:128'b0):bank_dout[128*int'(p_bank)+:128];nt<=!nt;
   end
   if(w_push)begin wide_q[wt]<=bank_dout;wt<=!wt;end
   if(n_pop)nh<=!nh;
   if(w_pop)wh<=!wh;
   case({n_push,n_pop})
    2'b10:nc<=nc+1'b1;
    2'b01:nc<=nc-1'b1;
    default:begin end
   endcase
   case({w_push,w_pop})
    2'b10:wc<=wc+1'b1;
    2'b01:wc<=wc-1'b1;
    default:begin end
   endcase
   pending<=w_fire||n_fire;
   if(w_fire||n_fire)begin
    p_wide<=w_fire;p_write<=!w_fire&&wr;p_bank<=addr[1:0];p_data<=din;
   end
  end
 end
endmodule
