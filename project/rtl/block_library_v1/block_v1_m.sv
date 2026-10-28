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
            SCALE=5,ALIGN=6,COMMIT=7,BURST=8,DRAIN=9,
            READ_SHIFT=10,READ_ROUND=11,READ_CLAMP=12;
 reg [3:0] state;
 reg signed [15:0] a[0:7],b[0:63];
 reg a_valid;reg [7:0] b_valid;
 reg signed [15:0] product[0:63];
 reg signed [7:0] multiplicand[0:63],multiplier[0:63];
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
 // Two finite operand banks, four K8 tiles each. S16 uses radix128 products
 // in the same64 physical S8 multipliers. Loader and active bank are distinct.
 reg signed [15:0] tile_a[0:63],tile_b[0:511];
 reg [7:0] tile_a_valid;reg [7:0] tile_b_valid[0:7];
 reg [7:0] tile_fmt_a,tile_fmt_b;
 reg execution_bank;reg [2:0] tile_count;reg [1:0] issue_tile;
 reg [1:0] issue_a,issue_b;reg [3:0] last_k;
 reg product_valid,reduce_valid,product_last,reduce_last;
 reg [5:0] product_shift,reduce_shift;
 reg burst_completion;
 reg read_index;reg [6:0] read_shift;reg [1:0] read_width;
 reg signed [127:0] read_q[0:3],read_r[0:3];reg [3:0] read_increment;
 reg [127:0] read_remainder,read_half;
 wire burst_busy=state==BURST||state==DRAIN;
 wire [5:0] digit_shift = burst_busy?reduce_shift:7*({4'b0,digit_a}+{4'b0,digit_b});
 assign cmd_ready=!reset&&(!rsp_valid||rsp_ready)&&
   (state==IDLE||(burst_busy&&cmd_op>=7&&cmd_op<=9&&cmd_index[5]!=execution_bank));
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
  for(integer r=0;r<8;r=r+1)for(integer c=0;c<8;c=c+1)begin
   multiplicand[8*r+c]=0;multiplier[8*r+c]=0;
   if(state==BURST)begin
    if(r<int'(active_n)&&(issue_tile+1<tile_count||c<int'(last_k)))begin
     multiplicand[8*r+c]=digit(tile_a[(int'(execution_bank)*4+int'(issue_tile))*8+c],fmt_a,issue_a);
     multiplier[8*r+c]=digit(tile_b[(int'(execution_bank)*4+int'(issue_tile))*64+8*r+c],fmt_b,issue_b);
    end
   end else if(r<int'(active_n)&&c<int'(active_k))begin
    multiplicand[8*r+c]=digit(a[c],fmt_a,digit_a);multiplier[8*r+c]=digit(b[8*r+c],fmt_b,digit_b);
   end
  end
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
  case(read_width)
   0:begin lower_limit=-128;upper_limit=127;end
   1:begin lower_limit=-32768;upper_limit=32767;end
   2:begin lower_limit=-128'sd2147483648;upper_limit=2147483647;end
   default:read_error=1;
  endcase
  for(integer r=0;r<4;r=r+1)begin
   lane_number=4*int'(read_index)+r;
   if(lane_number<8)begin
    rounded=read_r[r];
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

 // Loader acknowledgement does not terminate the independently running core.
 // A new A beat starts a tile generation and invalidates its old B words.
 task automatic load_tile;
  integer t,base,k,chunk;
  begin
   t=int'(cmd_index[5:3]);base=t*8;chunk=int'(cmd_index[2:0]);
   rsp_valid<=1;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
   if(cmd_op==7)begin
    if(cmd_index[2:1]!=0)rsp_error<=1;
    else begin
     for(k=0;k<8;k=k+1)tile_a[base+k]<=cmd_index[0]?$signed(cmd_data[16*k+:16]):$signed(cmd_data[8*k+:8]);
     tile_a_valid[t]<=1;tile_fmt_a[t]<=cmd_index[0];tile_b_valid[t]<=0;
    end
   end else if(!tile_a_valid[t]||(cmd_op==8&&chunk>=4)||
       (tile_b_valid[t]!=0&&tile_fmt_b[t]!=(cmd_op==9)))rsp_error<=1;
   else begin
    tile_fmt_b[t]<=cmd_op==9;
    if(cmd_op==8)begin
     for(k=0;k<16;k=k+1)tile_b[t*64+chunk*16+k]<=$signed(cmd_data[8*k+:8]);
     tile_b_valid[t][{cmd_index[1:0],1'b0}+:2]<=2'b11;
    end else begin
     for(k=0;k<8;k=k+1)tile_b[t*64+chunk*8+k]<=$signed(cmd_data[16*k+:16]);
     tile_b_valid[t][chunk]<=1;
    end
   end
  end
 endtask

 reg tiles_loaded;reg [16:0] descriptor_k;
 always @* begin
  tiles_loaded=1;
  descriptor_k=({14'b0,cmd_data[14:12]}-1)*8+{13'b0,cmd_data[7:4]};
  for(integer t=0;t<4;t=t+1)if(t<cmd_data[14:12])begin
   if(!tile_a_valid[int'(cmd_index[5])*4+t]||tile_fmt_a[int'(cmd_index[5])*4+t]!=cmd_data[0]||
      tile_fmt_b[int'(cmd_index[5])*4+t]!=cmd_data[1]||
      (tile_b_valid[int'(cmd_index[5])*4+t]&(8'hff>>(8-cmd_data[11:8])))!=(8'hff>>(8-cmd_data[11:8])))tiles_loaded=0;
  end
 end

 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;rsp_valid<=0;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
   a_valid<=0;b_valid<=0;accumulator_valid<=0;merged_valid<=0;k_count<=0;
   fmt_a<=0;fmt_b<=0;clear_acc<=0;active_k<=0;active_n<=0;
   digit_a<=0;digit_b<=0;scale_lane<=0;scale_factor<=0;
   tile_a_valid<=0;tile_fmt_a<=0;tile_fmt_b<=0;execution_bank<=0;tile_count<=0;
   issue_tile<=0;issue_a<=0;issue_b<=0;last_k<=0;product_valid<=0;reduce_valid<=0;
   product_last<=0;reduce_last<=0;product_shift<=0;reduce_shift<=0;burst_completion<=0;
   read_index<=0;read_shift<=0;read_width<=0;read_increment<=0;
   for(i=0;i<8;i=i+1)tile_b_valid[i]<=0;
   merge_shift<=0;clear_merge<=0;merge_error<=0;scale_product<=0;
   for(i=0;i<8;i=i+1)begin accumulator[i]<=0;merged[i]<=0;preview[i]<=0;reduced[i]<=0;end
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(burst_busy&&cmd_valid&&cmd_ready)load_tile();
   if(state==PRODUCT||state==BURST)for(i=0;i<64;i=i+1)product[i]<=multiplicand[i]*multiplier[i];
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
       burst_completion<=0;
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
      5:if(merged_valid&&cmd_index<2&&cmd_data[9:8]<3)begin
         read_index<=cmd_index[0];read_shift<=cmd_data[6:0];read_width<=cmd_data[9:8];state<=READ_SHIFT;
        end
        else respond(0,1,0);
      6:begin
       accumulator_valid<=0;merged_valid<=0;k_count<=0;a_valid<=0;b_valid<=0;
       tile_a_valid<=0;for(i=0;i<8;i=i+1)tile_b_valid[i]<=0;
       respond(0,0,0);
      end
      7,8,9:load_tile();
      10:if(cmd_index[4:0]!=0||cmd_data[127:15]!=0||cmd_data[3]||
        cmd_data[7:4]==0||cmd_data[7:4]>8||cmd_data[11:8]==0||cmd_data[11:8]>8||
        cmd_data[14:12]==0||cmd_data[14:12]>4||!tiles_loaded||
        (!cmd_data[2]&&(!accumulator_valid||{1'b0,k_count}+descriptor_k>65535)))respond(0,1,0);
       else begin
        fmt_a<=cmd_data[0];fmt_b<=cmd_data[1];active_n<=cmd_data[11:8];last_k<=cmd_data[7:4];
        execution_bank<=cmd_index[5];tile_count<=cmd_data[14:12];issue_tile<=0;issue_a<=0;issue_b<=0;
        product_valid<=0;reduce_valid<=0;burst_completion<=1;accumulator_valid<=0;
        k_count<=cmd_data[2]?descriptor_k[15:0]:k_count+descriptor_k[15:0];
        if(cmd_data[2])for(i=0;i<8;i=i+1)accumulator[i]<=0;
        state<=BURST;
       end
      default:respond(0,1,0);
     endcase
    end
    PRODUCT:state<=REDUCE;
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
    BURST,DRAIN:begin
     product_valid<=state==BURST;reduce_valid<=product_valid;
     if(state==BURST)begin
      product_shift<=7*({4'b0,issue_a}+{4'b0,issue_b});
      product_last<=issue_tile+1==tile_count&&issue_a==(fmt_a?2:0)&&issue_b==(fmt_b?2:0);
      if(issue_b==(fmt_b?2:0))begin
       issue_b<=0;
       if(issue_a==(fmt_a?2:0))begin
        issue_a<=0;
        if(issue_tile+1==tile_count)state<=DRAIN;else issue_tile<=issue_tile+1'b1;
       end else issue_a<=issue_a+1'b1;
      end else issue_b<=issue_b+1'b1;
     end
     if(product_valid)begin
      for(i=0;i<8;i=i+1)reduced[i]<=sums[i];
      reduce_shift<=product_shift;reduce_last<=product_last;
     end
     if(reduce_valid)begin
      if(accumulation_error)begin
       accumulator_valid<=0;product_valid<=0;reduce_valid<=0;
       // Completion waits for the response register rather than overwriting
       // an accepted loader acknowledgement. Legal S16/fullK cannot overflow.
       state<=DONE;
      end else begin
       for(i=0;i<8;i=i+1)accumulator[i]<=next_acc[i][63:0];
       if(reduce_last)begin accumulator_valid<=1;state<=DONE;end
      end
     end
    end
    DONE:if(!rsp_valid||rsp_ready)respond(burst_completion?128'h80000000000000000000000000000000:128'd0,!accumulator_valid,0);
    READ_SHIFT:begin
     for(i=0;i<4;i=i+1)begin
      read_q[i]<=merged[4*int'(read_index)+i]>>>read_shift;
      read_remainder=$unsigned(merged[4*int'(read_index)+i])&({128{1'b1}}>>(128-read_shift));
      read_half=128'd1<<(read_shift-1);
      read_increment[i]<=read_shift!=0&&((read_remainder>read_half)||
                         (read_remainder==read_half&&((merged[4*int'(read_index)+i]>>>read_shift)&1)));
     end
     state<=READ_ROUND;
    end
    READ_ROUND:begin for(i=0;i<4;i=i+1)read_r[i]<=read_q[i]+read_increment[i];state<=READ_CLAMP;end
    READ_CLAMP:respond(read_data,0,read_saturated);
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
