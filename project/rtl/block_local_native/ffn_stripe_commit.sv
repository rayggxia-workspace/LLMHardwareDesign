`timescale 1ns/1ps
// One outstanding stripe. P providers return after actual FINAL S writes;
// after all three correct terminals the one COPY service scatters six
// fragments. The outer ring sees commit only after all six true ACK proofs.
module ffn_stripe_commit(
 input wire clk,reset,
 input wire stripe_valid,output wire stripe_ready,input wire [63:0] stripe_owner,
 input wire [15:0] stripe_first,input wire [7:0] stripe_width,
 output wire [2:0] project_valid,input wire [2:0] project_ready,
 output wire [63:0] project_owner,output wire [47:0] project_first,
 output wire [11:0] project_groups,
 input wire [2:0] project_done_valid,output wire [2:0] project_done_ready,
 input wire [191:0] project_done_owner,input wire [47:0] project_done_first,
 input wire [14:0] project_done_gate_words,project_done_up_words,
 input wire [2:0] project_done_error,
 output wire copy_stage,copy_valid,input wire copy_ready,
 output wire [1:0] copy_source,output wire [127:0] copy_key,
 output wire [15:0] copy_generation,output wire [31:0] copy_first,
 output wire [9:0] copy_scratch,copy_ring,
 output wire [4:0] copy_words,
 input wire copy_done_valid,output wire copy_done_ready,
 input wire [127:0] copy_done_key,input wire [10:0] copy_done_prefix,input wire copy_done_error,
 output wire commit_valid,input wire commit_ready,
 output wire [63:0] commit_owner,output wire [15:0] commit_first,output reg commit_error,
 output reg [31:0] rejected_terminals
);
 localparam [2:0] IDLE=0,PROJ=1,SEND=2,WAIT_COPY=3,COMMIT=4;
 reg [2:0] phase,issued,retired;
 reg [63:0] owner;
 reg [15:0] first,epoch;
 reg [7:0] width;
 reg [1:0] source;
 reg way;
 wire width_legal=stripe_width==8'd64||stripe_width==8'd128||stripe_width==8'd192;
 // All supported widths divide into N8 groups, interleaved P0/P1/P2.
 function automatic [3:0] groups(input [7:0] w,input [1:0] p);
  case(w)
   8'd64:groups=p==2 ? 4'd2 : 4'd3;
   8'd128:groups=p==0 ? 4'd6 : 4'd5;
   8'd192:groups=4'd8;
   default:groups=0;
  endcase
 endfunction
 function automatic [15:0] col(input [15:0] base,input [1:0] p);
  col=base+{11'd0,p,3'd0};
 endfunction

 assign stripe_ready=!reset&&phase==IDLE;
 assign project_valid=!reset&&phase==PROJ ? ~issued : 3'b000;
 wire [2:0] project_fire=project_valid&project_ready;
 assign project_done_ready=!reset&&phase==PROJ ? (issued|project_fire)&~retired : 3'b000;
 assign project_owner=owner;
 wire [2:0] matching,bad_count,terminal_fire,foreign_terminal;
 for(genvar p=0;p<3;p=p+1)begin: ports
  wire [3:0] n=groups(width,2'(p));
  assign project_first[16*p+:16]=col(first,2'(p));
  assign project_groups[4*p+:4]=n;
  assign matching[p]=project_done_owner[64*p+:64]==owner&&project_done_first[16*p+:16]==col(first,2'(p));
  assign terminal_fire[p]=project_done_valid[p]&&project_done_ready[p]&&matching[p];
  assign foreign_terminal[p]=project_done_valid[p]&&project_done_ready[p]&&!matching[p];
  assign bad_count[p]=project_done_gate_words[5*p+:5]!={n,1'b0}||project_done_up_words[5*p+:5]!={n,1'b0};
 end
 wire project_failure=|(terminal_fire&(bad_count|project_done_error));
 assign copy_stage=!reset&&(phase==SEND||phase==WAIT_COPY);
 assign copy_valid=!reset&&phase==SEND&&epoch!=16'hffff;
 assign copy_done_ready=!reset&&phase==WAIT_COPY;
 assign copy_source=source;
 assign copy_key={owner,first,way,source,45'h46464e010};
 assign copy_generation=epoch+16'd1;
 assign copy_first={16'd0,col(first,source)};
 assign copy_scratch=way ? 10'd912 : 10'd896;
 assign copy_ring=way ? 10'd784 : 10'd720;
 assign copy_words={groups(width,source),1'b0};
 assign commit_valid=!reset&&phase==COMMIT;
 assign commit_owner=owner;
 assign commit_first=first;
 wire rejected_copy=copy_done_valid&&copy_done_ready&&copy_done_key!=copy_key;
 always @(posedge clk)begin
  if(reset)begin
   phase<=IDLE;owner<=0;first<=0;width<=0;issued<=0;retired<=0;source<=0;way<=0;epoch<=0;
   commit_error<=0;rejected_terminals<=0;
  end else begin
   rejected_terminals<=rejected_terminals+{31'd0,rejected_copy}+
    {31'd0,foreign_terminal[0]}+{31'd0,foreign_terminal[1]}+{31'd0,foreign_terminal[2]};
   case(phase)
    IDLE:if(stripe_valid&&stripe_ready)begin
     owner<=stripe_owner;first<=stripe_first;width<=stripe_width;
     issued<=0;retired<=0;source<=0;way<=0;
     // 11008 columns total, all actual stripes are N8 aligned.
     if(!width_legal||stripe_first[2:0]!=0||{1'b0,stripe_first}+{9'd0,stripe_width}>17'd11008)begin
      commit_error<=1;phase<=COMMIT;
     end else begin commit_error<=0;phase<=PROJ;end
    end
    PROJ:begin
     issued<=issued|project_fire;retired<=retired|terminal_fire;
     if(project_failure)commit_error<=1;
     if((retired|terminal_fire)==3'b111)phase<=commit_error||project_failure ? COMMIT : SEND;
    end
    SEND:if(epoch==16'hffff)begin phase<=COMMIT;commit_error<=1;end
    else if(copy_valid&&copy_ready)phase<=WAIT_COPY;
    WAIT_COPY:if(copy_done_valid&&copy_done_ready&&!rejected_copy)begin
     epoch<=epoch+16'd1;
     if(copy_done_error||copy_done_prefix!={6'd0,copy_words})begin phase<=COMMIT;commit_error<=1;end
     else if(source==2&&way)phase<=COMMIT;
     else begin
      phase<=SEND;
      if(source==2)begin source<=0;way<=1;end else source<=source+2'd1;
     end
    end
    COMMIT:if(commit_valid&&commit_ready)phase<=IDLE;
    default:phase<=IDLE;
   endcase
  end
 end
endmodule
