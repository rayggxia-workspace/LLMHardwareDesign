module layer_dma(
 input wire clk,reset,
 input wire desc_valid,desc_write,complete_ready,
 output wire desc_ready,complete_valid,busy,
 input wire [39:0] desc_address,
 input wire [9:0] desc_local,
 input wire [10:0] desc_words,
 input wire [15:0] desc_tag,
 output wire [1:0] complete_status,
 output wire [15:0] complete_tag,
 output wire [10:0] completed_words,
 output wire protocol_error,
 output wire mem_valid,input wire mem_ready,output wire [184:0] mem_data,
 input wire response_valid,output wire response_ready,input wire [145:0] response_data,
 input wire host_select,host_req,host_write,host_take,
 input wire [9:0] host_address,input wire [127:0] host_data,
 output wire host_ready,host_valid,output wire [127:0] host_result
);
 wire req,wr,take,ready,valid;
 wire [9:0] address;
 wire [127:0] data,result;
 wire [3:0] unused_live,unused_grant;
 wire unused_gvalid,unused_eligible;
 hbm_group_dma #(.GROUPS(1),.S_PER_GROUP(1),.SLOTS(8),.CHANNELS(1)) dma(
  .clk(clk),.reset(reset),.channel_count(3'd1),.credit_limit(4'd8),
  .desc_valid(desc_valid),.desc_write(desc_write),.complete_ready(complete_ready),
  .desc_ready(desc_ready),.desc_address_flat(desc_address),.desc_local_flat(desc_local),
  .desc_words_flat(desc_words),.desc_tag_flat(desc_tag),
  .complete_valid(complete_valid),.complete_status_flat(complete_status),
  .complete_tag_flat(complete_tag),.completed_words_flat(completed_words),
  .busy(busy),.protocol_error(protocol_error),
  .mem_valid(mem_valid),.mem_ready(mem_ready),.mem_data_flat(mem_data),
  .response_valid(response_valid),.response_ready(response_ready),.response_data_flat(response_data),
  .s_req(req),.s_wr(wr),.s_take(take),.s_address_flat(address),.s_data_flat(data),
  .s_ready(ready&&!host_select),.s_valid(valid&&!host_select),.s_result_flat(result),
  .live_count_flat(unused_live),.grant_valid(unused_gvalid),.grant_s_flat(unused_grant),
  .eligible_debug(unused_eligible)
 );
 assign host_ready=host_select&&ready;
 assign host_valid=host_select&&valid;
 assign host_result=result;
 block_feed_s16k storage(
  .clk(clk),.reset(reset),.req(host_select?host_req:req),
  .wr(host_select?host_write:wr),.addr(host_select?host_address:address),
  .din(host_select?host_data:data),.ready(ready),.valid(valid),
  .take(host_select?host_take:take),.dout(result),
  .wide_req(1'b0),.wide_addr(8'd0),.wide_ready(),.wide_valid(),.wide_take(1'b0),.wide_dout()
 );
endmodule
