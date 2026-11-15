// Candidate exact S80 partial-sum transport, not a final RNE result.
// One slot on the existing S128 port. A restored raw stream is only scratch
// until successful DONE with matching key+metadata and true source commit.
// No payload SRAM/FIFO: the compute provider supplies/accepts ordered words.
module dot_s80_checkpoint #(
 parameter integer WORDS=20,
 parameter integer INDEX=$clog2(WORDS+3)
) (
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,
 input wire cmd_restore,input wire cmd_committed,
 input wire [31:0] cmd_tag,input wire [127:0] cmd_key,cmd_metadata,
 input wire [9:0] cmd_base,
 input wire abort_valid,output wire abort_ready,input wire [31:0] abort_tag,
 input wire state_in_valid,output wire state_in_ready,input wire [127:0] state_in_word,
 output wire state_out_valid,input wire state_out_ready,output wire [127:0] state_out_word,
 output wire s_req_valid,input wire s_req_ready,output wire s_req_write,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,input wire s_rsp_error,
 output reg done_valid,input wire done_ready,output reg [31:0] done_tag,
 output reg done_error,done_aborted,output reg [INDEX-1:0] done_ack_count
);
 localparam [INDEX-1:0] DATA_END=INDEX'(WORDS),TOTAL=INDEX'(WORDS+2);
 reg busy,restore,error,aborted,req_held,out_held;
 reg [31:0] tag;
 reg [127:0] key,metadata;
 reg [9:0] base;
 reg [INDEX-1:0] issued,received;
 wire [INDEX-1:0] pending=issued-received;
 wire [INDEX-1:0] issue_offset=restore?
   (issued<2 ? DATA_END+issued : issued-2):issued;
 wire load_data=restore&&received>=2;
 wire save_data=!restore&&issued<DATA_END;
 wire stopping=error||aborted;
 assign cmd_ready=!reset&&!busy&&!done_valid;
 assign abort_ready=!reset&&busy&&!stopping&&abort_tag==tag&&(issued!=TOTAL||pending!=0||req_held||out_held);
 wire header_bad=restore&&received<2&&s_rsp_data!=(received==0?key:metadata);
 assign state_out_valid=!reset&&busy&&s_rsp_valid&&pending!=0&&load_data&&(!stopping||out_held)&&(!s_rsp_error||out_held);
 assign state_out_word=s_rsp_data;
 assign s_rsp_ready=!reset&&busy&&pending!=0&&
   (!load_data||state_out_ready||((stopping||s_rsp_error)&&!out_held));
 wire ack_fire=s_rsp_valid&&s_rsp_ready;
 assign s_req_valid=!reset&&busy&&issued<TOTAL&&(!stopping||req_held)&&
   (pending<2||ack_fire)&&(!save_data||state_in_valid);
 wire req_fire=s_req_valid&&s_req_ready;
 assign state_in_ready=req_fire&&save_data;
 assign s_req_write=!restore;
 assign s_req_address=base+10'(issue_offset);
 assign s_req_data=restore?128'd0:save_data?state_in_word:issued==DATA_END?key:metadata;

 always @(posedge clk)begin
  if(reset)begin
   busy<=0;restore<=0;error<=0;aborted<=0;req_held<=0;out_held<=0;
   tag<=0;key<=0;metadata<=0;base<=0;issued<=0;received<=0;
   done_valid<=0;done_tag<=0;done_error<=0;done_aborted<=0;done_ack_count<=0;
  end else begin
   if(done_valid&&done_ready)done_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    if({1'b0,cmd_base}+11'(WORDS+2)>1024||(cmd_restore&&!cmd_committed))begin
     done_valid<=1;done_tag<=cmd_tag;done_error<=1;done_aborted<=0;done_ack_count<=0;
    end else begin
     busy<=1;restore<=cmd_restore;tag<=cmd_tag;key<=cmd_key;metadata<=cmd_metadata;base<=cmd_base;
     error<=0;aborted<=0;req_held<=0;out_held<=0;issued<=0;received<=0;
    end
   end
   if(busy)begin
    req_held<=s_req_valid&&!s_req_ready;out_held<=state_out_valid&&!state_out_ready;
    if(req_fire)issued<=issued+1'b1;
    if(ack_fire)begin
     received<=received+1'b1;
     if(s_rsp_error||header_bad)error<=1;
    end
    if(abort_valid&&abort_ready)aborted<=1;
    if(pending==0&&!req_held&&!out_held&&(stopping||issued==TOTAL))begin
     busy<=0;done_valid<=1;done_tag<=tag;done_error<=error;
     done_aborted<=aborted;done_ack_count<=received;
    end
   end
  end
 end
endmodule
