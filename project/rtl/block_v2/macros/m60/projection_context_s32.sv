// Sixteen8-lane S32 contexts. Two bounded arithmetic/metadata stages feed one
// elastic response owner. STEP reads the actual RF at stage3, including
// same-edge retirement forwarding. Active-lane faults reject the whole vector.
module projection_context_s32 (
 input wire clk, reset,
 input wire cmd_valid, output wire cmd_ready, cmd_step_ready, cmd_control_ready,
 input wire [2:0] cmd_kind,
 input wire [3:0] cmd_context,
 input wire [127:0] cmd_owner,
 input wire [31:0] cmd_tag,
 input wire [15:0] cmd_full_k, cmd_k_offset,
 input wire [7:0] cmd_group_k,
 input wire [3:0] cmd_n,
 input wire cmd_final,
 input wire [5:0] cmd_a_shift,
 input wire [255:0] cmd_partial, cmd_previous, cmd_bias,
 input wire [127:0] cmd_scale_fp16,
 output wire rsp_valid, input wire rsp_ready,
 output reg [2:0] rsp_kind,
 output reg [3:0] rsp_context,
 output reg [127:0] rsp_owner,
 output reg [31:0] rsp_tag,
 output wire [15:0] rsp_full_k,
 output wire [7:0] rsp_group_k,
 output wire [3:0] rsp_n,
 output wire [15:0] rsp_next_k,
 output reg rsp_final,
 output wire [255:0] rsp_data,
 output wire rsp_error
);
 reg [15:0] live;
 reg [127:0] owner [0:15];
 reg [255:0] state [0:15];
 reg [15:0] full_k [0:15], next_k [0:15];
 reg [7:0] group_k [0:15];
 reg [3:0] count_n [0:15];
 reg pending, pending_error;
 reg [15:0] pending_next_k, pending_full_k;
 reg [255:0] pending_data;
 reg [7:0] pending_group_k;
 reg [3:0] pending_n;
 assign rsp_valid=pending;
 assign rsp_error=pending_error;
 assign rsp_data=pending_error ? 256'd0 : pending_data;
 assign rsp_next_k=pending_error ? 16'd0 : pending_next_k;
 assign rsp_full_k=pending_error ? 16'd0 : pending_full_k;
 assign rsp_group_k=pending_error ? 8'd0 : pending_group_k;
 assign rsp_n=pending_error ? 4'd0 : pending_n;
 wire retire=pending && rsp_ready;
 wire response_ready=!pending || rsp_ready;

 typedef struct packed {
  logic [3:0] context_id;
  logic [127:0] owner_key;
  logic [31:0] tag;
  logic [15:0] full_length, offset;
  logic [7:0] group_length;
  logic [3:0] lanes;
  logic final_step;
  logic [255:0] bias;
 } step_metadata;
 reg product_meta_valid, rounded_meta_valid;
 step_metadata product_meta, rounded_meta;
 wire rounded_meta_ready=!rounded_meta_valid || response_ready;
 wire product_meta_ready=!product_meta_valid || rounded_meta_ready;
 wire scale_ready, scale_valid, scale_error;
 wire [31:0] scale_tag;
 wire [255:0] scale_data;
 // Controls never overtake arithmetic. STEP can fill two arithmetic owners
 // behind a held response, then honestly backpressures at that finite bound.
 // Two capacity observations for the same command port. The producer
 // that owns the port selects the matching class. Only cmd_ready on the
 // actual cmd_kind controls the single acceptance below.
 assign cmd_step_ready=!reset && scale_ready && product_meta_ready;
 assign cmd_control_ready=!reset && !product_meta_valid && !rounded_meta_valid && response_ready;
 assign cmd_ready=cmd_kind==2 ? cmd_step_ready : cmd_control_ready;
 wire accepted=cmd_valid && cmd_ready;
 wire accepted_step=accepted && cmd_kind==2;
 wire accepted_control=accepted && cmd_kind!=2;
 wire step_transfer=rounded_meta_valid && scale_valid && response_ready;
 scale_group_s32 #(.ROUND_ONLY(1'b1)) scale (
  .clk(clk),.reset(reset),.in_valid(accepted_step),.in_ready(scale_ready),
  .in_tag(cmd_tag),.in_n(cmd_n),.in_first(1'b1),.in_final(1'b0),
  .in_a_shift(cmd_a_shift),.in_partial(cmd_partial),.in_scale_fp16(cmd_scale_fp16),
  .in_previous(256'd0),.in_bias(256'd0),.out_valid(scale_valid),
  .out_ready(response_ready),.out_tag(scale_tag),.out_data(scale_data),.out_error(scale_error)
 );

 // One logical RF read port. The retiring registered response is bypassed;
 // the new stage3 sum cannot feed back into its own input.
 wire [3:0] read_context=rounded_meta_valid ? rounded_meta.context_id : cmd_context;
 reg effective_live;
 reg [127:0] effective_owner;
 reg [255:0] effective_state;
 reg [15:0] effective_full_k, effective_next_k;
 reg [7:0] effective_group_k;
 reg [3:0] effective_n;
 always @* begin
  effective_live=live[read_context]; effective_owner=owner[read_context];
  effective_state=state[read_context]; effective_full_k=full_k[read_context];
  effective_next_k=next_k[read_context]; effective_group_k=group_k[read_context];
  effective_n=count_n[read_context];
  // Precompute the same-edge retiring value without waiting for rsp_ready.
  // A new response/control only samples this read when response_ready=1;
  // with pending=1 that implies rsp_ready=1, hence actual retirement.
  // Under backpressure this combinational value is never committed. Keeping
  // ready out of the data mux avoids a ready->mux->prefix-adder timing path.
  if(pending && !rsp_error && rsp_context==read_context) begin
   effective_owner=rsp_owner; effective_state=rsp_data; effective_next_k=rsp_next_k;
   if(rsp_kind<=1) begin
    effective_live=1; effective_full_k=pending_full_k;
    effective_group_k=pending_group_k; effective_n=pending_n;
   end else if(rsp_kind==2) effective_live=!rsp_final;
   else effective_live=0;
  end
 end
 wire [16:0] step_next={1'b0,rounded_meta.offset}+{9'd0,rounded_meta.group_length};
 wire allocation_bad=effective_live || cmd_n==0 || cmd_n>8 ||
  (cmd_group_k!=16 && cmd_group_k!=128) || cmd_full_k==0 ||
  (cmd_full_k & ({8'd0,cmd_group_k}-16'd1))!=0 || cmd_k_offset>=cmd_full_k ||
  (cmd_k_offset & ({8'd0,cmd_group_k}-16'd1))!=0 ||
  (cmd_kind==0 && cmd_k_offset!=0) || (cmd_kind==1 && cmd_k_offset==0);
 wire control_owner_bad=!effective_live || effective_owner!=cmd_owner;
 wire control_bad=cmd_kind<=1 ? allocation_bad : (cmd_kind<=4 ? control_owner_bad : 1'b1);
 wire step_bad=!effective_live || effective_owner!=rounded_meta.owner_key ||
  rounded_meta.lanes!=effective_n || rounded_meta.group_length!=effective_group_k ||
  rounded_meta.full_length!=effective_full_k || rounded_meta.offset!=effective_next_k ||
  step_next>{1'b0,effective_full_k} ||
  (rounded_meta.final_step!=(step_next=={1'b0,effective_full_k})) ||
  scale_error || scale_tag!=rounded_meta.tag;
 wire signed [32:0] summed [0:7];
 wire signed [33:0] biased [0:7];
 wire [7:0] overflow;
 for(genvar lane=0;lane<8;lane=lane+1) begin: prefix
  assign summed[lane]=$signed({scale_data[lane*32+31],scale_data[lane*32+:32]}) +
    $signed({effective_state[lane*32+31],effective_state[lane*32+:32]});
  assign biased[lane]=$signed({summed[lane][32],summed[lane]}) +
    (rounded_meta.final_step ? $signed({{2{rounded_meta.bias[lane*32+31]}},rounded_meta.bias[lane*32+:32]}) : 34'sd0);
  assign overflow[lane]=lane<rounded_meta.lanes &&
    (summed[lane][32]!=summed[lane][31] || biased[lane][33:31]!={3{biased[lane][31]}});
 end
 wire step_error=step_bad || (|overflow);
 always @(posedge clk) begin
  if(reset) begin
   live<=0; pending<=0; pending_error<=0; pending_data<=0;
   rsp_kind<=0; rsp_context<=0; rsp_owner<=0; rsp_tag<=0; rsp_final<=0;
   pending_next_k<=0; pending_full_k<=0; pending_group_k<=0; pending_n<=0;
   product_meta_valid<=0; rounded_meta_valid<=0; product_meta<='0; rounded_meta<='0;
  end else begin
   if(product_meta_ready) begin
    product_meta_valid<=accepted_step;
    if(accepted_step) begin
     product_meta.context_id<=cmd_context; product_meta.owner_key<=cmd_owner;
     product_meta.tag<=cmd_tag; product_meta.full_length<=cmd_full_k;
     product_meta.offset<=cmd_k_offset; product_meta.group_length<=cmd_group_k;
     product_meta.lanes<=cmd_n; product_meta.final_step<=cmd_final; product_meta.bias<=cmd_bias;
    end
   end
   if(rounded_meta_ready) begin
    rounded_meta_valid<=product_meta_valid;
    if(product_meta_valid) rounded_meta<=product_meta;
   end
   if(retire && !rsp_error) begin
    if(rsp_kind<=1) begin
     live[rsp_context]<=1; owner[rsp_context]<=rsp_owner;
     full_k[rsp_context]<=pending_full_k; next_k[rsp_context]<=pending_next_k;
     group_k[rsp_context]<=pending_group_k; count_n[rsp_context]<=pending_n;
     state[rsp_context]<=pending_data;
    end else if(rsp_kind==2) begin
     state[rsp_context]<=pending_data; next_k[rsp_context]<=pending_next_k;
     live[rsp_context]<=!rsp_final;
    end else live[rsp_context]<=0;
   end
   if(response_ready) begin
    pending<=0;
    if(step_transfer) begin
     pending<=1; pending_error<=step_error;
     rsp_kind<=2; rsp_context<=rounded_meta.context_id; rsp_owner<=rounded_meta.owner_key;
     rsp_tag<=rounded_meta.tag; rsp_final<=rounded_meta.final_step;
     pending_full_k<=effective_full_k; pending_group_k<=effective_group_k;
     pending_n<=effective_n; pending_next_k<=step_next[15:0];
     for(integer n=0;n<8;n=n+1)
      pending_data[n*32+:32]<=!step_error && n<rounded_meta.lanes ? biased[n][31:0] : 32'd0;
    end else if(accepted_control) begin
     pending<=1; pending_error<=control_bad;
     rsp_kind<=cmd_kind; rsp_context<=cmd_context; rsp_owner<=cmd_owner;
     rsp_tag<=cmd_tag; rsp_final<=0;
     pending_full_k<=cmd_kind<=1 ? cmd_full_k : effective_full_k;
     pending_group_k<=cmd_kind<=1 ? cmd_group_k : effective_group_k;
     pending_n<=cmd_kind<=1 ? cmd_n : effective_n;
     pending_next_k<=cmd_kind<=1 ? cmd_k_offset : effective_next_k;
     if(cmd_kind==0 || cmd_kind==4) pending_data<=0;
     else if(cmd_kind==1) begin
      for(integer n=0;n<8;n=n+1)
       pending_data[n*32+:32]<=n<cmd_n ? cmd_previous[n*32+:32] : 32'd0;
     end else pending_data<=effective_state;
    end
   end
  end
 end
endmodule
