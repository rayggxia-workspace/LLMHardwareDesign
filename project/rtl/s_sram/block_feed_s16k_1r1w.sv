// Logical 16KiB, physical 32KiB: four lanes, two 256x128 1RW macros/lane.
// The two copies are migrating locations, not coherent mirrors. Each lane
// reads its live copy and writes the other physical port used by that read.
// One logical read and one logical write can be accepted every core cycle.
// Ordinary 128-bit reads share the read port with wide reads. Ordinary writes
// share the write port with masked 512-bit writes. A mask bit writes one full
// 128-bit word; byte write/RMW is not provided. Mask zero acknowledges a no-op.
//
// Same-edge read/write is READ-BEFORE-WRITE, including identical addresses.
// Read copy selectors are saved at acceptance, independent of later writes.
// Each response queue has two slots INCLUDING its in-flight operation.
// SRAM samples at edge K and commits/returns in the following low phase;
// response data or write ACK is registered at K+1, never at acceptance.
//
// reset is synchronous WARM reset: discard requests/responses, retain live
// locations and physical memory. An accepted write is not rolled back when
// reset is asserted later in its cycle. cold_reset additionally clears the
// live-location table and INVALIDATES ALL CONTENTS (it does not zero SRAM).
// Assert cold_reset at least once before use; rewrite words before reading
// after cold_reset. Thus no extra per-word valid bits are implied or hidden.
module block_feed_s16k_1r1w #(
 parameter bit ECHO_WRITE_DATA=1'b1
) (
 input wire clk,reset,cold_reset,
 input wire req,wr,input wire [9:0] addr,input wire [127:0] din,
 output wire ready,valid,input wire take,output wire [127:0] dout,
 input wire wide_req,input wire [7:0] wide_addr,output wire wide_ready,
 output wire wide_valid,input wire wide_take,output wire [511:0] wide_dout,
 input wire wide_write_req,input wire [7:0] wide_write_addr,
 input wire [511:0] wide_write_data,input wire [3:0] wide_write_mask,
 output wire wide_write_ready,wide_write_valid,input wire wide_write_take
`ifdef USE_POWER_PINS
 ,inout wire vdd,gnd
`endif
);
 wire stopped=reset||cold_reset;
 reg [255:0] live[0:3]; // 4 x 256 = 1024 live-location bits.
 reg [127:0] narrow_q[0:1];
 reg [511:0] read_q[0:1];
 reg nh,nt,rh,rt;
 reg [1:0] nc,rc,wc;
 reg n_pending,r_pending,w_pending;
 reg n_was_write,n_copy;
 reg [1:0] n_bank;
 reg [127:0] n_echo;
 reg [3:0] r_copy;
 reg prefer_wide_read,prefer_wide_write;

 assign valid=!stopped&&(nc!=0);
 assign wide_valid=!stopped&&(rc!=0);
 assign wide_write_valid=!stopped&&(wc!=0);
 assign dout=narrow_q[nh];
 assign wide_dout=read_q[rh];
 wire n_pop=valid&&take,r_pop=wide_valid&&wide_take;
 wire w_pop=wide_write_valid&&wide_write_take;
 wire [2:0] n_reserved={1'b0,nc}+{2'b0,n_pending};
 wire [2:0] r_reserved={1'b0,rc}+{2'b0,r_pending};
 wire [2:0] w_reserved={1'b0,wc}+{2'b0,w_pending};
 wire n_space=(n_reserved<3'd2)||n_pop;
 wire r_space=(r_reserved<3'd2)||r_pop;
 wire w_space=(w_reserved<3'd2)||w_pop;
 wire n_read_candidate=!stopped&&req&&!wr&&n_space;
 wire n_write_candidate=!stopped&&req&&wr&&n_space;
 wire r_candidate=!stopped&&wide_req&&r_space;
 wire w_candidate=!stopped&&wide_write_req&&w_space;
 assign wide_ready=!stopped&&r_space&&(!n_read_candidate||prefer_wide_read);
 assign wide_write_ready=!stopped&&w_space&&(!n_write_candidate||prefer_wide_write);
 assign ready=!stopped&&n_space&&
              (wr?(!w_candidate||!prefer_wide_write):(!r_candidate||!prefer_wide_read));
 wire n_fire=req&&ready;
 wire r_fire=wide_req&&wide_ready;
 wire w_fire=wide_write_req&&wide_write_ready;
 wire read_fire=r_fire||(n_fire&&!wr);
 wire write_fire=w_fire||(n_fire&&wr);
 wire [7:0] read_line=r_fire?wide_addr:addr[9:2];
 wire [7:0] write_line=w_fire?wide_write_addr:addr[9:2];
 wire [3:0] read_mask=r_fire?4'b1111:((n_fire&&!wr)?(4'b0001<<addr[1:0]):4'b0000);
 wire [3:0] write_mask=w_fire?wide_write_mask:((n_fire&&wr)?(4'b0001<<addr[1:0]):4'b0000);
 wire [3:0] read_copy,write_copy;
 wire [511:0] bank_data0,bank_data1;

 for(genvar lane=0;lane<4;lane=lane+1)begin: lanes
  assign read_copy[lane]=live[lane][read_line];
  assign write_copy[lane]=read_mask[lane]?!read_copy[lane]:!live[lane][write_line];
  wire [127:0] lane_write=w_fire?wide_write_data[128*lane+:128]:din;
  for(genvar copy=0;copy<2;copy=copy+1)begin: copies
   wire selected_read=read_fire&&read_mask[lane]&&(read_copy[lane]==1'(copy));
   wire selected_write=write_fire&&write_mask[lane]&&(write_copy[lane]==1'(copy));
   wire selected=selected_read||selected_write;
   wire [7:0] bank_addr=selected_write?write_line:read_line;
   wire [127:0] bank_data;
   s_sram_256x128_freepdk45 memory(
    .clk0(clk),.csb0(!selected),.web0(!selected_write),
    .addr0(bank_addr),.din0(lane_write),.dout0(bank_data)
`ifdef USE_POWER_PINS
    ,.vdd(vdd),.gnd(gnd)
`endif
   );
   if(copy==0)begin: copy_zero
    assign bank_data0[128*lane+:128]=bank_data;
   end else begin: copy_one
    assign bank_data1[128*lane+:128]=bank_data;
   end
  end
 end

 // Only cold reset touches the mapping. Warm reset cannot undo a write that
 // the real macro has already sampled and will commit in its low phase.
 always @(posedge clk)begin
  if(cold_reset)begin
   for(integer lane=0;lane<4;lane=lane+1)live[lane]<=256'b0;
  end else if(!reset&&write_fire)begin
   for(integer lane=0;lane<4;lane=lane+1)
    if(write_mask[lane])live[lane][write_line]<=write_copy[lane];
  end
 end

 always @(posedge clk)begin
  if(stopped)begin
   nh<=0;nt<=0;rh<=0;rt<=0;nc<=0;rc<=0;wc<=0;
   n_pending<=0;r_pending<=0;w_pending<=0;
   n_was_write<=0;n_copy<=0;n_bank<=0;n_echo<=0;r_copy<=0;
   prefer_wide_read<=1;prefer_wide_write<=1;
  end else begin
   if(n_pending)begin
    if(n_was_write)narrow_q[nt]<=ECHO_WRITE_DATA?n_echo:128'b0;
    else narrow_q[nt]<=n_copy?bank_data1[128*int'(n_bank)+:128]:bank_data0[128*int'(n_bank)+:128];
    nt<=!nt;
   end
   if(r_pending)begin
    for(integer lane=0;lane<4;lane=lane+1)
     read_q[rt][128*lane+:128]<=r_copy[lane]?bank_data1[128*lane+:128]:bank_data0[128*lane+:128];
    rt<=!rt;
   end
   if(n_pop)nh<=!nh;
   if(r_pop)rh<=!rh;
   case({n_pending,n_pop})
    2'b10:nc<=nc+1'b1;
    2'b01:nc<=nc-1'b1;
    default:begin end
   endcase
   case({r_pending,r_pop})
    2'b10:rc<=rc+1'b1;
    2'b01:rc<=rc-1'b1;
    default:begin end
   endcase
   case({w_pending,w_pop})
    2'b10:wc<=wc+1'b1;
    2'b01:wc<=wc-1'b1;
    default:begin end
   endcase
   n_pending<=n_fire;r_pending<=r_fire;w_pending<=w_fire;
   if(n_fire)begin
    n_was_write<=wr;n_copy<=read_copy[addr[1:0]];n_bank<=addr[1:0];n_echo<=din;
   end
   if(r_fire)r_copy<=read_copy;
   if(n_read_candidate&&r_candidate)prefer_wide_read<=!r_fire;
   if(n_write_candidate&&w_candidate)prefer_wide_write<=!w_fire;
  end
 end
endmodule
