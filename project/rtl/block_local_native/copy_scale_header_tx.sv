// Two metadata frames precede an A16 K128 tile on the existing 128-bit
// copy link. Header tags reserve bit15 of the old low16 namespace; S data
// tags keep it zero. No extra data bus or SRAM. Payload is held until ACK.
// Source registration comes from true 16-word producer ACK, not a timer.
module copy_scale_header_tx(
 input wire clk,reset,halt,
 input wire start_valid,output wire start_ready,
 input wire [127:0] start_key,
 input wire [15:0] start_generation,start_kk,
 input wire [31:0] start_session,start_ticket,
 input wire [5:0] start_shift,
 input wire [2:0] start_mask,
 input wire [15:0] start_written_mask,input wire start_producer_error,
 output wire [2:0] frame_valid,input wire [2:0] frame_ready,
 output wire [95:0] frame_tag,output wire [383:0] frame_data,
 input wire [2:0] ack_valid,output wire [2:0] ack_ready,
 input wire [95:0] ack_tag,input wire [2:0] ack_error,
 output reg done_valid,input wire done_ready,output reg done_error,
 output wire quiescent,output reg [31:0] rejected_ack
);
 reg active,failed;
 reg [127:0] key_q;
 reg [15:0] generation_q,last_generation,kk_q;
 reg [31:0] session_q,ticket_q;
 reg [5:0] shift_q;
 reg [2:0] mask_q,offer,sent,phase,completed;
 wire [2:0] matching_ack,bad_ack;
 wire any_ack_error=|(ack_valid&matching_ack&ack_error);
 wire [2:0] bad_count={2'd0,bad_ack[0]}+{2'd0,bad_ack[1]}+{2'd0,bad_ack[2]};
 wire [127:0] header={16'h0251,16'd256,kk_q,shift_q,10'd0,session_q,ticket_q};
 wire bad_start=start_generation<=last_generation || start_mask==0 ||
     start_kk[6:0]!=0 || start_shift>17 || start_written_mask!=16'hffff || start_producer_error;
 assign start_ready=!reset&&!halt&&!active&&!done_valid&&offer==0&&sent==0;
 assign frame_valid=offer&{3{!reset}};
 assign ack_ready={3{!reset}};
 assign quiescent=!active&&!done_valid&&offer==0&&sent==0;
 for(genvar p=0;p<3;p=p+1)begin:ports
  assign frame_tag[p*32+:32]={generation_q,5'b10000,10'd0,phase[p]};
  assign frame_data[p*128+:128]=phase[p] ? header : key_q;
  assign matching_ack[p]=active&&sent[p]&&mask_q[p]&&
        ack_tag[p*32+:32]=={generation_q,5'b10000,10'd0,phase[p]};
  assign bad_ack[p]=ack_valid[p]&&ack_ready[p]&&!matching_ack[p];
 end
 always @(posedge clk)begin
  if(reset)begin
   active<=0;failed<=0;key_q<=0;generation_q<=0;last_generation<=0;
   kk_q<=0;session_q<=0;ticket_q<=0;shift_q<=0;
   mask_q<=0;offer<=0;sent<=0;phase<=0;completed<=0;
   done_valid<=0;done_error<=0;rejected_ack<=0;
  end else begin
   if(done_valid&&done_ready)done_valid<=0;
   if(start_valid&&start_ready)begin
    if(start_generation>last_generation)last_generation<=start_generation;
    if(bad_start)begin done_valid<=1;done_error<=1;end
    else begin
     active<=1;failed<=0;key_q<=start_key;generation_q<=start_generation;
     kk_q<=start_kk;session_q<=start_session;ticket_q<=start_ticket;shift_q<=start_shift;
     mask_q<=start_mask;offer<=start_mask;sent<=0;phase<=0;completed<=0;
    end
   end
   if(active&&halt)failed<=1;
   if(bad_count!=0)rejected_ack<=rejected_ack+{29'd0,bad_count};
   for(integer p=0;p<3;p=p+1)begin
    if(frame_valid[p]&&frame_ready[p])begin offer[p]<=0;sent[p]<=1;end
    if(ack_valid[p]&&ack_ready[p])begin
     if(matching_ack[p])begin
      sent[p]<=0;
      if(ack_error[p])failed<=1;
      else if(phase[p])completed[p]<=1;
      else if(!failed&&!halt&&!any_ack_error)begin
       phase[p]<=1;offer[p]<=1;
      end
     end
    end
   end
   // A held offer is never withdrawn by halt/error. Drain all accepted and
   // proffered headers before reporting a failed prelude.
   if(active&&offer==0&&sent==0&&((completed&mask_q)==mask_q||failed||halt))begin
    active<=0;done_valid<=1;done_error<=failed||halt;
   end
  end
 end
endmodule
