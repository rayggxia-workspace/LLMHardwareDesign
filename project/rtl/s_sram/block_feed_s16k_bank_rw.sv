// Fixed 16KiB: four real 256x128 1RW macros. At most one physical operation
// per bank per edge. Wide reads gather all free banks, then any missing bank.
// An ordinary access can overlap only on a bank not used by that read beat.
module block_feed_s16k_bank_rw #(parameter bit ECHO_WRITE_DATA=1'b1) (
 input wire clk,reset,
 input wire req,wr,input wire [9:0] addr,input wire [127:0] din,
 output wire ready,valid,input wire take,output wire [127:0] dout,
 input wire wide_req,input wire [7:0] wide_addr,output wire wide_ready,
 output wire wide_valid,input wire wide_take,output wire [511:0] wide_dout
`ifdef USE_POWER_PINS
 ,inout wire vdd,gnd
`endif
);
 reg [127:0] narrow_q[0:1];
 reg nh,nt;reg [1:0] nc;
 reg n_pending,p_write;reg [1:0] p_bank;reg [127:0] p_data;
 reg w_active,w_valid;reg [7:0] w_line;
 reg [3:0] w_remaining,p_w_mask;
 reg [511:0] w_data;
 reg prefer_n;
 assign valid=!reset&&nc!=0;assign dout=narrow_q[nh];
 assign wide_valid=!reset&&w_valid;assign wide_dout=w_data;
 wire n_pop=valid&&take,w_pop=wide_valid&&wide_take;
 wire [2:0] n_reserved={1'b0,nc}+{2'b0,n_pending};
 wire n_capacity=(n_reserved<3'd2)||n_pop;
 assign wide_ready=!reset&&!w_active&&(!w_valid||w_pop);
 wire w_start=wide_req&&wide_ready;
 wire [3:0] w_want=reset?4'b0000:(w_start?4'b1111:(w_active?w_remaining:4'b0000));
 wire [7:0] read_line=w_start?wide_addr:w_line;
 // Preserve the atomic 512-bit line snapshot across a split gather. Writes
 // may resume after all fragments have been captured, even if its reply stalls.
 wire write_locked=wr&&(w_active||w_start)&&addr[9:2]==read_line;
 wire n_candidate=!reset&&req&&n_capacity&&!write_locked;
 wire conflict=n_candidate&&w_want[addr[1:0]];
 // An unfinished gather wins its last bank, bounding physical issue to two
 // beats. A fresh gather alternates with ordinary access on a collision.
 wire n_wins=conflict&&!w_active&&prefer_n;
 wire deny_n=(|w_want)&&w_want[addr[1:0]]&&(!n_candidate||!n_wins);
 assign ready=!reset&&n_capacity&&!write_locked&&!deny_n;
 wire n_fire=req&&ready;
 wire [3:0] n_mask=n_fire?(4'b0001<<addr[1:0]):4'b0000;
 wire [3:0] w_issue_mask=w_want&~n_mask;
 wire [511:0] bank_dout;
 for(genvar bank=0;bank<4;bank=bank+1)begin: banks
  wire n_selected=n_fire&&addr[1:0]==2'(bank);
  wire selected=n_selected||w_issue_mask[bank];
  wire [7:0] bank_addr=n_selected?addr[9:2]:read_line;
  s_sram_256x128_freepdk45 memory(
   .clk0(clk),.csb0(!selected),.web0(!(n_selected&&wr)),
   .addr0(bank_addr),.din0(din),.dout0(bank_dout[128*bank+:128])
`ifdef USE_POWER_PINS
   ,.vdd(vdd),.gnd(gnd)
`endif
  );
 end
 always @(posedge clk)begin
  if(reset)begin
   nh<=0;nt<=0;nc<=0;n_pending<=0;p_write<=0;p_bank<=0;p_data<=0;
   w_active<=0;w_valid<=0;w_line<=0;w_remaining<=0;p_w_mask<=0;w_data<=0;prefer_n<=1;
  end else begin
   if(n_pending)begin
    narrow_q[nt]<=p_write?(ECHO_WRITE_DATA?p_data:128'b0):bank_dout[128*int'(p_bank)+:128];
    nt<=!nt;
   end
   if(n_pop)nh<=!nh;
   case({n_pending,n_pop})
    2'b10:nc<=nc+1'b1;
    2'b01:nc<=nc-1'b1;
    default:begin end
   endcase
   n_pending<=n_fire;
   if(n_fire)begin p_write<=wr;p_bank<=addr[1:0];p_data<=din;end
   if(w_pop)w_valid<=0;
   if(w_start)begin
    w_active<=1;w_line<=wide_addr;w_remaining<=4'b1111&~w_issue_mask;w_data<=0;
   end else if(w_active)w_remaining<=w_remaining&~w_issue_mask;
   p_w_mask<=w_issue_mask;
   for(integer bank=0;bank<4;bank=bank+1)
    if(p_w_mask[bank])w_data[128*bank+:128]<=bank_dout[128*bank+:128];
   if((|p_w_mask)&&w_remaining==0)begin w_valid<=1;w_active<=0;end
   if(conflict)prefer_n<=!n_wins;
  end
 end
endmodule
