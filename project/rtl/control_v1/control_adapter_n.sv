// Fixed N endpoint specialization; numerical macro remains separate and unchanged.
module control_adapter_n(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output wire complete_valid,input wire complete_ready,output wire [63:0] complete_data,
 output wire s_req,s_wr,output wire [9:0] s_addr,output wire [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout,
 output wire cmd_valid,input wire cmd_ready,output wire [3:0] cmd_op,cmd_count,output wire [31:0] cmd_param,
 output wire [127:0] cmd_data,cmd_aux,input wire rsp_valid,output wire rsp_ready,
 input wire [127:0] rsp_data,input wire rsp_error,rsp_saturated
);
 wire [3:0] op,count;wire [31:0] param;wire [127:0] a,b,c;
 wire cv,cr,rv,rr,error,saturated;wire [127:0] data;
 assign cmd_valid=cv;assign cr=cmd_ready;assign cmd_op=op;assign cmd_count=count;assign cmd_param=param;
 assign cmd_data=a;assign cmd_aux=b;assign rv=rsp_valid;assign rsp_ready=rr;
 assign data=rsp_data;assign error=rsp_error;assign saturated=rsp_saturated;
 wire unused_shape=&{1'b0,c};
 control_vector_adapter #(.KIND(2)) adapter(
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
