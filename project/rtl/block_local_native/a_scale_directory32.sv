// One finite directory for one object: 32 committed K128 tile shifts (24B),
// valid bits and one shared object identity. X and striped Mid need separate
// instances while both are live. No A payload or new SRAM is stored here.
// publish_* must come from real quantizer completion / checked metadata frame,
// not from a predicted duration or an X-data copy ACK. Storage/lease release
// inputs are LC lifetime proofs; the joint LC must wire them to actual drain.
module a_scale_directory32 (
 input wire clk, reset,
 input wire cfg_valid, output wire cfg_ready,
 input wire [127:0] cfg_key,
 input wire [15:0] cfg_first_kk,
 input wire [5:0] cfg_tiles,
 input wire cfg_stride3,
 input wire storage_released, leases_drained,
 output reg cfg_rejected,
 input wire publish_valid, output wire publish_ready,
 input wire [127:0] publish_key,
 input wire [15:0] publish_kk,
 input wire [5:0] publish_shift,
 input wire [15:0] publish_written_mask,
 input wire publish_error,
 output reg publish_rejected,
 input wire [127:0] lookup_key,
 input wire [15:0] lookup_kk,
 output wire lookup_valid,
 output wire [5:0] lookup_shift,
 output reg [31:0] rejected_publications
);
 reg active;
 reg [127:0] key;
 reg [15:0] first_kk;
 reg [5:0] tiles;
 reg stride3;
 reg [31:0] valid_tiles;
 reg [5:0] shifts[0:31];
 wire [16:0] cfg_last={1'b0,cfg_first_kk}+({11'd0,cfg_tiles}-17'd1)*(cfg_stride3?17'd384:17'd128);
 wire cfg_bad=cfg_first_kk[6:0]!=0 || cfg_tiles==0 || cfg_tiles>32 || cfg_last>17'd65408;
 wire [8:0] publish_number=9'((publish_kk-first_kk)>>7);
 wire [8:0] lookup_number=9'((lookup_kk-first_kk)>>7);
 wire [8:0] publish_entry=stride3?publish_number/9'd3:publish_number;
 wire [8:0] lookup_entry=stride3?lookup_number/9'd3:lookup_number;
 wire [4:0] publish_index=publish_entry[4:0],lookup_index=lookup_entry[4:0];
 wire publish_range=active && publish_key==key && publish_kk[6:0]==0 &&
     publish_kk>=first_kk && publish_entry<{3'd0,tiles} && (!stride3 || publish_number%9'd3==0);
 wire publish_bad=!publish_range || publish_error || publish_shift>17 ||
     publish_written_mask!=16'hffff || valid_tiles[publish_index];
 assign cfg_ready=!reset && storage_released && leases_drained && !publish_valid;
 assign publish_ready=!reset;
 assign lookup_valid=!reset && active && lookup_key==key && lookup_kk[6:0]==0 &&
     lookup_kk>=first_kk && lookup_entry<{3'd0,tiles} && (!stride3 || lookup_number%9'd3==0) && valid_tiles[lookup_index];
 assign lookup_shift=lookup_valid?shifts[lookup_index]:6'd0;
 always @(posedge clk)begin
  if(reset)begin
   active<=0;key<=0;first_kk<=0;tiles<=0;stride3<=0;valid_tiles<=0;
   cfg_rejected<=0;publish_rejected<=0;rejected_publications<=0;
  end else begin
   cfg_rejected<=0;publish_rejected<=0;
   if(cfg_valid && cfg_ready)begin
    cfg_rejected<=cfg_bad;
    if(!cfg_bad)begin active<=1;key<=cfg_key;first_kk<=cfg_first_kk;tiles<=cfg_tiles;stride3<=cfg_stride3;valid_tiles<=0;end
   end
   if(publish_valid && publish_ready)begin
    publish_rejected<=publish_bad;
    if(publish_bad)rejected_publications<=rejected_publications+1'b1;
    else begin valid_tiles[publish_index]<=1;shifts[publish_index]<=publish_shift;end
   end
  end
 end
endmodule
