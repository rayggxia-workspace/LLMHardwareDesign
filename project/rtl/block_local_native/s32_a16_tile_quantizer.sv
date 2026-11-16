// LC K128 S32->A16 normalizer. Two original S response-owner slots, two
// 16B packing slots, no new SRAM or source-tile register cache. Optional observed
// producer shift skips the max scan; data/scale commit still needs all true ACKs.
// A held request survives cancel/fault, then all accepted transactions drain.
// Failed output reports its actual committed prefix and publishes no scale.
module s32_a16_tile_quantizer (
 input wire clk, reset,
 input wire cmd_valid, output wire cmd_ready,
 input wire [127:0] cmd_key,
 input wire [15:0] cmd_generation, cmd_kk,
 input wire [9:0] cmd_source, cmd_destination,
 input wire cmd_shift_known, input wire [5:0] cmd_shift,
 input wire cancel_valid, input wire [127:0] cancel_key,
 output reg s_valid, input wire s_ready,
 output reg s_write,
 output reg [9:0] s_address,
 output reg [127:0] s_data,
 output reg [31:0] s_tag,
 input wire rsp_valid, output wire rsp_ready,
 input wire [31:0] rsp_tag,
 input wire [127:0] rsp_data, input wire rsp_error,
 output reg done_valid, input wire done_ready,
 output reg [127:0] done_key,
 output reg [15:0] done_kk,
 output reg done_error, done_cancelled,
 output reg [4:0] done_words,
 output reg [15:0] done_written_mask,
 output reg [5:0] done_shift,
 output reg [31:0] rejected_responses
);
 localparam [1:0] SCAN=0, CHOOSE=1, CONVERT=2, WRITE=3;
 reg busy, failed, cancelled;
 reg [1:0] phase;
 reg [5:0] scan_issued, read_issued;
 reg [4:0] write_issued, written;
 reg [15:0] written_mask;
 reg [127:0] key, pack_data[0:1];
 reg [1:0] allocated, write_pending, returned[0:1];
 reg [31:0] maximum;
 reg [15:0] generation, last_generation, kk;
 reg [9:0] source_base, destination_base;
 reg [5:0] shift;
 reg [1:0] tag_kind[0:1], count;
 reg [5:0] tag_index[0:1];
 reg head, tail, stalled;
 reg [1:0] held_kind, request_kind;
 reg [5:0] held_index, request_index;
 function automatic [31:0] magnitude(input [31:0] value);
  begin magnitude=value[31] ? (~value+32'd1) : value;end
 endfunction
 function automatic [4:0] committed_prefix(input [15:0] mask);
  reg stopped;
  begin
   committed_prefix=0;stopped=0;
   for(integer i=0;i<16;i=i+1)begin
    if(!mask[i])stopped=1;
    if(!stopped)committed_prefix=committed_prefix+1'b1;
   end
  end
 endfunction
 function automatic [31:0] maximum_word(input [127:0] word_data);
  reg [31:0] result, candidate;
  begin
   result=0;
   for(integer i=0;i<4;i=i+1) begin
    candidate=magnitude(word_data[32*i+:32]);
    if(candidate>result) result=candidate;
   end
   maximum_word=result;
  end
 endfunction
 function automatic [5:0] choose_shift(input [31:0] largest);
  reg found;
  begin
   choose_shift=17;found=0;
   for(integer s=0;s<18;s=s+1) begin
    if(!found && {32'd0,largest}<=(64'd32767<<s)) begin choose_shift=6'(s);found=1;end
   end
  end
 endfunction
 // Return {overflow, four signed A16 values}. Magnitude arithmetic implements
 // symmetric ties-to-even, including INT_MIN, without signed shift ambiguity.
 function automatic [64:0] quantize_word(input [127:0] word_data,input [5:0] amount);
  reg [31:0] absolute_value, quotient, remainder_value, half;
  reg [15:0] result;
  reg overflow;
  begin
   quantize_word=0;overflow=0;
   for(integer i=0;i<4;i=i+1) begin
    absolute_value=magnitude(word_data[32*i+:32]);quotient=absolute_value>>amount;
    if(amount!=0) begin
     remainder_value=absolute_value&((32'd1<<amount)-32'd1);half=32'd1<<(amount-1'b1);
     if(remainder_value>half || (remainder_value==half && quotient[0])) quotient=quotient+32'd1;
    end
    if((word_data[32*i+31] && quotient>32768) || (!word_data[32*i+31] && quotient>32767)) overflow=1;
    result=word_data[32*i+31] ? (~quotient[15:0]+16'd1) : quotient[15:0];
    quantize_word[16*i+:16]=result;
   end
   quantize_word[64]=overflow;
  end
 endfunction
 wire [10:0] source_limit={1'b0,cmd_source}+11'd32;
 wire [10:0] destination_limit={1'b0,cmd_destination}+11'd16;
 wire command_bad=cmd_generation<=last_generation || cmd_kk[6:0]!=0 ||
     source_limit>1024 || destination_limit>1024 ||
     !(source_limit<={1'b0,cmd_destination} || destination_limit<={1'b0,cmd_source}) ||
     (cmd_shift_known && cmd_shift>17);
 wire cancel_fire=cancel_valid && busy && cancel_key==key;
 wire [31:0] expected_tag={generation,tag_kind[head],tag_index[head],8'd0};
 wire response_match=count!=0 && rsp_tag==expected_tag;
 wire response_fire=rsp_valid && rsp_ready && response_match;
 wire [64:0] packed_word=quantize_word(rsp_data,shift);
 wire [31:0] word_max=maximum_word(rsp_data);
 wire tag_space=count<2 || response_fire;
 wire request_fire=s_valid && s_ready;
 assign cmd_ready=!reset && !busy && !done_valid;
 assign rsp_ready=!reset;
 always @* begin
  s_valid=0;request_kind=SCAN;request_index=0;
  if(!reset && stalled)begin s_valid=1;request_kind=held_kind;request_index=held_index;end
  else if(!reset && busy && !failed && !cancelled && !cancel_fire && tag_space)begin
   if(phase==SCAN && scan_issued<32)begin s_valid=1;request_index=scan_issued;end
   else if(phase==CONVERT)begin
    if(write_issued<16 && returned[write_issued[0]]==2'b11 && !write_pending[write_issued[0]])begin
     s_valid=1;request_kind=WRITE;request_index={1'b0,write_issued};
    end else if(read_issued<32 && (read_issued[0] || !allocated[read_issued[1]]))begin
     s_valid=1;request_kind=CONVERT;request_index=read_issued;
    end
   end
  end
  s_write=request_kind==WRITE;
  s_address=(s_write?destination_base:source_base)+{4'd0,request_index};
  s_data=s_write?pack_data[request_index[0]]:128'd0;
  s_tag={generation,request_kind,request_index,8'd0};
 end
 always @(posedge clk)begin
  if(reset)begin
   busy<=0;failed<=0;cancelled<=0;phase<=SCAN;scan_issued<=0;read_issued<=0;write_issued<=0;written<=0;written_mask<=0;
   key<=0;pack_data[0]<=0;pack_data[1]<=0;allocated<=0;write_pending<=0;returned[0]<=0;returned[1]<=0;
   maximum<=0;generation<=0;last_generation<=0;kk<=0;source_base<=0;destination_base<=0;shift<=0;
   tag_kind[0]<=0;tag_kind[1]<=0;tag_index[0]<=0;tag_index[1]<=0;count<=0;head<=0;tail<=0;
   stalled<=0;held_kind<=0;held_index<=0;
   done_valid<=0;done_key<=0;done_kk<=0;done_error<=0;done_cancelled<=0;done_words<=0;done_written_mask<=0;done_shift<=0;rejected_responses<=0;
  end else begin
   if(done_valid && done_ready)done_valid<=0;
   if(cmd_valid && cmd_ready)begin
    if(cmd_generation>last_generation)last_generation<=cmd_generation;
    done_key<=cmd_key;done_kk<=cmd_kk;done_error<=command_bad;done_cancelled<=0;done_words<=0;done_written_mask<=0;done_shift<=0;
    if(command_bad)done_valid<=1;
    else begin
     busy<=1;failed<=0;cancelled<=0;key<=cmd_key;generation<=cmd_generation;kk<=cmd_kk;
     source_base<=cmd_source;destination_base<=cmd_destination;shift<=cmd_shift_known?cmd_shift:0;
     phase<=cmd_shift_known?CONVERT:SCAN;scan_issued<=0;read_issued<=0;write_issued<=0;written<=0;written_mask<=0;
     allocated<=0;write_pending<=0;returned[0]<=0;returned[1]<=0;maximum<=0;
    end
   end
   if(cancel_fire)cancelled<=1;
   if(busy && phase==CHOOSE && !failed && !cancelled)begin shift<=choose_shift(maximum);phase<=CONVERT;end
   if(s_valid && !s_ready)begin stalled<=1;held_kind<=request_kind;held_index<=request_index;end
   if(request_fire)begin
    stalled<=0;tag_kind[tail]<=request_kind;tag_index[tail]<=request_index;tail<=!tail;
    if(request_kind==SCAN)scan_issued<=scan_issued+1'b1;
    else if(request_kind==WRITE)begin write_issued<=write_issued+1'b1;write_pending[request_index[0]]<=1;end
    else begin read_issued<=read_issued+1'b1;if(!request_index[0])allocated[request_index[1]]<=1;end
   end
   if(rsp_valid && rsp_ready && !response_match)rejected_responses<=rejected_responses+1'b1;
   if(response_fire)begin
    head<=!head;
    if(rsp_error)failed<=1;
    else if(tag_kind[head]==WRITE)begin
     written<=written+1'b1;written_mask[tag_index[head][3:0]]<=1;write_pending[tag_index[head][0]]<=0;
     allocated[tag_index[head][0]]<=0;returned[tag_index[head][0]]<=0;
    end else if(!failed && !cancelled && !cancel_fire)begin
     if(tag_kind[head]==SCAN)begin
      if(word_max>maximum)maximum<=word_max;
      if(tag_index[head]==31)phase<=CHOOSE;
     end else if(packed_word[64])failed<=1;
     else begin
      pack_data[tag_index[head][1]][64*tag_index[head][0]+:64]<=packed_word[63:0];
      returned[tag_index[head][1]][tag_index[head][0]]<=1;
     end
    end
   end
   case({request_fire,response_fire})
    2'b10:count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:begin end
   endcase
   if(busy && !s_valid && count==0 && (failed || cancelled || (phase==CONVERT && written==16)))begin
    busy<=0;done_valid<=1;done_key<=key;done_kk<=kk;done_error<=failed;done_cancelled<=cancelled;
    done_words<=committed_prefix(written_mask);done_written_mask<=written_mask;done_shift<=(failed || cancelled)?6'd0:shift;
   end
  end
 end
endmodule
