// Issue151 W3: bounded one-word E gather/execute/scatter service.
// The caller retains the ordinary-S owner lease until rsp is consumed.
// Native E is external. reset must be coordinated with E and the S helper.
module block_w3_e_ctrl(
 input wire clk,reset,
 input wire req_valid,output wire req_ready,
 input wire [3:0] req_op,input wire [4:0] req_shift,
 input wire [3:0] req_count,
 input wire [9:0] req_src_a,req_src_b,req_src_c,req_dst,
 output wire rsp_valid,input wire rsp_ready,
 output wire rsp_error,rsp_saturated,
 output wire mem_req_valid,input wire mem_req_ready,
 output wire mem_req_write,output wire [9:0] mem_req_addr,
 output wire [127:0] mem_req_data,
 input wire mem_rsp_valid,output wire mem_rsp_ready,
 input wire [127:0] mem_rsp_data,input wire mem_rsp_error,
 output wire e_in_valid,input wire e_in_ready,
 output wire [3:0] e_in_op,output wire [4:0] e_in_shift,
 output wire [127:0] e_in_a,e_in_b,e_in_c,
 input wire e_out_valid,output wire e_out_ready,
 input wire [127:0] e_out_data,
 input wire e_out_error,e_out_saturated
);
 localparam [3:0] IDLE=0,READ_REQ=1,READ_RSP=2,ISSUE=3,
                  CAPTURE=4,WRITE_REQ=5,WRITE_RSP=6,RESPONSE=7;
 reg [3:0] state,op_hold,count_hold;
 reg [4:0] shift_hold;
 reg [9:0] src_a_hold,src_b_hold,src_c_hold,dst_hold;
 reg [1:0] operand;
 reg need_b,need_c,error_hold,saturated_hold;
 reg [127:0] a_hold,b_hold,c_hold,result_hold;

 function automatic uses_b;
  input [3:0] op;
  begin case(op)
   0,1,2,3,4,5,6,9:uses_b=1'b1;
   default:uses_b=1'b0;
  endcase end
 endfunction
 function automatic uses_c;
  input [3:0] op;
  begin uses_c=op==3||op==6;end
 endfunction
 function automatic [127:0] input_mask;
  input [127:0] data;
  input [3:0] op,count;
  integer lane;
  begin
   input_mask=0;
   for(lane=0;lane<8;lane=lane+1)begin
    if(op==13)begin
     if(lane<4&&lane<count)input_mask[32*lane+:32]=data[32*lane+:32];
    end else if(lane<count)input_mask[16*lane+:16]=data[16*lane+:16];
   end
  end
 endfunction
 function automatic [127:0] output_mask;
  input [127:0] data;
  input [3:0] op,count;
  integer lane;
  begin
   output_mask=0;
   for(lane=0;lane<8;lane=lane+1)begin
    if(lane<count)begin
     if(op==12)output_mask[8*lane+:8]=data[8*lane+:8];
     else output_mask[16*lane+:16]=data[16*lane+:16];
    end
   end
  end
 endfunction

 assign req_ready=!reset&&state==IDLE;
 assign rsp_valid=!reset&&state==RESPONSE;
 assign rsp_error=error_hold;
 assign rsp_saturated=saturated_hold;
 assign mem_req_valid=!reset&&(state==READ_REQ||state==WRITE_REQ);
 assign mem_req_write=state==WRITE_REQ;
 assign mem_req_addr=state==WRITE_REQ?dst_hold:
                     operand==0?src_a_hold:operand==1?src_b_hold:src_c_hold;
 assign mem_req_data=result_hold;
 assign mem_rsp_ready=!reset&&(state==READ_RSP||state==WRITE_RSP);
 assign e_in_valid=!reset&&state==ISSUE;
 assign e_in_op=op_hold;
 assign e_in_shift=shift_hold;
 assign e_in_a=a_hold;
 assign e_in_b=b_hold;
 assign e_in_c=c_hold;
 assign e_out_ready=!reset&&state==CAPTURE;

 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;op_hold<=0;shift_hold<=0;count_hold<=0;operand<=0;
   src_a_hold<=0;src_b_hold<=0;src_c_hold<=0;dst_hold<=0;
   need_b<=0;need_c<=0;error_hold<=0;saturated_hold<=0;
   a_hold<=0;b_hold<=0;c_hold<=0;result_hold<=0;
  end else case(state)
   IDLE:if(req_valid&&req_ready)begin
    op_hold<=req_op;shift_hold<=req_shift;count_hold<=req_count;
    src_a_hold<=req_src_a;src_b_hold<=req_src_b;
    src_c_hold<=req_src_c;dst_hold<=req_dst;operand<=0;
    need_b<=uses_b(req_op);need_c<=uses_c(req_op);
    a_hold<=0;b_hold<=0;c_hold<=0;result_hold<=0;
    error_hold<=0;saturated_hold<=0;
    // Invalid op14/15 deliberately reaches native E to classify its error.
    if(req_count==0||req_count>8||(req_op==13&&req_count>4)||
       (req_op==9&&req_count[0]))begin
     error_hold<=1;state<=RESPONSE;
    end else state<=READ_REQ;
   end
   READ_REQ:if(mem_req_valid&&mem_req_ready)state<=READ_RSP;
   READ_RSP:if(mem_rsp_valid&&mem_rsp_ready)begin
    if(mem_rsp_error)begin error_hold<=1;state<=RESPONSE;end
    else begin
     case(operand)
      0:a_hold<=input_mask(mem_rsp_data,op_hold,count_hold);
      1:b_hold<=input_mask(mem_rsp_data,op_hold,count_hold);
      default:c_hold<=input_mask(mem_rsp_data,op_hold,count_hold);
     endcase
     if(operand==0&&need_b)begin operand<=1;state<=READ_REQ;end
     else if(operand!=2&&need_c)begin operand<=2;state<=READ_REQ;end
     else state<=ISSUE;
    end
   end
   ISSUE:if(e_in_valid&&e_in_ready)state<=CAPTURE;
   CAPTURE:if(e_out_valid&&e_out_ready)begin
    error_hold<=e_out_error;saturated_hold<=e_out_saturated;
    if(e_out_error)state<=RESPONSE;
    else begin
     result_hold<=output_mask(e_out_data,op_hold,count_hold);state<=WRITE_REQ;
    end
   end
   WRITE_REQ:if(mem_req_valid&&mem_req_ready)state<=WRITE_RSP;
   WRITE_RSP:if(mem_rsp_valid&&mem_rsp_ready)begin
    error_hold<=mem_rsp_error;state<=RESPONSE;
   end
   RESPONSE:if(rsp_valid&&rsp_ready)state<=IDLE;
   default:begin error_hold<=1;state<=RESPONSE;end
  endcase
 end
endmodule
