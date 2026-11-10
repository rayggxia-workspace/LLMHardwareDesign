// Explicit LOCAL_S_PACK64 source, independent of DDR. Refs #250.
// One source binding and one accepted MC64 request. Existing packer owns the
// only64B payload hold and16B S cache; no additional W bank/FIFO/SRAM.
// 17 ordinary W-first beats:16 W8 payloads, then scale1+48B zero padding.
module dynamic_s32_weight_source (
 input wire clk,reset,
 input wire bind_valid,output wire bind_ready,
 input wire [127:0] bind_key,
 input wire [63:0] bind_record_base,
 input wire [31:0] bind_scalar_base,bind_k_stride,bind_n_stride,
 input wire [7:0] bind_length,
 input wire [3:0] bind_n,
 input wire [2:0] bind_digit,
 input wire bind_k_major,
 output reg bind_ack_valid,input wire bind_ack_ready,
 output reg [127:0] bind_ack_key,output reg bind_ack_error,
 input wire release_valid,output wire release_ready,input wire [127:0] release_key,
 input wire cancel_valid,output wire cancel_ready,input wire [127:0] cancel_key,
 input wire close_valid,output wire close_ready,input wire [31:0] close_tag_base,
 input wire req_valid,output wire req_ready,
 input wire [63:0] req_address,input wire [31:0] req_tag,input wire [4:0] req_record_beats,
 output wire rsp_valid,input wire rsp_ready,output wire [31:0] rsp_tag,
 output wire [511:0] rsp_data,
 output wire s_valid,input wire s_ready,output wire [31:0] s_address,s_tag,
 input wire r_valid,output wire r_ready,input wire [31:0] r_tag,
 input wire [127:0] r_data,input wire r_error,
 output reg fault_valid,input wire fault_ready,
 output reg [3:0] fault_reason,output reg [31:0] fault_tag,
 output reg [63:0] fault_address,
 output wire active,quiescent,
 output reg [4:0] returned_beats
);
 localparam [2:0] IDLE=0,START_PACK=1,WAIT_PACK=2,RETURN_CONSTANT=3;
 reg [2:0] state;
 reg owned,cancelled,closed,tag_bound,held_offer,poisoned;
 reg [127:0] owner;
 reg [63:0] record_base,offer_address;
 reg [31:0] scalar_base,k_stride,n_stride,tag_base,offer_tag,pending_tag;
 reg [7:0] length;
 reg [3:0] lanes;
 reg [2:0] digit;
 reg k_major;
 reg [16:0] issued,returned;
 reg [4:0] pending_beat;
 reg [31:0] pack_base;
 reg [4:0] pack_k;
 reg [2:0] pack_n;
 reg scale_return;
 wire ack_space=!bind_ack_valid || bind_ack_ready;
 wire fault_space=!fault_valid || fault_ready;
 assign active=owned;
 assign quiescent=!owned && state==IDLE && !held_offer && !poisoned;
 assign bind_ready=!reset && !owned && state==IDLE && ack_space;
 wire [63:0] bind_last={32'd0,bind_scalar_base}+
  ({56'd0,bind_length}-64'd1)*{32'd0,bind_k_stride}+
  ({60'd0,bind_n}-64'd1)*{32'd0,bind_n_stride};
 wire bind_bad=bind_length==0 || bind_length>128 || bind_n==0 || bind_n>8 || bind_digit>4 ||
  bind_record_base[5:0]!=0 || bind_record_base>64'hfffffffffffffbc0 || bind_last>4095;
 wire complete=returned==17'h1ffff;
 assign release_ready=!reset && owned && state==IDLE && !held_offer && !poisoned && fault_space &&
  (complete || (cancelled && (closed || issued==0)));
 assign cancel_ready=!reset && owned && !cancelled && fault_space;
 assign close_ready=!reset && owned && cancelled && !held_offer && fault_space;
 assign req_ready=!reset && owned && state==IDLE && fault_space &&
  (!cancelled || held_offer) && !closed && !poisoned;
 wire [63:0] displacement=req_address-record_base;
 wire [4:0] beat=displacement[10:6];
 wire request_bad=req_record_beats!=17 || req_address<record_base || displacement>=1088 || req_address[5:0]!=0 ||
  req_tag[4:0]!=beat || (tag_bound && req_tag[31:5]!=tag_base[31:5]) || issued[beat] ||
  (held_offer && (req_address!=offer_address || req_tag!=offer_tag));
 wire [7:0] k_offset={1'b0,beat[3:1],4'd0};
 wire [3:0] n_offset={1'b0,beat[0],2'b0};
 wire no_payload=k_offset>=length || n_offset>=lanes;
 wire [31:0] next_base=scalar_base+{24'd0,k_offset}*k_stride+{28'd0,n_offset}*n_stride;
 wire [7:0] available_k=length-k_offset;
 wire [3:0] available_n=lanes-n_offset;
 wire p_cmd_ready,p_out_valid,p_out_ready,p_out_error,p_out_weight;
 wire [31:0] p_out_tag;wire [511:0] p_out_data;
 dynamic_s32_packer packer(.clk,.reset,.cmd_valid(state==START_PACK),.cmd_ready(p_cmd_ready),
  .cmd_tag(pending_tag),.cmd_weight(1'b1),.cmd_k_major(k_major),.cmd_digit(digit),
  .cmd_scalar_base(pack_base),.cmd_k_stride(k_stride),.cmd_n_stride(n_stride),
  .cmd_k_count(pack_k),.cmd_n_count(pack_n),.s_valid,.s_ready,.s_address,.s_tag,
  .r_valid,.r_ready,.r_tag,.r_data,.r_error,.out_valid(p_out_valid),.out_ready(p_out_ready),
  .out_tag(p_out_tag),.out_weight(p_out_weight),.out_error(p_out_error),.out_data(p_out_data));
 reg [511:0] scale_word;
 always @*begin
  scale_word=0;
  for(integer j=0;j<8;j=j+1)if(j<int'(lanes))scale_word[j*16+:16]=16'h3c00;
 end
 wire pack_error=p_out_error || !p_out_weight || p_out_tag!=pending_tag;
 assign rsp_valid=!reset && (state==RETURN_CONSTANT || (state==WAIT_PACK && p_out_valid && !pack_error));
 assign rsp_tag=pending_tag;
 assign rsp_data=state==RETURN_CONSTANT ? (scale_return ? scale_word : 512'd0) : p_out_data;
 assign p_out_ready=state==WAIT_PACK && (pack_error ? fault_space : rsp_ready);
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;owned<=0;cancelled<=0;closed<=0;tag_bound<=0;held_offer<=0;poisoned<=0;
   owner<=0;record_base<=0;offer_address<=0;scalar_base<=0;k_stride<=0;n_stride<=0;
   tag_base<=0;offer_tag<=0;pending_tag<=0;length<=0;lanes<=0;digit<=0;k_major<=0;
   issued<=0;returned<=0;pending_beat<=0;pack_base<=0;pack_k<=0;pack_n<=0;scale_return<=0;
   fault_valid<=0;fault_reason<=0;fault_tag<=0;fault_address<=0;
   bind_ack_valid<=0;bind_ack_key<=0;bind_ack_error<=0;returned_beats<=0;
  end else begin
   if(bind_ack_valid && bind_ack_ready)bind_ack_valid<=0;
   if(fault_valid && fault_ready)fault_valid<=0;
   if(bind_valid && bind_ready)begin
    bind_ack_valid<=1;bind_ack_key<=bind_key;bind_ack_error<=bind_bad;
    if(!bind_bad)begin
     owned<=1;owner<=bind_key;record_base<=bind_record_base;
     scalar_base<=bind_scalar_base;k_stride<=bind_k_stride;n_stride<=bind_n_stride;
     length<=bind_length;lanes<=bind_n;digit<=bind_digit;k_major<=bind_k_major;
     cancelled<=0;closed<=0;tag_bound<=0;held_offer<=0;poisoned<=0;issued<=0;returned<=0;returned_beats<=0;
    end
   end
   if(release_valid && release_ready)begin
    if(release_key==owner)owned<=0;
    else if(fault_space)begin fault_valid<=1;fault_reason<=1;fault_tag<=0;fault_address<=record_base;end
   end
   if(cancel_valid && cancel_ready)begin
    if(cancel_key!=owner)begin fault_valid<=1;fault_reason<=2;fault_tag<=0;fault_address<=record_base;end
    else begin
     cancelled<=1;
     // A previously offered MC request may not be withdrawn on cancellation.
     held_offer<=req_valid && !req_ready;
     offer_address<=req_address;offer_tag<=req_tag;
    end
   end
   if(close_valid && close_ready)begin
    if(!tag_bound || close_tag_base!=tag_base)begin
     fault_valid<=1;fault_reason<=3;fault_tag<=close_tag_base;fault_address<=record_base;
    end else closed<=1;
   end
   if(req_valid && req_ready)begin
    if(request_bad)begin fault_valid<=1;fault_reason<=4;fault_tag<=req_tag;fault_address<=req_address;end
    else begin
     issued[beat]<=1;pending_beat<=beat;pending_tag<=req_tag;
     if(!tag_bound)begin tag_bound<=1;tag_base<={req_tag[31:5],5'd0};end
     held_offer<=0;
     if(beat==16 || no_payload)begin
      state<=RETURN_CONSTANT;scale_return<=beat==16;
     end else begin
      pack_base<=next_base;pack_k<=available_k>=8'd16 ? 5'd16 : available_k[4:0];
      pack_n<=available_n>=4'd4 ? 3'd4 : available_n[2:0];state<=START_PACK;
     end
    end
   end
   if(state==START_PACK && p_cmd_ready)state<=WAIT_PACK;
   if(state==WAIT_PACK && p_out_valid && p_out_ready && pack_error)begin
    fault_valid<=1;fault_reason<=5;fault_tag<=pending_tag;fault_address<=record_base+{53'd0,pending_beat,6'd0};
    // MC has no error-data return wire. Do not fabricate a successful beat or
    // silently return zeros: quarantine this owner until system reset/drain
    // recovery is explicitly implemented in the surrounding fabric.
    state<=IDLE;poisoned<=1;
   end
   if(rsp_valid && rsp_ready)begin
    returned[pending_beat]<=1;returned_beats<=returned_beats+1'b1;state<=IDLE;
   end
  end
 end
endmodule
