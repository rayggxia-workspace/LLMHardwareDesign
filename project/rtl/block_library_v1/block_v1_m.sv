// Complete finite matrix engine. Numeric/port contract: docs/BLOCK_LIBRARY_V1.md.
// LOAD_A=0; LOAD_B=1(row index); MAC=2; READ_PARTIAL=3(two lanes);
// MERGE=4; READ_FINAL=5(four S32 containers); RESET_CONTEXT=6.
// There is one command/response owner. All responses hold under backpressure.
module block_v1_m(
 input wire clk,reset,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_op,input wire [5:0] cmd_index,
 input wire [127:0] cmd_data,
 output reg rsp_valid,input wire rsp_ready,
 output reg [127:0] rsp_data,output reg rsp_error,rsp_saturated,
 output wire busy
);
 localparam IDLE=0,PRODUCT=1,REDUCE=2,ACCUMULATE=3,DONE=4,
            SCALE=5,ALIGN=6,COMMIT=7;
 reg [3:0] state;
 reg signed [15:0] a[0:7],b[0:63];
 reg a_valid;reg [7:0] b_valid;
 reg signed [15:0] product[0:63];
 reg signed [18:0] reduced[0:7];
 reg signed [63:0] accumulator[0:7];
 reg signed [127:0] merged[0:7],preview[0:7];
 reg accumulator_valid,merged_valid;
 reg [15:0] k_count;
 reg fmt_a,fmt_b,clear_acc;
 reg [3:0] active_k,active_n;
 reg [1:0] digit_a,digit_b;
 reg [2:0] scale_lane;
 reg signed [31:0] scale_factor;
 reg [6:0] merge_shift;
 reg clear_merge,merge_error;
 reg signed [95:0] scale_product;
 wire [5:0] digit_shift = 7*({4'b0,digit_a}+{4'b0,digit_b});
 assign cmd_ready=state==IDLE&&!rsp_valid;
 assign busy=!cmd_ready;

 function automatic signed [7:0] digit;
  input signed [15:0] value;input wide;input [1:0] part;
  begin
   if(!wide) digit=value[7:0];
   else case(part)
    0:digit={1'b0,value[6:0]};
    1:digit={1'b0,value[13:7]};
    default:digit={{6{value[15]}},value[15:14]};
   endcase
  end
 endfunction

 // Arithmetic-floor quotient + positive remainder implements ties-to-even
 // for both signs, without abs(-2^127) overflow.
 function automatic signed [127:0] round_even;
  input signed [127:0] value;input [6:0] shift;
  reg signed [127:0] quotient;
  reg [127:0] remainder,half,mask;
  begin
   if(shift==0) round_even=value;
   else begin
    quotient=value>>>shift;
    mask={128{1'b1}}>>(128-shift);
    remainder=$unsigned(value)&mask;
    half=128'd1<<(shift-1);
    round_even=quotient+((remainder>half)||((remainder==half)&&quotient[0]));
   end
  end
 endfunction

 integer i,j;
 reg signed [18:0] sums[0:7];
 reg signed [64:0] next_acc[0:7];
 reg accumulation_error;
 reg signed [255:0] aligned_scale;
 reg signed [128:0] merge_sum;
 reg alignment_error;
 reg [127:0] read_data;
 reg read_saturated,read_error;
 reg signed [127:0] rounded,lower_limit,upper_limit;
 integer lane_number;
 always @* begin
  accumulation_error=0;
  for(integer row=0;row<8;row=row+1)begin
   // Explicit balanced local tree, not an external product interface.
   sums[row]=
    (($signed({{3{product[8*row][15]}},product[8*row]})+
      $signed({{3{product[8*row+1][15]}},product[8*row+1]}))+
     ($signed({{3{product[8*row+2][15]}},product[8*row+2]})+
      $signed({{3{product[8*row+3][15]}},product[8*row+3]})))+
    (($signed({{3{product[8*row+4][15]}},product[8*row+4]})+
      $signed({{3{product[8*row+5][15]}},product[8*row+5]}))+
     ($signed({{3{product[8*row+6][15]}},product[8*row+6]})+
      $signed({{3{product[8*row+7][15]}},product[8*row+7]})));
   next_acc[row]=$signed({accumulator[row][63],accumulator[row]})+
       ($signed({{46{reduced[row][18]}},reduced[row]})<<<digit_shift);
   if(next_acc[row][64]!=next_acc[row][63])accumulation_error=1;
  end
  aligned_scale=$signed({{160{scale_product[95]}},scale_product})<<<merge_shift;
  merge_sum=$signed({aligned_scale[127],aligned_scale[127:0]})+
      (clear_merge?129'sd0:$signed({merged[scale_lane][127],merged[scale_lane]}));
  alignment_error=aligned_scale[255:127]!={129{aligned_scale[127]}} ||
                  merge_sum[128]!=merge_sum[127];
  read_data=0;read_saturated=0;read_error=0;
  rounded=0;lower_limit=0;upper_limit=0;lane_number=0;
  case(cmd_data[9:8])
   0:begin lower_limit=-128;upper_limit=127;end
   1:begin lower_limit=-32768;upper_limit=32767;end
   2:begin lower_limit=-128'sd2147483648;upper_limit=2147483647;end
   default:read_error=1;
  endcase
  for(integer r=0;r<4;r=r+1)begin
   lane_number=4*int'(cmd_index)+r;
   if(lane_number<8)begin
    rounded=round_even(merged[lane_number],cmd_data[6:0]);
    if(rounded<lower_limit)begin rounded=lower_limit;read_saturated=1;end
    else if(rounded>upper_limit)begin rounded=upper_limit;read_saturated=1;end
    read_data[32*r+:32]=rounded[31:0];
   end
  end
 end

 task automatic respond;
  input [127:0] data;input error;input saturated;
  begin rsp_valid<=1;rsp_data<=data;rsp_error<=error;rsp_saturated<=saturated;state<=IDLE;end
 endtask

 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;rsp_valid<=0;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
   a_valid<=0;b_valid<=0;accumulator_valid<=0;merged_valid<=0;k_count<=0;
   fmt_a<=0;fmt_b<=0;clear_acc<=0;active_k<=0;active_n<=0;
   digit_a<=0;digit_b<=0;scale_lane<=0;scale_factor<=0;
   merge_shift<=0;clear_merge<=0;merge_error<=0;scale_product<=0;
   for(i=0;i<8;i=i+1)begin accumulator[i]<=0;merged[i]<=0;preview[i]<=0;reduced[i]<=0;end
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   case(state)
    IDLE:if(cmd_valid&&cmd_ready)begin
     case(cmd_op)
      0:begin
       for(i=0;i<8;i=i+1)a[i]<=$signed(cmd_data[16*i+:16]);
       a_valid<=1;respond(0,0,0);
      end
      1:if(cmd_index<8)begin
       for(i=0;i<8;i=i+1)b[8*int'(cmd_index)+i]<=$signed(cmd_data[16*i+:16]);
       b_valid[cmd_index]<=1;respond(0,0,0);
      end else respond(0,1,0);
      2:if(!a_valid || cmd_data[7:4]==0 || cmd_data[7:4]>8 ||
         cmd_data[11:8]==0 || cmd_data[11:8]>8 ||
         (b_valid & (8'hff>>(8-cmd_data[11:8])))!=(8'hff>>(8-cmd_data[11:8])) ||
         (!cmd_data[2]&&!accumulator_valid) ||
         (!cmd_data[2]&&({1'b0,k_count}+{13'b0,cmd_data[7:4]})>17'd65535))respond(0,1,0);
      else begin
       fmt_a<=cmd_data[0];fmt_b<=cmd_data[1];clear_acc<=cmd_data[2];
       active_k<=cmd_data[7:4];active_n<=cmd_data[11:8];
       digit_a<=0;digit_b<=0;state<=PRODUCT;
       k_count<=cmd_data[2]?{12'b0,cmd_data[7:4]}:k_count+{12'b0,cmd_data[7:4]};
       accumulator_valid<=0;
       if(cmd_data[2])for(i=0;i<8;i=i+1)accumulator[i]<=0;
      end
      3:if(accumulator_valid&&cmd_index<4)
        respond({accumulator[2*int'(cmd_index)+1],accumulator[2*int'(cmd_index)]},0,0);
        else respond(0,1,0);
      4:if(!accumulator_valid || (!cmd_data[39]&&!merged_valid) || cmd_data[38:32]>63)
        respond(0,1,0);
       else begin
        scale_lane<=0;scale_factor<=$signed(cmd_data[31:0]);merge_shift<=cmd_data[38:32];
        clear_merge<=cmd_data[39];merge_error<=0;state<=SCALE;
       end
      5:if(merged_valid&&cmd_index<2&&!read_error)respond(read_data,0,read_saturated);
        else respond(0,1,0);
      6:begin
       accumulator_valid<=0;merged_valid<=0;k_count<=0;a_valid<=0;b_valid<=0;
       respond(0,0,0);
      end
      default:respond(0,1,0);
     endcase
    end
    PRODUCT:begin
     for(i=0;i<8;i=i+1)for(j=0;j<8;j=j+1)
      if(i<int'(active_n)&&j<int'(active_k))
       product[8*i+j]<=digit(a[j],fmt_a,digit_a)*digit(b[8*i+j],fmt_b,digit_b);
      else product[8*i+j]<=0;
     state<=REDUCE;
    end
    REDUCE:begin for(i=0;i<8;i=i+1)reduced[i]<=sums[i];state<=ACCUMULATE;end
    ACCUMULATE:if(accumulation_error)begin
     // The legal <=65535 S16 input domain cannot overflow S64. Keep a guard
     // rather than publishing an unproved wrap if the contract is changed.
     accumulator_valid<=0;respond(0,1,0);
    end else begin
     for(i=0;i<8;i=i+1)accumulator[i]<=next_acc[i][63:0];
     if(digit_b==(fmt_b?2:0))begin
      digit_b<=0;
      if(digit_a==(fmt_a?2:0))begin accumulator_valid<=1;state<=DONE;end
      else begin digit_a<=digit_a+1'b1;state<=PRODUCT;end
     end else begin digit_b<=digit_b+1'b1;state<=PRODUCT;end
    end
    DONE:respond(0,0,0);
    SCALE:begin scale_product<=accumulator[scale_lane]*scale_factor;state<=ALIGN;end
    ALIGN:begin
     preview[scale_lane]<=merge_sum[127:0];merge_error<=merge_error|alignment_error;
     if(scale_lane==7)state<=COMMIT;
     else begin scale_lane<=scale_lane+1'b1;state<=SCALE;end
    end
    COMMIT:begin
     if(!merge_error)begin
      for(i=0;i<8;i=i+1)merged[i]<=preview[i];
      merged_valid<=1;
     end
     respond(0,merge_error,0);
    end
    default:begin accumulator_valid<=0;merged_valid<=0;respond(0,1,0);end
   endcase
  end
 end
endmodule
