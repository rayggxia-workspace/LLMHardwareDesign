// One RAW16 service; request ownership survives cancellation until real ACK.
// S is a separate immutable block_local_s_macro. No payload array exists here.
module lc_raw16_s_adapter #(parameter bit ENABLE_TWO_WORD=1'b0)(
 input wire clk,reset,admit,response_enable,
 input wire req_valid,output wire req_ready,input wire [1:0] req_kind,
 input wire [2:0] req_resource,req_token,input wire [31:0] req_sequence,req_job,req_epoch,req_task,
 input wire [1023:0] req_descriptor,input wire [63:0] req_base,input wire [31:0] req_length,req_version,
 output reg rsp_valid,input wire rsp_ready,output reg [1:0] rsp_kind,output reg [2:0] rsp_token,
 output reg [31:0] rsp_sequence,rsp_job,rsp_epoch,rsp_task,output reg [15:0] rsp_status,
 output reg [31:0] rsp_read,rsp_write,output wire rsp_saturated,
 output reg link_valid,input wire link_ready,output reg [1:0] link_kind,
 output reg [31:0] link_job,link_epoch,link_task,link_sequence,link_edge,
 output reg [7:0] link_peer,output reg [127:0] link_data,
 input wire store_valid,output wire store_ready,input wire [127:0] store_data,
 input wire done_valid,output wire done_ready,input wire [15:0] done_status,
 output wire s_req,s_write,output wire [9:0] s_address,output wire [127:0] s_data,
 input wire s_ready,s_valid,input wire [127:0] s_result,output wire s_take,
 output reg poison,output wire busy
);
 localparam [3:0] IDLE=0,RX_LINK=1,RX_DATA=2,WRITE_REQ=3,WRITE_RSP=4,
                  READ_REQ=5,READ_RSP=6,TX_LINK=7,ACK=8,RESULT=9;
 reg [3:0] state;reg [9:0] address;reg [127:0] payload;
 reg two_words,second_word;
 wire request_two_words=ENABLE_TWO_WORD && req_length==32;
 wire request_size_ok=req_length==16 || (request_two_words && req_base<=16352);
 wire another_word=two_words && !second_word;
 assign req_ready=!reset&&admit&&!poison&&state==IDLE;
 assign busy=state!=IDLE;
 assign rsp_saturated=0;
 assign s_req=!reset&&!poison&&(state==WRITE_REQ||state==READ_REQ);
 assign s_write=state==WRITE_REQ;
 assign s_address=address;assign s_data=payload;
 assign store_ready=!reset&&!poison&&state==WRITE_RSP&&s_valid&&response_enable&&s_result==payload;
 assign s_take=!reset&&!poison&&response_enable&&
                (state==READ_RSP||state==WRITE_RSP&&store_valid&&s_result==payload);
 assign done_ready=!reset&&!poison&&state==ACK&&!rsp_valid;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;poison<=0;address<=0;payload<=0;two_words<=0;second_word<=0;rsp_valid<=0;rsp_kind<=0;rsp_token<=0;
   rsp_sequence<=0;rsp_job<=0;rsp_epoch<=0;rsp_task<=0;rsp_status<=0;rsp_read<=0;rsp_write<=0;
   link_valid<=0;link_kind<=0;link_job<=0;link_epoch<=0;link_task<=0;link_sequence<=0;link_edge<=0;link_peer<=0;link_data<=0;
  end else begin
   if(req_valid&&req_ready)begin
    if((req_kind!=1&&req_kind!=2)||req_resource!=5||!request_size_ok||req_version!=1||req_base>=16384||req_base[3:0]!=0)poison<=1;
    else begin
     rsp_kind<=req_kind;rsp_token<=req_token;rsp_sequence<=req_sequence;rsp_job<=req_job;rsp_epoch<=req_epoch;rsp_task<=req_task;
     rsp_read<=req_kind==2&&!request_two_words?32'd16:32'd0;
     rsp_write<=req_kind==1&&!request_two_words?32'd16:32'd0;
     address<=req_base[13:4];payload<=0;two_words<=request_two_words;second_word<=0;
     link_kind<=req_kind;link_job<=req_job;link_epoch<=req_epoch;link_task<=req_task;link_sequence<=req_sequence;
     link_edge<=req_descriptor[192+:32];link_peer<=req_descriptor[160+:8];link_data<=0;
     link_valid<=req_kind==1;state<=req_kind==1?RX_LINK:READ_REQ;
    end
   end
   if(link_valid&&link_ready)begin link_valid<=0;state<=link_kind==1?RX_DATA:ACK;end
   if(state==RX_DATA&&store_valid)begin payload<=store_data;state<=WRITE_REQ;end
   if(s_req&&s_ready)state<=s_write?WRITE_RSP:READ_RSP;
   if(state==WRITE_RSP&&s_valid&&s_result!=payload)poison<=1;
   if(state==WRITE_RSP&&store_valid&&store_ready)begin
    state<=ACK;
    if(two_words)rsp_write<=rsp_write+32'd16;
   end
   if(state==READ_RSP&&s_valid&&s_take)begin
    link_data<=s_result;link_valid<=1;state<=TX_LINK;
    if(two_words)rsp_read<=rsp_read+32'd16;
   end
   if(done_valid&&done_ready)begin
    if(another_word&&done_status==0)begin
     address<=address+10'd1;second_word<=1;
     link_edge<=link_edge+32'd1;
     state<=rsp_kind==1?RX_DATA:READ_REQ;
    end else begin
     rsp_status<=done_status;rsp_valid<=1;state<=RESULT;
    end
   end
   if(rsp_valid&&rsp_ready)begin rsp_valid<=0;state<=IDLE;end
  end
 end
endmodule
