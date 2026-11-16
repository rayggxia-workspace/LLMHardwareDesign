// Finite S128 -> existing A32B / W64B packer. No SRAM and no DDR shortcut.
// S contains dense little-endian S32 scalars. W output is four N columns,
// each sixteen K bytes, matching one existing weight_records 64B fill beat.
// Source traversal may be K-major to avoid rereading a word in AV layout.
module dynamic_s32_packer (
 input wire clk, reset,
 input wire cmd_valid, output wire cmd_ready,
 input wire [31:0] cmd_tag,
 input wire cmd_weight, cmd_k_major,
 input wire [2:0] cmd_digit,
 input wire [31:0] cmd_scalar_base, cmd_k_stride, cmd_n_stride,
 input wire [4:0] cmd_k_count,
 input wire [2:0] cmd_n_count,
 output wire s_valid, input wire s_ready,
 output wire [31:0] s_address, s_tag,
 input wire r_valid, output wire r_ready,
 input wire [31:0] r_tag,
 input wire [127:0] r_data,
 input wire r_error,
 output reg out_valid, input wire out_ready,
 output reg [31:0] out_tag,
 output reg out_weight, out_error,
 output reg [511:0] out_data
);
 localparam [1:0] IDLE=0, WALK=1, WAIT_R=2;
 reg [1:0] state;
 reg weight, k_major;
 reg [2:0] digit, n_count;
 reg [4:0] k_count;
 reg [31:0] k_stride, n_stride;
 // The largest command scalar is base +15*k_stride+3*n_stride <2^37.
 // Increment this finite cursor; do not replicate variable multipliers for
 // every look-ahead scalar. Modular row jumps are exact within that bound.
 reg [36:0] scalar_cursor;
 reg [5:0] element;
 reg [31:0] generation, pending_tag;
 reg [31:0] cached_address;
 reg cache_valid;
 reg [127:0] cache_data;
 wire [3:0] k_index=weight && k_major ? element[5:2] : element[3:0];
 wire [1:0] n_index=!weight ? 2'd0 : (k_major ? element[1:0] : element[5:4]);
 wire [31:0] address=scalar_cursor[33:2];
 wire address_bad=|scalar_cursor[36:34];
 wire inactive={1'b0,k_index}>=k_count || {1'b0,n_index}>=n_count;
 wire hit=cache_valid && cached_address==address;
 // Four scalars from the *same existing* S128 response may be extracted in
 // one cycle. Generic strided cases retain single-scalar walking. No second
 // cache/read owner or extra port is introduced by this combinational lane.
 wire fast_walk=(!weight || !k_major) ? k_stride==1 : n_stride==1;
 reg [511:0] walked_data;
 reg [2:0] walked_count;
 reg walk_open;
 reg [6:0] trial;
 reg [3:0] trial_k;
 reg [1:0] trial_n;
 reg [36:0] trial_scalar,walked_scalar;
 wire [36:0] row_jump=weight && k_major ?
  {5'd0,k_stride}-({5'd0,n_stride}<<2)+{5'd0,n_stride} :
  {5'd0,n_stride}-({5'd0,k_stride}<<4)+{5'd0,k_stride};
 reg [31:0] trial_value;
 reg [5:0] trial_destination;
 reg trial_inactive;
 function automatic [15:0] extract_a(input [31:0] value,input [2:0] d);
  extract_a=d==0 ? {1'b0,value[14:0]} : d==1 ? {1'b0,value[29:15]} :
   {{14{value[31]}},value[31:30]};
 endfunction
 function automatic [7:0] extract_w(input [31:0] value,input [2:0] d);
  extract_w=d==0 ? {1'b0,value[6:0]} : d==1 ? {1'b0,value[13:7]} :
   d==2 ? {1'b0,value[20:14]} : d==3 ? {1'b0,value[27:21]} : {{4{value[31]}},value[31:28]};
 endfunction
 always @*begin
  walked_data=out_data;walked_count=0;walk_open=1;
  trial=0;trial_k=0;trial_n=0;trial_scalar=scalar_cursor;walked_scalar=scalar_cursor;
  trial_value=0;trial_destination=0;trial_inactive=0;
  for(integer j=0;j<4;j=j+1)begin
   trial={1'b0,element}+7'(j);
   trial_k=weight && k_major ? trial[5:2] : trial[3:0];
   trial_n=!weight ? 2'd0 : (k_major ? trial[1:0] : trial[5:4]);
   trial_inactive={1'b0,trial_k}>=k_count || {1'b0,trial_n}>=n_count;
   trial_destination=weight ? {trial_n,trial_k} : trial[5:0];
   trial_value=cache_data[{trial_scalar[1:0],5'd0}+:32];
   if(trial>=(weight ? 7'd64 : 7'd16) || (j!=0 && !fast_walk) ||
      (!trial_inactive && ((|trial_scalar[36:34]) || !cache_valid || trial_scalar[33:2]!=cached_address)))
    walk_open=0;
   if(walk_open)begin
    if(weight)walked_data[trial_destination*8+:8]=trial_inactive ? 8'd0 : extract_w(trial_value,digit);
    else walked_data[trial_destination*16+:16]=trial_inactive ? 16'd0 : extract_a(trial_value,digit);
    walked_count=walked_count+1'b1;
   end
   if(weight && (k_major ? trial_n==3 : trial_k==15))trial_scalar=trial_scalar+row_jump;
   else trial_scalar=trial_scalar+(weight && k_major ? {5'd0,n_stride} : {5'd0,k_stride});
   if(walk_open)walked_scalar=trial_scalar;
  end
 end
 wire [6:0] next_element={1'b0,element}+{4'd0,walked_count};
 assign cmd_ready=!reset && state==IDLE && (!out_valid || out_ready);
 assign s_valid=!reset && state==WALK && !inactive && !hit && !address_bad;
 assign s_address=address;
 assign s_tag=generation;
 assign r_ready=!reset && state==WAIT_R;
 always @(posedge clk) begin
  if(reset)begin
   state<=IDLE;weight<=0;k_major<=0;digit<=0;n_count<=0;k_count<=0;
   scalar_cursor<=0;k_stride<=0;n_stride<=0;element<=0;generation<=0;pending_tag<=0;
   cached_address<=0;cache_valid<=0;cache_data<=0;
   out_valid<=0;out_tag<=0;out_weight<=0;out_error<=0;out_data<=0;
  end else begin
   if(out_valid && out_ready)out_valid<=0;
   case(state)
    IDLE: if(cmd_valid && cmd_ready)begin
     out_tag<=cmd_tag;out_weight<=cmd_weight;out_error<=0;out_data<=0;
     if(cmd_k_count==0 || cmd_k_count>16 || cmd_n_count==0 || cmd_n_count>4 ||
        (!cmd_weight && (cmd_n_count!=1 || cmd_digit>2)) || (cmd_weight && cmd_digit>4)) begin
      out_valid<=1;out_error<=1;
     end else begin
      weight<=cmd_weight;k_major<=cmd_k_major;digit<=cmd_digit;
      n_count<=cmd_n_count;k_count<=cmd_k_count;
      scalar_cursor<={5'd0,cmd_scalar_base};k_stride<=cmd_k_stride;n_stride<=cmd_n_stride;
      element<=0;cache_valid<=0;state<=WALK;
     end
    end
    WALK: begin
     if(address_bad && !inactive)begin
      out_valid<=1;out_error<=1;out_data<=0;state<=IDLE;
     end else if(inactive || hit)begin
      out_data<=walked_data;
      if(next_element>=(weight ? 7'd64 : 7'd16))begin out_valid<=1;state<=IDLE;end
      else begin element<=next_element[5:0];scalar_cursor<=walked_scalar;end
     end else if(s_valid && s_ready)begin
      pending_tag<=generation;generation<=generation+1'b1;
      cached_address<=address;state<=WAIT_R;
     end
    end
    WAIT_R: if(r_valid && r_ready)begin
     if(r_error || r_tag!=pending_tag)begin
      out_valid<=1;out_error<=1;out_data<=0;cache_valid<=0;state<=IDLE;
     end else begin cache_data<=r_data;cache_valid<=1;state<=WALK;end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
