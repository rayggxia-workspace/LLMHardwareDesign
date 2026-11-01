// 有限搬运器。外存平台必须按请求顺序返回一次响应（写操作也返回）。
// 地址以字节计，S 地址以 128-bit 字计；只支持完整、16-byte 对齐传输。
// 一个描述符；LOAD 最多四个已预留字；STORE/STREAM 最多一个字。
// 错误不回滚：排空整个已接受描述符后报告失败；缓冲区由调用方独占。
// reset 必须同时清空平台请求/响应队列，不能单独丢弃在途事务。
module finite_dma (
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,
 input wire [1:0] cmd_mode, // 0: external->S; 1: S->external; 2: T->external
 input wire [31:0] cmd_ext_base,cmd_ext_stride,
 input wire [10:0] cmd_rows,cmd_cols,cmd_s_base,cmd_s_stride,
 output reg done_valid,input wire done_ready,output reg done_error,
 output wire busy,
 output wire ext_valid,input wire ext_ready,output wire ext_write,
 output wire [31:0] ext_addr,output wire [127:0] ext_data,
 input wire ext_rsp_valid,output wire ext_rsp_ready,
 input wire [127:0] ext_rsp_data,input wire ext_rsp_error,
 output wire s_req,s_wr,output wire [9:0] s_addr,output wire [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout,
 input wire stream_valid,output wire stream_ready,
 input wire [127:0] stream_data,input wire stream_last,
 output wire [2:0] reserved_words
);
 localparam IDLE=0,LOAD=1,FETCH=2,SWAIT=3,WREQ=4,WACK=5;
 reg [2:0] state;
 reg [1:0] mode;
 reg [10:0] cols,total,issued,received,drained,issue_col,drain_col;
 reg [31:0] ext_cursor,ext_stride;
 reg [10:0] s_cursor,s_stride;
 reg [127:0] fifo[0:3],held;
 reg [3:0] fifo_error;
 reg s_pending,failed;
 wire [21:0] count_product=cmd_rows*cmd_cols;
 wire [63:0] ext_end={32'd0,cmd_ext_base}+
  ({53'd0,cmd_rows}-64'd1)*{32'd0,cmd_ext_stride}+({53'd0,cmd_cols}<<4)-64'd1;
 wire [63:0] s_end={53'd0,cmd_s_base}+
  ({53'd0,cmd_rows}-64'd1)*{53'd0,cmd_s_stride}+{53'd0,cmd_cols};
 wire legal=cmd_mode<3&&cmd_rows!=0&&cmd_cols!=0&&
  cmd_rows<=1024&&cmd_cols<=1024&&count_product<=1024&&
  cmd_ext_base[3:0]==0&&cmd_ext_stride[3:0]==0&&
  {32'd0,cmd_ext_stride}>=({53'd0,cmd_cols}<<4)&&ext_end<=64'hffffffff&&
  (cmd_mode==2?(count_product<=384):
   (cmd_s_base<1024&&cmd_s_stride>=cmd_cols&&s_end<=1024));
 assign cmd_ready=!reset&&state==IDLE&&(!done_valid||done_ready);
 assign busy=state!=IDLE||done_valid;
 assign reserved_words=state==LOAD?3'(issued-drained):3'd0;
 wire load_word=state==LOAD&&received>drained&&!s_pending;
 wire discard=load_word&&fifo_error[drained[1:0]];
 assign ext_valid=!reset&&((state==LOAD&&issued<total&&issued-drained<4)||state==WREQ);
 assign ext_write=state==WREQ;
 assign ext_addr=ext_cursor;
 assign ext_data=held;
 assign ext_rsp_ready=!reset&&((state==LOAD&&received<issued)||state==WACK);
 assign s_req=!reset&&((load_word&&!discard)||(state==FETCH&&mode==1));
 assign s_wr=state==LOAD;
 assign s_addr=s_cursor[9:0];
 assign s_din=fifo[drained[1:0]];
 assign s_take=!reset&&((state==LOAD&&s_pending)||state==SWAIT);
 assign stream_ready=!reset&&state==FETCH&&mode==2;
 wire load_retire=state==LOAD&&(discard||(s_pending&&s_valid));
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;mode<=0;cols<=0;total<=0;issued<=0;received<=0;drained<=0;
   issue_col<=0;drain_col<=0;ext_cursor<=0;ext_stride<=0;s_cursor<=0;s_stride<=0;
   held<=0;fifo_error<=0;s_pending<=0;failed<=0;done_valid<=0;done_error<=0;
  end else begin
   if(done_valid&&done_ready)done_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    done_error<=0;failed<=0;s_pending<=0;fifo_error<=0;
    issued<=0;received<=0;drained<=0;issue_col<=0;drain_col<=0;
    cols<=cmd_cols;total<=count_product[10:0];mode<=cmd_mode;
    ext_cursor<=cmd_ext_base;ext_stride<=cmd_ext_stride;
    s_cursor<=cmd_s_base;s_stride<=cmd_s_stride;
    if(!legal)begin done_valid<=1;done_error<=1;end
    else state<=cmd_mode==0?LOAD:FETCH;
   end
   if(state==LOAD)begin
    if(ext_valid&&ext_ready)begin
     issued<=issued+1'b1;
     if(issue_col+1'b1==cols)begin
      issue_col<=0;ext_cursor<=ext_cursor+ext_stride-({21'd0,cols-11'd1}<<4);
     end else begin issue_col<=issue_col+1'b1;ext_cursor<=ext_cursor+16;end
    end
    if(ext_rsp_valid&&ext_rsp_ready)begin
     fifo[received[1:0]]<=ext_rsp_data;fifo_error[received[1:0]]<=ext_rsp_error;
     received<=received+1'b1;if(ext_rsp_error)failed<=1;
    end
    if(s_req&&s_ready)s_pending<=1;
    if(load_retire)begin
     s_pending<=0;drained<=drained+1'b1;
     if(drain_col+1'b1==cols)begin drain_col<=0;s_cursor<=s_cursor+s_stride-(cols-11'd1);end
     else begin drain_col<=drain_col+1'b1;s_cursor<=s_cursor+1'b1;end
     if(drained+1'b1==total)begin state<=IDLE;done_valid<=1;done_error<=failed;end
    end
   end else case(state)
    FETCH:if(mode==1)begin if(s_req&&s_ready)state<=SWAIT;end
     else if(stream_valid&&stream_ready)begin
      held<=stream_data;state<=WREQ;
      if(stream_last!=(drained+1'b1==total))failed<=1;
     end
    SWAIT:if(s_valid&&s_take)begin held<=s_dout;state<=WREQ;end
    WREQ:if(ext_valid&&ext_ready)state<=WACK;
    WACK:if(ext_rsp_valid&&ext_rsp_ready)begin
     if(ext_rsp_error)failed<=1;
     drained<=drained+1'b1;
     if(drained+1'b1==total)begin
      state<=IDLE;done_valid<=1;done_error<=failed||ext_rsp_error;
     end else begin
      state<=FETCH;
      if(drain_col+1'b1==cols)begin
       drain_col<=0;s_cursor<=s_cursor+s_stride-(cols-11'd1);
       ext_cursor<=ext_cursor+ext_stride-({21'd0,cols-11'd1}<<4);
      end else begin drain_col<=drain_col+1'b1;s_cursor<=s_cursor+1'b1;ext_cursor<=ext_cursor+16;end
     end
    end
    default:begin end
   endcase
  end
 end
endmodule
