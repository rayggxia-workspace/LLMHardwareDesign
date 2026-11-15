`timescale 1ns/1ps
// Actual ABI02504d02 command transmitter. Caller retains its ONE command
// owner/fields until cmd_ready at the final true M handshake. No128B shadow
// frame: dynamic RESTORE words may be supplied from real S read responses.
module m_short_command_tx(
 input logic clk,reset,
 input logic cmd_valid,output logic cmd_ready,
 input logic [3:0] cmd_opcode,cmd_scope,
 input logic [15:0] cmd_scope_generation,cmd_high16,
 input logic [31:0] cmd_session,cmd_record,
 input logic [1:0] cmd_bank,
 output logic [2:0] word_index,
 input logic payload_valid,output logic payload_ready,input logic [127:0] payload_data,
 output logic lc_valid,input logic lc_ready,output logic lc_sop,lc_eop,output logic [127:0] lc_data,
 output logic reject_valid,input logic reject_ready,output logic [7:0] reject_status
);
 logic [3:0] length;
 logic [127:0] header;
 logic bad;
 always_comb begin
   case(cmd_opcode)
     1,5:length=8;
     2,3:length=2;
     4,6,7,8:length=1;
     default:length=0;
   endcase
   bad=length==0||cmd_session==0||
       ((cmd_opcode!=6&&cmd_opcode!=7)&&cmd_bank!=0)||
       ((cmd_opcode!=4&&cmd_opcode!=6&&cmd_opcode!=7)&&cmd_high16!=0)||
       (cmd_opcode==4&&(cmd_high16!=0&&cmd_high16!=3&&cmd_high16!=4))||
       (cmd_opcode==8&&(cmd_record!=0||cmd_scope!=0||cmd_scope_generation!=0));
   header=0;header[15:0]=16'h4d02;header[19:16]=cmd_opcode;header[23:20]=length;
   header[27:24]=cmd_scope;header[29:28]=cmd_bank;header[63:32]=cmd_session;
   header[95:64]=cmd_record;header[111:96]=cmd_scope_generation;header[127:112]=cmd_high16;
 end
 assign lc_valid=!reset&&cmd_valid&&!bad&&(word_index==0||payload_valid);
 assign lc_sop=word_index==0;
 assign lc_eop={1'b0,word_index}==length-1'b1;
 assign lc_data=word_index==0?header:payload_data;
 assign payload_ready=!reset&&cmd_valid&&!bad&&word_index!=0&&lc_ready;
 assign reject_valid=!reset&&cmd_valid&&bad;
 assign reject_status=8'd1;
 assign cmd_ready=!reset&&(bad?reject_ready:(lc_ready&&lc_valid&&lc_eop));
 always_ff @(posedge clk)begin
   if(reset)word_index<=0;
   else if(cmd_valid&&cmd_ready)word_index<=0;
   else if(lc_valid&&lc_ready)word_index<=word_index+1'b1;
 end
endmodule
