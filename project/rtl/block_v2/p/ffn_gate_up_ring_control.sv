`timescale 1ns/1ps
// Bounded reference schedule for the fixed Qwen dense FFN shape. The three
// P compute/scatter services report a stripe only after every required write
// ACK. G reads two 64-value spans and the Mid owner commits one A16 tile.
// No cycle delays advance the cursor, no tensor data live in this controller.
module ffn_gate_up_ring_control #(
 parameter integer TOTAL_COLUMNS=11008
)(
 input wire clk,reset,
 input wire start_valid,output wire start_ready,input wire [63:0] start_owner,
 output wire stripe_valid,input wire stripe_ready,
 output wire [63:0] stripe_owner,output wire [15:0] stripe_first,
 output wire [7:0] stripe_width,
 input wire stripe_commit_valid,output wire stripe_commit_ready,
 input wire [63:0] stripe_commit_owner,input wire [15:0] stripe_commit_first,
 input wire stripe_commit_error,
 output wire g_valid,input wire g_ready,
 output wire [9:0] g_gate_base,g_up_base,g_mid_base,
 input wire g_commit_valid,output wire g_commit_ready,
 input wire g_commit_error,input wire [5:0] g_commit_words,
 output wire mid_valid,input wire mid_ready,output wire [63:0] mid_job_owner,
 output wire [15:0] mid_first,output reg [1:0] mid_destination,
 output wire [9:0] mid_destination_base,
 input wire mid_commit_valid,output wire mid_commit_ready,
 input wire [63:0] mid_commit_owner,input wire [15:0] mid_commit_first,
 input wire mid_commit_error,
 output reg done_valid,input wire done_ready,output reg done_error,
 output reg [31:0] rejected_commits
);
 localparam [3:0] IDLE=0,DECIDE=1,STRIPE_SEND=2,STRIPE_WAIT=3,G_SEND=4,G_WAIT=5,MID_SEND=6,MID_WAIT=7;
 localparam [15:0] COLS=16'(TOTAL_COLUMNS);
 reg [3:0] phase;
 reg [63:0] owner;
 reg [15:0] produced,committed;
 reg [4:0] mid_slot;
 reg high_half;
 wire [15:0] pending=produced-committed;
 wire [15:0] remaining=COLS-produced;
 wire [5:0] ring_word=committed[7:2]+(high_half ? 6'd16 : 6'd0);
 wire stripe_match=stripe_commit_owner==owner&&stripe_commit_first==produced;
 wire mid_match=mid_commit_owner==owner&&mid_commit_first==committed;
 assign start_ready=!reset&&phase==IDLE&&!done_valid;
 assign stripe_valid=!reset&&phase==STRIPE_SEND;
 assign stripe_owner=owner;
 assign stripe_first=produced;
 assign stripe_width=remaining>=16'd192 ? 8'd192:remaining[7:0];
 assign stripe_commit_ready=!reset&&phase==STRIPE_WAIT;
 assign g_valid=!reset&&phase==G_SEND;
 assign g_gate_base=10'd720+{4'd0,ring_word};
 assign g_up_base=10'd784+{4'd0,ring_word};
 assign g_mid_base=high_half ? 10'd864:10'd848;
 assign g_commit_ready=!reset&&phase==G_WAIT;
 assign mid_valid=!reset&&phase==MID_SEND;
 assign mid_job_owner=owner;
 assign mid_first=committed;
 assign mid_destination_base=10'd256+{1'd0,mid_slot,4'd0};
 assign mid_commit_ready=!reset&&phase==MID_WAIT;

 always @(posedge clk)begin
  if(reset)begin
   phase<=IDLE;owner<=0;produced<=0;committed<=0;mid_slot<=0;mid_destination<=0;
   high_half<=0;done_valid<=0;done_error<=0;rejected_commits<=0;
  end else begin
   if(done_valid&&done_ready)done_valid<=0;
   case(phase)
    IDLE:if(start_valid&&start_ready)begin
     owner<=start_owner;produced<=0;committed<=0;mid_slot<=0;mid_destination<=0;
     high_half<=0;done_error<=0;phase<=DECIDE;
    end
    DECIDE:begin
     if(committed==COLS)begin phase<=IDLE;done_valid<=1;end
     else if(pending>=16'd128)begin high_half<=0;phase<=G_SEND;end
     else if(produced<COLS && pending+{8'd0,stripe_width}<=16'd256)phase<=STRIPE_SEND;
     else begin phase<=IDLE;done_valid<=1;done_error<=1;end
    end
    STRIPE_SEND:if(stripe_valid&&stripe_ready)phase<=STRIPE_WAIT;
    STRIPE_WAIT:if(stripe_commit_valid&&stripe_commit_ready)begin
     if(!stripe_match)rejected_commits<=rejected_commits+1'b1;
     else if(stripe_commit_error)begin phase<=IDLE;done_valid<=1;done_error<=1;end
     else begin produced<=produced+{8'd0,stripe_width};phase<=DECIDE;end
    end
    G_SEND:if(g_valid&&g_ready)phase<=G_WAIT;
    G_WAIT:if(g_commit_valid&&g_commit_ready)begin
     if(g_commit_error||g_commit_words!=6'd16)begin phase<=IDLE;done_valid<=1;done_error<=1;end
     else if(!high_half)begin high_half<=1;phase<=G_SEND;end
     else phase<=MID_SEND;
    end
    MID_SEND:if(mid_valid&&mid_ready)phase<=MID_WAIT;
    MID_WAIT:if(mid_commit_valid&&mid_commit_ready)begin
     if(!mid_match)rejected_commits<=rejected_commits+1'b1;
     else if(mid_commit_error)begin phase<=IDLE;done_valid<=1;done_error<=1;end
     else begin
      committed<=committed+16'd128;phase<=DECIDE;
      if(mid_destination==2)begin mid_destination<=0;mid_slot<=mid_slot+5'd1;end
      else mid_destination<=mid_destination+2'd1;
     end
    end
    default:begin phase<=IDLE;done_valid<=1;done_error<=1;end
   endcase
  end
 end

`ifndef SYNTHESIS
 initial begin
  assert(TOTAL_COLUMNS>=128&&TOTAL_COLUMNS<=11008&&TOTAL_COLUMNS%128==0)
   else $fatal(1,"FFN ring profile incompatible with finite Mid windows");
 end
 always @(posedge clk)if(!reset&&phase!=IDLE)begin
  assert(produced>=committed&&pending<=256)else $fatal(1,"FFN ring lifetime violation");
  if(mid_valid)assert(mid_destination<3&&mid_slot<29)else $fatal(1,"FFN Mid window overflow");
 end
`endif
endmodule
