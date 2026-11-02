// Issue151 W4: one non-interleaved S-backed N group, bounded to 1..1024 S16; new module, old controller unchanged.
// Caller owns the S helper and immutable source/gamma regions through rsp take.
// A runtime native/memory error poisons reuse until coordinated ctrl/N/helper
// reset. Admission errors before BEGIN do not modify N or poison the service.
module block_w4_n_long_ctrl(
 input wire clk,reset,
 input wire req_valid,output wire req_ready,
 input wire [1:0] req_mode,input wire [15:0] req_count,
 input wire [31:0] req_epsilon,
 input wire [9:0] req_src_addr,req_gamma_addr,req_exp_addr,req_dst_addr,
 output wire rsp_valid,input wire rsp_ready,
 output wire rsp_error,rsp_saturated,output wire busy,
 output wire n_cmd_valid,input wire n_cmd_ready,
 output wire [3:0] n_cmd_op,n_cmd_count,
 output wire [31:0] n_cmd_param,
 output wire [127:0] n_cmd_data,n_cmd_aux,
 input wire n_rsp_valid,output wire n_rsp_ready,
 input wire [127:0] n_rsp_data,
 input wire n_rsp_error,n_rsp_saturated,
 output wire mem_req_valid,input wire mem_req_ready,
 output wire mem_req_write,output wire [9:0] mem_req_addr,
 output wire [127:0] mem_req_data,
 input wire mem_rsp_valid,output wire mem_rsp_ready,
 input wire [127:0] mem_rsp_data,input wire mem_rsp_error
);
 localparam [2:0] IDLE=0,N_REQ=1,N_RSP=2,MEM_REQ=3,MEM_RSP=4,RESPONSE=5;
 localparam [2:0] FLOW_BEGIN=0,FLOW_STATS=1,FLOW_FINAL_STATS=2,
                  FLOW_EXP=3,FLOW_FINAL_EXP=4,FLOW_REPLAY=5;
 localparam [2:0] READ_SRC=0,READ_GAMMA=1,READ_EXP=2,WRITE_EXP=3,WRITE_DST=4;
 reg [2:0] state,flow,access_kind;
 reg [1:0] mode_hold;
 reg [15:0] count_hold;
 reg [31:0] epsilon_hold;
 reg [9:0] src_hold,gamma_hold,exp_hold,dst_hold;
 reg [7:0] words_hold,word_index;
 reg [3:0] cmd_op_hold,cmd_count_hold;
 reg [31:0] cmd_param_hold;
 reg [127:0] cmd_data_hold,cmd_aux_hold,raw_hold,result_hold;
 reg error_hold,saturated_hold,poisoned;

 // Extended arithmetic prevents address/count wrap from passing admission.
 wire [16:0] request_words=({1'b0,req_count}+17'd7)>>3;
 wire [15:0] remaining=count_hold-({8'd0,word_index}<<3);
 wire [3:0] chunk_count=remaining>8?4'd8:remaining[3:0];
 wire last_word={1'b0,word_index}+9'd1=={1'b0,words_hold};
 function automatic range_fits;
  input [9:0] base;
  input [16:0] words;
  begin range_fits=({7'd0,base}+words)<=17'd1024;end
 endfunction
 function automatic disjoint;
  input [9:0] a,b;
  input [16:0] words;
  begin
   disjoint=({7'd0,a}+words)<={7'd0,b}||({7'd0,b}+words)<={7'd0,a};
  end
 endfunction
 wire admission_ok=req_mode<=2&&req_count>=1&&req_count<=1024&&
  (req_mode==0||req_epsilon!=0)&&range_fits(req_src_addr,request_words)&&
  range_fits(req_dst_addr,request_words)&&
  disjoint(req_src_addr,req_dst_addr,request_words)&&
  (req_mode==0?
   (range_fits(req_exp_addr,request_words)&&
    disjoint(req_src_addr,req_exp_addr,request_words)&&
    disjoint(req_exp_addr,req_dst_addr,request_words)):
   (range_fits(req_gamma_addr,request_words)&&
    disjoint(req_src_addr,req_gamma_addr,request_words)&&
    disjoint(req_gamma_addr,req_dst_addr,request_words)));

 function automatic [127:0] mask_tail;
  input [127:0] data;
  input [3:0] count;
  integer lane;
  begin
   mask_tail=0;
   for(lane=0;lane<8;lane=lane+1)
    if(lane<count)mask_tail[16*lane+:16]=data[16*lane+:16];
  end
 endfunction

 assign req_ready=!reset&&state==IDLE&&!poisoned;
 assign rsp_valid=!reset&&state==RESPONSE;
 assign rsp_error=error_hold;
 assign rsp_saturated=saturated_hold;
 // Poison is a reset-required lock, including after the error rsp is consumed.
 assign busy=!reset&&(state!=IDLE||poisoned);
 assign n_cmd_valid=!reset&&state==N_REQ;
 assign n_cmd_op=cmd_op_hold;
 assign n_cmd_count=cmd_count_hold;
 assign n_cmd_param=cmd_param_hold;
 assign n_cmd_data=cmd_data_hold;
 assign n_cmd_aux=cmd_aux_hold;
 assign n_rsp_ready=!reset&&state==N_RSP;
 assign mem_req_valid=!reset&&state==MEM_REQ;
 assign mem_req_write=access_kind==WRITE_EXP||access_kind==WRITE_DST;
 assign mem_req_addr=(access_kind==READ_GAMMA?gamma_hold:
                      access_kind==READ_EXP||access_kind==WRITE_EXP?exp_hold:
                      access_kind==WRITE_DST?dst_hold:src_hold)+{2'd0,word_index};
 assign mem_req_data=result_hold;
 assign mem_rsp_ready=!reset&&state==MEM_RSP;

 task automatic issue_n;
  input [3:0] op,count;
  input [31:0] param;
  input [127:0] data,aux;
  begin
   cmd_op_hold<=op;cmd_count_hold<=count;cmd_param_hold<=param;
   cmd_data_hold<=data;cmd_aux_hold<=aux;state<=N_REQ;
  end
 endtask
 task automatic fail_service;
  begin error_hold<=1;poisoned<=1;state<=RESPONSE;end
 endtask

 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;flow<=FLOW_BEGIN;access_kind<=READ_SRC;
   mode_hold<=0;count_hold<=0;epsilon_hold<=0;
   src_hold<=0;gamma_hold<=0;exp_hold<=0;dst_hold<=0;
   words_hold<=0;word_index<=0;
   cmd_op_hold<=0;cmd_count_hold<=0;cmd_param_hold<=0;
   cmd_data_hold<=0;cmd_aux_hold<=0;raw_hold<=0;result_hold<=0;
   error_hold<=0;saturated_hold<=0;poisoned<=0;
  end else case(state)
   IDLE:if(req_valid&&req_ready)begin
    mode_hold<=req_mode;count_hold<=req_count;epsilon_hold<=req_epsilon;
    src_hold<=req_src_addr;gamma_hold<=req_gamma_addr;
    exp_hold<=req_exp_addr;dst_hold<=req_dst_addr;
    words_hold<=request_words[7:0];word_index<=0;flow<=FLOW_BEGIN;
    raw_hold<=0;result_hold<=0;error_hold<=0;saturated_hold<=0;
    if(!admission_ok)begin error_hold<=1;state<=RESPONSE;end
    else issue_n(4'd0,4'd0,{30'd0,req_mode},{96'd0,req_epsilon},128'd0);
   end
   N_REQ:if(n_cmd_valid&&n_cmd_ready)state<=N_RSP;
   N_RSP:if(n_rsp_valid&&n_rsp_ready)begin
    saturated_hold<=saturated_hold||n_rsp_saturated;
    if(n_rsp_error)fail_service();
    else case(cmd_op_hold)
     0:begin flow<=FLOW_STATS;word_index<=0;access_kind<=READ_SRC;state<=MEM_REQ;end
     1:if(last_word)begin
       flow<=FLOW_FINAL_STATS;issue_n(4'd2,4'd0,32'd0,128'd0,128'd0);
      end else begin word_index<=word_index+1'b1;access_kind<=READ_SRC;state<=MEM_REQ;end
     2:begin
      word_index<=0;access_kind<=READ_SRC;state<=MEM_REQ;
      flow<=mode_hold==0?FLOW_EXP:FLOW_REPLAY;
     end
     3:begin
      // Preserve U16 EXP bits exactly, including code32768; no signed cast.
      result_hold<=mask_tail(n_rsp_data,chunk_count);access_kind<=WRITE_EXP;state<=MEM_REQ;
     end
     4:begin flow<=FLOW_REPLAY;word_index<=0;access_kind<=READ_EXP;state<=MEM_REQ;end
     5,6:begin
      result_hold<=mask_tail(n_rsp_data,chunk_count);access_kind<=WRITE_DST;state<=MEM_REQ;
     end
     default:fail_service();
    endcase
   end
   MEM_REQ:if(mem_req_valid&&mem_req_ready)state<=MEM_RSP;
   MEM_RSP:if(mem_rsp_valid&&mem_rsp_ready)begin
    if(mem_rsp_error)fail_service();
    else case(access_kind)
     READ_SRC:begin
      raw_hold<=mask_tail(mem_rsp_data,chunk_count);
      if(flow==FLOW_STATS)
       issue_n(4'd1,chunk_count,32'd0,mask_tail(mem_rsp_data,chunk_count),128'd0);
      else if(flow==FLOW_EXP)
       issue_n(4'd3,chunk_count,32'd0,mask_tail(mem_rsp_data,chunk_count),128'd0);
      else if(flow==FLOW_REPLAY&&mode_hold!=0)begin access_kind<=READ_GAMMA;state<=MEM_REQ;end
      else fail_service();
     end
     READ_GAMMA:issue_n(4'd5,chunk_count,32'd0,raw_hold,mask_tail(mem_rsp_data,chunk_count));
     READ_EXP:issue_n(4'd6,chunk_count,32'd0,mask_tail(mem_rsp_data,chunk_count),128'd0);
     WRITE_EXP:if(last_word)begin
       flow<=FLOW_FINAL_EXP;issue_n(4'd4,4'd0,32'd0,128'd0,128'd0);
      end else begin word_index<=word_index+1'b1;access_kind<=READ_SRC;state<=MEM_REQ;end
     WRITE_DST:if(last_word)begin error_hold<=0;state<=RESPONSE;end
      else begin
       word_index<=word_index+1'b1;access_kind<=mode_hold==0?READ_EXP:READ_SRC;state<=MEM_REQ;
      end
     default:fail_service();
    endcase
   end
   RESPONSE:if(rsp_valid&&rsp_ready)state<=IDLE;
   default:fail_service();
  endcase
 end
endmodule
