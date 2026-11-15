`timescale 1ns/1ps
// Parent standard-cell activation source for one selected M projection service.
// Fetch K128 S32 (512 B), quantize into 16 existing SRAM words, then publish
// the committed window. No U/P connection, COPY channel or extra SRAM exists.
module projection_local_source(
 input wire clk,reset,scope_start,scope_end,scope_cancel,
 input wire [127:0] scope_key,
 input wire [63:0] scope_source_address,
 input wire [15:0] scope_full_k,
 input wire [9:0] scope_source_word,scope_a_word,
 input wire need_valid,input wire [15:0] need_k,input wire [127:0] need_key,
 output wire window_valid,output wire [127:0] window_key,
 output wire [15:0] window_generation,window_k,
 output wire [31:0] window_session,window_ticket,
 output wire [5:0] window_shift,
 input wire proof_valid,output wire proof_ready,
 input wire proof_error,proof_source_drained,input wire [5:0] proof_shift,
 output reg failed,output wire drained,
 output wire rd_valid,input wire rd_ready,output wire [63:0] rd_address,rd_tag,
 input wire rd_rsp_valid,output wire rd_rsp_ready,
 input wire [63:0] rd_rsp_tag,input wire [511:0] rd_rsp_data,input wire rd_rsp_error,
 output wire load_valid,input wire load_ready,
 output wire [9:0] load_address,output wire [127:0] load_data,output wire [31:0] load_tag,
 input wire load_rsp_valid,output wire load_rsp_ready,input wire [31:0] load_rsp_tag,input wire load_rsp_error,
 output wire quant_valid,input wire quant_ready,output wire quant_write,
 output wire [9:0] quant_address,output wire [127:0] quant_data,output wire [31:0] quant_tag,
 input wire quant_rsp_valid,output wire quant_rsp_ready,
 input wire [31:0] quant_rsp_tag,input wire [127:0] quant_rsp_data,input wire quant_rsp_error
);
 localparam [2:0] EMPTY=0,FETCH=1,FETCH_WAIT=2,QUANT=3,QUANT_WAIT=4,PUBLISHED=5;
 reg [2:0] state;
 reg active,cancelled,proof_seen;
 reg [127:0] key;
 reg [63:0] source_address;
 reg [15:0] full_k,k;
 reg [9:0] source_word,a_word;
 reg [31:0] session;
 reg [5:0] shift;
 wire loader_ready,loader_done,loader_error;
 wire [63:0] loader_rd_tag;
 assign rd_tag={8'd0,session,window_generation,loader_rd_tag[7:0]};
 wire quantizer_ready,quantizer_done,quantizer_error,quantizer_cancelled;
 wire [127:0] quantizer_owner;
 wire [15:0] quantizer_k,quantizer_mask;
 wire [4:0] quantizer_words;
 wire [5:0] quantizer_shift;
 wire [31:0] rejected;
 wire stop=cancelled||scope_cancel;
 wire requested=active&&need_valid&&(state==EMPTY||(state==PUBLISHED&&proof_seen&&need_k!=k));
 wire bad_request=need_key!=key||need_k[6:0]!=0||need_k>=full_k||
   (state==EMPTY ? need_k!=0 : need_k!=k+16'd128);
 assign window_valid=active&&state==PUBLISHED&&!failed&&!stop;
 assign window_key=key;
 assign window_k=k;
 assign window_generation=(k>>7)+16'd1;
 assign window_session=session;
 assign window_ticket={16'd0,window_generation};
 assign window_shift=shift;
 assign proof_ready=active&&state==PUBLISHED;
 assign drained=state==EMPTY||state==PUBLISHED;
 s128_ddr_range_load #(.PIPELINE_WRITES(1'b1)) loader(
  .clk,.reset,.launch_valid(state==FETCH&&!stop),.launch_ready(loader_ready),
  .launch_base(source_address+{46'd0,k,2'd0}),.launch_s_base(source_word),
  .launch_bursts(8'd8),.launch_pair(1'b0),.launch_pair_beat(1'b0),.launch_pair_high(1'b0),
  .done_valid(loader_done),.done_error(loader_error),.done_ready(state==FETCH_WAIT),
  .rd_valid,.rd_ready,.rd_address,.rd_tag(loader_rd_tag),.rd_rsp_valid,.rd_rsp_ready,
  .rd_rsp_tag(rd_rsp_error||rd_rsp_tag!=rd_tag ? loader_rd_tag^64'd1 : loader_rd_tag),.rd_rsp_data,
  .s_valid(load_valid),.s_ready(load_ready),.s_address(load_address),.s_data(load_data),.s_tag(load_tag),
  .s_rsp_valid(load_rsp_valid),.s_rsp_ready(load_rsp_ready),
  .s_rsp_tag(load_rsp_error ? (load_rsp_tag | 32'h80000000) : load_rsp_tag));
 s32_a16_tile_quantizer #(.SESSION_IDS(1'b1)) quantizer(
  .clk,.reset,.cmd_valid(state==QUANT&&!stop),.cmd_ready(quantizer_ready),
  .cmd_key(key),.cmd_generation(window_generation),.cmd_kk(k),.cmd_session(session),
  .cmd_source(source_word),.cmd_destination(a_word),.cmd_shift_known(1'b0),.cmd_shift(6'd0),
  .cancel_valid(stop),.cancel_key(key),
  .s_valid(quant_valid),.s_ready(quant_ready),.s_write(quant_write),
  .s_address(quant_address),.s_data(quant_data),.s_tag(quant_tag),
  .rsp_valid(quant_rsp_valid),.rsp_ready(quant_rsp_ready),.rsp_tag(quant_rsp_tag),
  .rsp_data(quant_rsp_data),.rsp_error(quant_rsp_error),
  .done_valid(quantizer_done),.done_ready(state==QUANT_WAIT),.done_key(quantizer_owner),
  .done_kk(quantizer_k),.done_error(quantizer_error),.done_cancelled(quantizer_cancelled),
  .done_words(quantizer_words),.done_written_mask(quantizer_mask),.done_shift(quantizer_shift),
  .rejected_responses(rejected));
 always @(posedge clk)begin
  if(reset)begin
   state<=EMPTY;active<=0;cancelled<=0;proof_seen<=0;failed<=0;key<=0;source_address<=0;
   full_k<=0;k<=0;source_word<=0;a_word<=0;session<=0;shift<=0;
  end else begin
   if(scope_start&&active)failed<=1;
   else if(scope_start)begin
    active<=1;cancelled<=0;proof_seen<=0;
    failed<=session==32'hffffffff||scope_full_k==0||scope_full_k[6:0]!=0||
      scope_source_address[5:0]!=0||scope_source_address[63:48]!=0||
      {1'b0,scope_source_address}+{47'd0,scope_full_k,2'd0}>(65'd1<<48)||
      scope_source_word>992||scope_a_word>1008||
      !({1'b0,scope_source_word}+11'd32<={1'b0,scope_a_word}||
        {1'b0,scope_a_word}+11'd16<={1'b0,scope_source_word});
    key<=scope_key;source_address<=scope_source_address;full_k<=scope_full_k;
    source_word<=scope_source_word;a_word<=scope_a_word;session<=session+32'd1;state<=EMPTY;
   end else begin
    if(scope_cancel)cancelled<=1;
    if(scope_end&&drained)begin active<=0;state<=EMPTY;end
    else if(requested&&!stop&&!failed)begin
     if(bad_request)failed<=1;
     else begin k<=need_k;proof_seen<=0;state<=FETCH;end
    end
    if(proof_valid&&proof_ready)begin
     proof_seen<=1;
     if(proof_error||!proof_source_drained||proof_shift!=shift)failed<=1;
    end
    case(state)
     FETCH:if(stop)state<=EMPTY;else if(loader_ready)state<=FETCH_WAIT;
     FETCH_WAIT:if(loader_done)begin
      if(loader_error)failed<=1;
      state<=loader_error||stop ? EMPTY : QUANT;
     end
     QUANT:if(stop)state<=EMPTY;else if(quantizer_ready)state<=QUANT_WAIT;
     QUANT_WAIT:if(quantizer_done)begin
      if(quantizer_error||quantizer_cancelled||quantizer_owner!=key||quantizer_k!=k||
         quantizer_words!=16||quantizer_mask!=16'hffff)begin failed<=1;state<=EMPTY;end
      else begin shift<=quantizer_shift;state<=stop ? EMPTY : PUBLISHED;end
     end
     default:begin end
    endcase
   end
  end
 end
endmodule
