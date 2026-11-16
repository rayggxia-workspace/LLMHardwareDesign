`timescale 1ns/1ps
// One ordinary U S128 read in flight; one 16B holding register per P.
// A prefetched source response may backpressure at the existing U provider
// while old destination ACKs drain. No private wide port or extra data FIFO.
module early_copy_3p #(
  // A source that also receives this COPY shares one ordered S response
  // stream. Prefetching its next read can block the old write ACK behind
  // that response while all payload holds still wait for those ACKs.
  parameter logic PREFETCH_NEXT_WORD=1'b1
)(
  input logic clk,reset,halt,
  input logic start_valid,output logic start_ready,
  input logic [127:0] start_key,
  input logic [15:0] start_generation,
  input logic [9:0] start_U_base,
  input logic [29:0] start_P_bases,
  input logic [10:0] start_words,
  input logic [2:0] start_P_mask,
  input logic destination_window_released,
  output logic u_valid,input logic u_ready,
  output logic [9:0] u_address,output logic [31:0] u_tag,
  input logic u_response_valid,output logic u_response_ready,
  input logic [31:0] u_response_tag,
  input logic [127:0] u_response_data,input logic u_response_error,
  output logic [2:0] p_valid,input logic [2:0] p_ready,
  output logic [29:0] p_address,output logic [95:0] p_tag,
  output logic [383:0] p_data,
  input logic [2:0] p_ack_valid,output logic [2:0] p_ack_ready,
  input logic [95:0] p_ack_tag,input logic [2:0] p_ack_error,
  output logic [127:0] copy_key,
  output logic [32:0] copy_committed_prefix,
  output logic done_valid,input logic done_ready,output logic done_error,
  output logic quiescent,output logic [31:0] fault_cycles,
  output logic [31:0] committed_words
);
  logic active,failed,request_pending,inflight;
  logic [127:0] key_q;
  logic [15:0] generation_q,last_generation;
  logic [9:0] U_base;
  logic [9:0] P_base[3];
  logic [10:0] words,issued;
  logic [2:0] P_mask,hold_full,hold_sent;
  logic [127:0] hold_data[3];
  logic [31:0] hold_tag[3],request_tag;
  logic [9:0] hold_index[3],request_index;
  logic [10:0] committed[3];
  logic [2:0] ack_match;
  logic [3:0] commits_now;
  logic bad_start,bad_u,bad_ack;
  wire matching_u=inflight&&u_response_tag==request_tag;
  wire start_shape=start_generation>last_generation&&start_words!=0&&
      start_words<=1024&&start_P_mask!=0&&
      {1'b0,start_U_base}+start_words<=11'd1024&&
      (!start_P_mask[0]||{1'b0,start_P_bases[9:0]}+start_words<=11'd1024)&&
      (!start_P_mask[1]||{1'b0,start_P_bases[19:10]}+start_words<=11'd1024)&&
      (!start_P_mask[2]||{1'b0,start_P_bases[29:20]}+start_words<=11'd1024);
  assign start_ready=!reset&&!halt&&!active&&!done_valid&&
      !request_pending&&!inflight&&hold_full==0&&destination_window_released;
  assign u_valid=!reset&&request_pending;
  assign u_address=U_base+request_index;
  assign u_tag=request_tag;
  assign u_response_ready=!reset&&(!matching_u||u_response_error||halt||failed||hold_full==0);
  assign p_ack_ready={3{!reset}};
  assign copy_key=key_q;
  assign copy_committed_prefix={committed[2],committed[1],committed[0]};
  assign quiescent=!active&&!done_valid&&!request_pending&&!inflight&&hold_full==0;
  always_comb begin
    commits_now=0;bad_ack=0;
    for(integer i=0;i<3;i=i+1) begin
      p_valid[i]=!reset&&hold_full[i]&&!hold_sent[i];
      p_address[10*i+:10]=P_base[i]+hold_index[i];
      p_tag[32*i+:32]=hold_tag[i];p_data[128*i+:128]=hold_data[i];
      ack_match[i]=hold_full[i]&&hold_sent[i]&&p_ack_tag[32*i+:32]==hold_tag[i];
      if(p_ack_valid[i]&&p_ack_ready[i]) begin
        if(!ack_match[i]) bad_ack=1;
        else if(!p_ack_error[i]) commits_now=commits_now+1'b1;
      end
    end
    bad_start=start_valid&&start_ready&&!start_shape;
    bad_u=u_response_valid&&u_response_ready&&!matching_u;
  end
  always_ff @(posedge clk) begin
    if(reset) begin
      active<=0;failed<=0;request_pending<=0;inflight<=0;
      key_q<=0;generation_q<=0;last_generation<=0;U_base<=0;
      words<=0;issued<=0;P_mask<=0;hold_full<=0;hold_sent<=0;
      request_tag<=0;request_index<=0;done_valid<=0;done_error<=0;
      fault_cycles<=0;committed_words<=0;
      for(integer i=0;i<3;i=i+1) begin P_base[i]<=0;hold_data[i]<=0;hold_tag[i]<=0;hold_index[i]<=0;committed[i]<=0;end
    end else begin
      if(bad_start||bad_u||bad_ack) fault_cycles<=fault_cycles+1'b1;
      if(commits_now!=0) committed_words<=committed_words+{28'd0,commits_now};
      if(done_valid&&done_ready) done_valid<=0;
      if(start_valid&&start_ready) begin
        if(start_generation>last_generation) last_generation<=start_generation;
        if(!start_shape) begin done_valid<=1;done_error<=1;end
        else begin
          active<=1;failed<=0;key_q<=start_key;generation_q<=start_generation;
          U_base<=start_U_base;words<=start_words;issued<=0;P_mask<=start_P_mask;
          for(integer i=0;i<3;i=i+1) begin P_base[i]<=start_P_bases[10*i+:10];committed[i]<=0;end
        end
      end
      if(active&&!done_valid&&!halt&&!failed&&!request_pending&&!inflight&&issued<words&&
         (PREFETCH_NEXT_WORD||hold_full==0)) begin
        request_pending<=1;request_index<=issued[9:0];request_tag<={generation_q,5'd0,issued};
      end
      // Proposed source valid survives cancellation. Its response is then
      // consumed/discarded, never written into a fresh epoch.
      if(u_valid&&u_ready) begin request_pending<=0;inflight<=1;issued<=issued+1'b1;end
      if(u_response_valid&&u_response_ready&&matching_u) begin
        inflight<=0;
        if(u_response_error) failed<=1;
        else if(!halt&&!failed) begin
          for(integer i=0;i<3;i=i+1) begin
            if(P_mask[i]) begin hold_full[i]<=1;hold_sent[i]<=0;hold_data[i]<=u_response_data;hold_tag[i]<=request_tag;hold_index[i]<=request_index;end
          end
        end
      end
      for(integer i=0;i<3;i=i+1) begin
        if(p_valid[i]&&p_ready[i]) hold_sent[i]<=1;
        if(p_ack_valid[i]&&p_ack_ready[i]&&ack_match[i]) begin
          hold_full[i]<=0;hold_sent[i]<=0;
          if(p_ack_error[i]) failed<=1;
          else if({1'b0,hold_index[i]}==committed[i]) committed[i]<=committed[i]+1'b1;
          else failed<=1;
        end
      end
      if(active&&!request_pending&&!inflight&&hold_full==0&&
         (issued==words||halt||failed)) begin
        active<=0;done_valid<=1;done_error<=halt||failed;
      end
    end
  end
endmodule
