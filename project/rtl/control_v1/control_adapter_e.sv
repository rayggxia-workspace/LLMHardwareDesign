// Fixed E endpoint specialization; numerical macro remains separate and unchanged.
module control_adapter_e(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output wire complete_valid,input wire complete_ready,output wire [63:0] complete_data,
 output wire s_req,s_wr,output wire [9:0] s_addr,output wire [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout,
 output wire in_valid,input wire in_ready,output wire [3:0] in_op,output wire [4:0] in_shift,
 output wire [127:0] in_a,in_b,in_c,input wire out_valid,output wire out_ready,
 input wire [127:0] out_data,input wire out_error,out_saturated
);
 wire [3:0] op,count;wire [31:0] param;wire [127:0] a,b,c;
 wire cv,cr,rv,rr,error,saturated;wire [127:0] data;
 assign in_valid=cv;assign cr=in_ready;assign in_op=op;assign in_shift=param[4:0];
 assign in_a=a;assign in_b=b;assign in_c=c;assign rv=out_valid;assign out_ready=rr;
 assign data=out_data;assign error=out_error;assign saturated=out_saturated;
 wire unused_shape=&{1'b0,count,param[31:5]};
 control_vector_adapter #(.KIND(3)) adapter(
  .clk(clk),
  .reset(reset),
  .task_valid(task_valid),
  .task_ready(task_ready),
  .task_data(task_data),
  .complete_valid(complete_valid),
  .complete_ready(complete_ready),
  .complete_data(complete_data),
  .s_req(s_req),
  .s_wr(s_wr),
  .s_addr(s_addr),
  .s_din(s_din),
  .s_ready(s_ready),
  .s_valid(s_valid),
  .s_take(s_take),
  .s_dout(s_dout),
  .core_valid(cv),
  .core_ready(cr),
  .core_op(op),
  .core_count(count),
  .core_param(param),
  .core_a(a),
  .core_b(b),
  .core_c(c),
  .core_rsp_valid(rv),
  .core_rsp_ready(rr),
  .core_rsp_data(data),
  .core_error(error),
  .core_saturated(saturated)
 );
endmodule
