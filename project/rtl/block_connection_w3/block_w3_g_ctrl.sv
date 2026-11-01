// Issue151 W3: gather one S16 word, stream ordered pairs through external G,
// collect all in-flight responses, then scatter once and consume the write ACK.
// The top retains the S owner lease until rsp is consumed. No standalone cancel.
module block_w3_g_ctrl(
 input wire clk,reset,
 input wire req_valid,output wire req_ready,
 input wire [2:0] req_fn,input wire req_gated,
 input wire [3:0] req_count,
 input wire [9:0] req_src_a,req_src_b,req_dst,
 output wire rsp_valid,input wire rsp_ready,
 output wire rsp_error,rsp_saturated,
 output wire mem_req_valid,input wire mem_req_ready,
 output wire mem_req_write,output wire [9:0] mem_req_addr,
 output wire [127:0] mem_req_data,
 input wire mem_rsp_valid,output wire mem_rsp_ready,
 input wire [127:0] mem_rsp_data,input wire mem_rsp_error,
 output wire g_in_valid,input wire g_in_ready,
 output wire [2:0] g_in_fn,output wire g_in_gated,
 output wire [31:0] g_in_x,g_in_gate,
 input wire g_out_valid,output wire g_out_ready,
 input wire [31:0] g_out_data,
 input wire g_out_error,g_out_saturated
);
 localparam [3:0] IDLE=0,READ_REQ=1,READ_RSP=2,STREAM=3,
                  WRITE_REQ=4,WRITE_RSP=5,RESPONSE=6;
 reg [3:0] state,count_hold;
 reg [2:0] fn_hold,total_pairs,issued,retired;
 reg gated_hold,operand,error_hold,saturated_hold;
 reg [9:0] src_a_hold,src_b_hold,dst_hold;
 reg [127:0] a_hold,b_hold,result_hold;
 integer lane;

 function automatic [127:0] mask_word;
  input [127:0] data;
  input [3:0] count;
  integer j;
  begin
   mask_word=0;
   for(j=0;j<8;j=j+1)
    if(j<count)mask_word[16*j+:16]=data[16*j+:16];
  end
 endfunction

 assign req_ready=!reset&&state==IDLE;
 assign rsp_valid=!reset&&state==RESPONSE;
 assign rsp_error=error_hold;
 assign rsp_saturated=saturated_hold;
 assign mem_req_valid=!reset&&(state==READ_REQ||state==WRITE_REQ);
 assign mem_req_write=state==WRITE_REQ;
 assign mem_req_addr=state==WRITE_REQ?dst_hold:operand?src_b_hold:src_a_hold;
 assign mem_req_data=result_hold;
 assign mem_rsp_ready=!reset&&(state==READ_RSP||state==WRITE_RSP);
 assign g_in_valid=!reset&&state==STREAM&&issued<total_pairs;
 assign g_in_fn=fn_hold;
 assign g_in_gated=gated_hold;
 assign g_in_x=a_hold[32*issued[1:0]+:32];
 assign g_in_gate=b_hold[32*issued[1:0]+:32];
 // issued/retired count accepts, never an assumed fixed pipeline latency.
 assign g_out_ready=!reset&&state==STREAM&&retired<issued;

 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;count_hold<=0;fn_hold<=0;gated_hold<=0;operand<=0;
   total_pairs<=0;issued<=0;retired<=0;error_hold<=0;saturated_hold<=0;
   src_a_hold<=0;src_b_hold<=0;dst_hold<=0;
   a_hold<=0;b_hold<=0;result_hold<=0;
  end else case(state)
   IDLE:if(req_valid&&req_ready)begin
    fn_hold<=req_fn;gated_hold<=req_gated;count_hold<=req_count;
    src_a_hold<=req_src_a;src_b_hold<=req_src_b;dst_hold<=req_dst;
    total_pairs<=({1'b0,req_count}+5'd1)>>1;
    issued<=0;retired<=0;operand<=0;error_hold<=0;saturated_hold<=0;
    a_hold<=0;b_hold<=0;result_hold<=0;
    // Unsupported fn4..7 is submitted to native G and drained as an error.
    if(req_count==0||req_count>8)begin error_hold<=1;state<=RESPONSE;end
    else state<=READ_REQ;
   end
   READ_REQ:if(mem_req_valid&&mem_req_ready)state<=READ_RSP;
   READ_RSP:if(mem_rsp_valid&&mem_rsp_ready)begin
    if(mem_rsp_error)begin error_hold<=1;state<=RESPONSE;end
    else begin
     if(!operand)a_hold<=mask_word(mem_rsp_data,count_hold);
     else b_hold<=mask_word(mem_rsp_data,count_hold);
     if(!operand&&gated_hold)begin operand<=1;state<=READ_REQ;end
     else state<=STREAM;
    end
   end
   STREAM:begin
    if(g_in_valid&&g_in_ready)issued<=issued+1'b1;
    if(g_out_valid&&g_out_ready)begin
     error_hold<=error_hold||g_out_error;
     saturated_hold<=saturated_hold||g_out_saturated;
     for(lane=0;lane<2;lane=lane+1)begin
      if(2*retired+lane<count_hold)
       result_hold[32*retired+16*lane+:16]<=g_out_data[16*lane+:16];
     end
     retired<=retired+1'b1;
     if(retired+1'b1==total_pairs)begin
      if(error_hold||g_out_error)state<=RESPONSE;
      else state<=WRITE_REQ;
     end
    end
   end
   WRITE_REQ:if(mem_req_valid&&mem_req_ready)state<=WRITE_RSP;
   WRITE_RSP:if(mem_rsp_valid&&mem_rsp_ready)begin
    error_hold<=error_hold||mem_rsp_error;state<=RESPONSE;
   end
   RESPONSE:if(rsp_valid&&rsp_ready)state<=IDLE;
   default:begin error_hold<=1;state<=RESPONSE;end
  endcase
 end
endmodule
