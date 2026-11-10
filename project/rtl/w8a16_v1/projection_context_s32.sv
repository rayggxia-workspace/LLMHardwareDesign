// Candidate M-internal projection RF: exactly 16 x 8 x S32 data (512 B).
// Owner keys and K cursors are real metadata, not free storage. One elastic
// response stage feeds a separately bounded result/S-write service. Capturing
// a SPILL/FINAL into that service releases this RF entry; the memory snapshot
// becomes restorable only after the external service's actual S-write ACK.
// No command/result field is a physical pin contract for a standalone leaf.
module projection_context_s32 (
 input wire clk, reset,
 input wire cmd_valid, output wire cmd_ready,
 input wire [2:0] cmd_kind, // CREATE=0, RESTORE=1, STEP=2, SPILL=3, DROP=4
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
 reg [15:0] pending_next_k;
 reg [255:0] pending_data;
 reg [15:0] pending_full_k;
 reg [7:0] pending_group_k;
 reg [3:0] pending_n;
 wire scale_valid, scale_ready, scale_error;
 wire [31:0] scale_tag;
 wire [255:0] scale_data;
 assign rsp_valid = pending && (rsp_kind!=2 || scale_valid);
 assign rsp_data = rsp_error ? 256'd0 : (rsp_kind==2 ? scale_data : pending_data);
 assign rsp_next_k = rsp_error ? 16'd0 : pending_next_k;
 assign rsp_full_k = rsp_error ? 16'd0 : pending_full_k;
 assign rsp_group_k = rsp_error ? 8'd0 : pending_group_k;
 assign rsp_n = rsp_error ? 4'd0 : pending_n;
 assign rsp_error = pending_error || (rsp_kind==2 && scale_error);
 wire retire = rsp_valid && rsp_ready;
 assign cmd_ready = !reset && (!pending || retire) && scale_ready;

 // Read-after-write bypass makes consecutive group16 head updates and
 // CREATE->STEP legal at one accepted command/cycle under no backpressure.
 reg effective_live;
 reg [127:0] effective_owner;
 reg [255:0] effective_state;
 reg [15:0] effective_full_k, effective_next_k;
 reg [7:0] effective_group_k;
 reg [3:0] effective_n;
 always @* begin
  effective_live=live[cmd_context]; effective_owner=owner[cmd_context];
  effective_state=state[cmd_context]; effective_full_k=full_k[cmd_context];
  effective_next_k=next_k[cmd_context]; effective_group_k=group_k[cmd_context];
  effective_n=count_n[cmd_context];
  if(retire && !rsp_error && rsp_context==cmd_context) begin
   effective_owner=rsp_owner; effective_state=rsp_data;
   effective_next_k=rsp_next_k;
   if(rsp_kind<=1) begin
    effective_live=1; effective_full_k=pending_full_k;
    effective_group_k=pending_group_k; effective_n=pending_n;
   end else if(rsp_kind==2) effective_live=!rsp_final;
   else effective_live=0;
  end
 end
 wire [16:0] next_offset={1'b0,cmd_k_offset}+{9'd0,cmd_group_k};
 wire allocation_bad = effective_live || cmd_n==0 || cmd_n>8 ||
  (cmd_group_k!=16 && cmd_group_k!=128) || cmd_full_k==0 ||
  (cmd_full_k & ({8'd0,cmd_group_k}-16'd1))!=0 ||
  cmd_k_offset>=cmd_full_k ||
  (cmd_k_offset & ({8'd0,cmd_group_k}-16'd1))!=0 ||
  (cmd_kind==0 && cmd_k_offset!=0) || (cmd_kind==1 && cmd_k_offset==0);
 wire owner_bad = !effective_live || effective_owner!=cmd_owner;
 wire step_bad = owner_bad || cmd_n!=effective_n ||
  cmd_group_k!=effective_group_k || cmd_full_k!=effective_full_k ||
  cmd_k_offset!=effective_next_k || next_offset>{1'b0,effective_full_k} ||
  (cmd_final!=(next_offset=={1'b0,effective_full_k}));
 wire command_bad = cmd_kind<=1 ? allocation_bad :
  cmd_kind==2 ? step_bad : (cmd_kind<=4 ? owner_bad : 1'b1);
 wire accepted=cmd_valid && cmd_ready;
 scale_group_s32 scale (
  .clk(clk),.reset(reset),.in_valid(accepted && cmd_kind==2),.in_ready(scale_ready),
  .in_tag(cmd_tag),.in_n(cmd_n),.in_first(1'b0),.in_final(cmd_final),
  .in_a_shift(cmd_a_shift),.in_partial(cmd_partial),.in_scale_fp16(cmd_scale_fp16),
  .in_previous(effective_state),.in_bias(cmd_bias),.out_valid(scale_valid),
  .out_ready(retire && rsp_kind==2),.out_tag(scale_tag),
  .out_data(scale_data),.out_error(scale_error)
 );
 always @(posedge clk) begin
  if(reset) begin
   live<=0; pending<=0; pending_error<=0; pending_data<=0;
   rsp_kind<=0; rsp_context<=0; rsp_owner<=0; rsp_tag<=0;
   pending_next_k<=0; rsp_final<=0;
   pending_full_k<=0; pending_group_k<=0; pending_n<=0;
  end else begin
   if(retire) begin
    pending<=0;
    if(!rsp_error) begin
     if(rsp_kind<=1) begin
      live[rsp_context]<=1; owner[rsp_context]<=rsp_owner;
      full_k[rsp_context]<=pending_full_k; next_k[rsp_context]<=rsp_next_k;
      group_k[rsp_context]<=pending_group_k; count_n[rsp_context]<=pending_n;
      state[rsp_context]<=rsp_data;
     end else if(rsp_kind==2) begin
      state[rsp_context]<=rsp_data; next_k[rsp_context]<=rsp_next_k;
      live[rsp_context]<=!rsp_final;
     end else live[rsp_context]<=0;
    end
   end
   if(accepted) begin
    pending<=1; pending_error<=command_bad;
    rsp_kind<=cmd_kind; rsp_context<=cmd_context; rsp_owner<=cmd_owner;
    rsp_tag<=cmd_tag; rsp_final<=cmd_kind==2 && cmd_final;
    pending_next_k<=command_bad ? 16'd0 : (cmd_kind==2 ? next_offset[15:0] :
                (cmd_kind<=1 ? cmd_k_offset : effective_next_k));
    // Snapshot metadata must come from the owned RF entry, not fields an
    // unrelated SPILL/DROP command happens to present on the input bus.
    pending_full_k<=cmd_kind<=1 ? cmd_full_k : effective_full_k;
    pending_group_k<=cmd_kind<=1 ? cmd_group_k : effective_group_k;
    pending_n<=cmd_kind<=1 ? cmd_n : effective_n;
    if(cmd_kind==0 || cmd_kind==4) pending_data<=0;
    else if(cmd_kind==1) begin
     for(integer n=0;n<8;n=n+1)
      pending_data[n*32+:32]<=n<cmd_n ? cmd_previous[n*32+:32] : 32'd0;
    end else pending_data<=effective_state;
   end
  end
 end
 // Tag equality is structural: scale and metadata enter on the same fire.
 // Do not expose scale_tag as another package-level output.
 wire unused_scale_tag = ^scale_tag;
endmodule
