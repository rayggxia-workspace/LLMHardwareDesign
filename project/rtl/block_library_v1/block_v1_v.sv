// Finite vector macro: 8 element/stat multipliers, 2 pipelined function lanes,
// independent exact group divider/sqrt, 1KiB input + 1KiB output replay.
module block_v1_v(
 input wire clk,reset,cmd_valid,output wire cmd_ready,
 input wire [3:0] cmd_op,input wire [7:0] cmd_index,input wire [127:0] cmd_data,
 output reg rsp_valid,input wire rsp_ready,output reg [127:0] rsp_data,
 output reg rsp_error,rsp_saturated,output wire busy
);
 localparam IDLE=0,P_MUL=1,P_WRITE=2,S_MUL=3,S_WRITE=4,F_RUN=5,
 G_START=6,G_WAIT=7,G_ROOT=8,G_ROOT_WAIT=9,N_LOW=10,N_HIGH=11,N_WRITE=12,
 C_MUL=13,C_ADD=14,C_END=15,T_SCAN=16,T_SAVE=17,
 ROT_LOW=18,ROT_HIGH=19,ROT_ROUND=20,ROT_COMBINE=21,S_REDUCE=22,C_REDUCE=23,
 M_EXEC=24,P_TOTAL=25,P_ROUND=26,G_MUL=27,G_ADD=28;
 localparam F_DRAIN=29,F_DENOM=30;
 reg [4:0] phase;
 reg [4:0] mul_return;
 reg signed [31:0] a[0:7],b[0:7],input_mem[0:255],output_mem[0:255];
 reg [1:0] a_valid,b_valid;reg [63:0] replay_valid;
 reg [8:0] output_count,length,offset;
 reg [3:0] point_op,point_count;reg [6:0] point_shift;
 reg [1:0] point_width;reg broadcast_b,swap_b;
 reg signed [31:0] scalar_b,scalar_c;
 reg signed [31:0] mul_a[0:7];reg signed [32:0] mul_b[0:7],point_b[0:7];
 // Break operand selection from the eight shared multipliers.
 reg signed [31:0] operand_a[0:7];reg signed [32:0] operand_b[0:7];
 // Align reduction validity with the existing registered multiplier operands.
 reg [7:0] operand_reduce_mask;
 reg signed [64:0] product[0:7],low_product[0:7];
 reg signed [127:0] point_total[0:7],point_rounded[0:7];
 reg signed [127:0] rounded,total[0:7],sum;
 // Whole-domain bounds:65535 S32 values fit S64 sum and U80 squares.
 reg signed [63:0] stats_sum[0:1];
 reg [79:0] sumsq,stats_sumsq[0:1];
 reg signed [31:0] maximum,stats_max[0:1],stats_min[0:1];
 reg [15:0] stats_argmax[0:1],stats_argmin[0:1],stats_count[0:1],stats_base;
 reg [1:0] stats_valid,stats_final;reg stats_start,stats_finish,stats_context;
 reg [3:0] stats_n;reg [127:0] block_sum,block_sq;
 reg signed [31:0] block_max,block_min;reg [15:0] block_argmax,block_argmin;
 reg signed [63:0] sum_tree[0:14],stat_block_sum;
 reg [79:0] square_tree[0:14],stat_block_sq;
 reg signed [31:0] max_tree[0:14],min_tree[0:14],stat_block_max,stat_block_min;
 reg [15:0] argmax_tree[0:14],argmin_tree[0:14],stat_block_argmax,stat_block_argmin;
 reg leaf_enabled;reg signed [31:0] leaf_value;
 reg [2:0] function_kind;reg [8:0] function_sent,function_received,function_length;
 // Register the exact two-U32 sum before the full-width accumulator.
 reg [32:0] function_pair_sum;reg function_pair_valid;
 reg composing,function_source_replay,function_subtract_max;reg signed [31:0] rot_low[0:7],rot_high[0:7];
 reg [1:0] compose_kind;reg [63:0] epsilon;
 reg [63:0] factor;
 reg [2:0] group_kind;reg [127:0] group_n,group_d,division_remainder;
 // Norm denominator: registered epsilon/count -> U80 product -> U128 sum.
 // 65535 is the full statistics count bound; no high product bits are lost.
 reg [15:0] norm_count;reg [79:0] norm_product;reg [127:0] norm_square;
 wire group_ready,group_valid,group_error;
 wire [127:0] group_q,group_r;
 wire group_in=phase==G_START||phase==G_ROOT;
 wire group_take=phase==G_WAIT||phase==G_ROOT_WAIT;
 block_v1_v_group group_unit(clk,reset,group_in,group_ready,phase==G_ROOT,
  group_n,group_d,group_valid,group_take,group_q,group_r,group_error);
 reg signed [31:0] fx0,fx1;reg signed [32:0] difference;
 wire function_in=phase==F_RUN&&function_sent<function_length;
 wire function_valid,function_error;wire signed [31:0] fy0,fy1;
 // Keep replay selection/subtract-max separate from LUT decode/interpolation.
 // Two lanes still accept one pair per cycle; add one macro-boundary cycle.
 reg function_input_valid;reg [2:0] function_input_kind;
 reg signed [31:0] function_input_x0,function_input_x1;
 always @(posedge clk)begin
  if(reset)function_input_valid<=0;
  else begin
   function_input_valid<=function_in;
   function_input_kind<=function_kind;
   function_input_x0<=fx0;function_input_x1<=fx1;
  end
 end
 block_v1_v_function function_unit(clk,reset,function_input_valid,function_input_kind,
  function_input_x0,function_input_x1,function_valid,fy0,fy1,function_error);
 // TopK holds forty arbitrary IDs and up to eight selected entries.
 reg [15:0] top_id[0:39],chosen_id[0:7];reg signed [31:0] chosen_value[0:7];
 reg [4:0] id_valid;reg [39:0] selected;
 reg [5:0] top_n,scan_index,best_index;reg [3:0] top_k,top_round;
 reg best_valid,top_valid;reg signed [31:0] best_value;reg [15:0] best_id;
 assign cmd_ready=!reset&&phase==IDLE&&(!rsp_valid||rsp_ready);
 assign busy=!cmd_ready;
 // Parallel byte sums plus explicit group carry preserve all128 result bits.
 // Avoid chaining a wide FMA carry into another wide rounding increment.
 function automatic signed [127:0] add128_grouped;
  input [127:0] left,right;input carry_in;
  reg [8:0] subtotal[0:15];reg [15:0] propagate;
  reg [16:0] carry;reg [127:0] result;integer g;
  begin
   for(g=0;g<16;g=g+1)begin
    subtotal[g]={1'b0,left[8*g+:8]}+{1'b0,right[8*g+:8]};
    propagate[g]=&(left[8*g+:8]^right[8*g+:8]);
   end
   carry[0]=carry_in;
   for(g=0;g<16;g=g+1)begin
    carry[g+1]=subtotal[g][8]|(propagate[g]&carry[g]);
    result[8*g+:8]=subtotal[g][7:0]+carry[g];
   end
   add128_grouped=result;
  end
 endfunction
 function automatic signed [127:0] rne;
  input signed [127:0] v;input [6:0] shift;
  reg signed [127:0] q;reg [127:0] remn,half;
  begin if(shift==0)rne=v;else begin q=v>>>shift;remn=$unsigned(v)&({128{1'b1}}>>(128-shift));half=128'd1<<(shift-1);rne=add128_grouped(q,{127'b0,((remn>half)||((remn==half)&&q[0]))},1'b0);end end
 endfunction
 reg replay_loaded;reg [129:0] twice_remainder,four_remainder;
 reg [128:0] rounded_group;reg root_increment;
 always @* begin
  replay_loaded=1;
  for(integer chunk=0;chunk<64;chunk=chunk+1)if(chunk*4<cmd_data[8:0]&&!replay_valid[chunk])replay_loaded=0;
  fx0=0;fx1=0;difference=0;
  for(integer j=0;j<2;j=j+1)begin
   if(function_sent+j<function_length)begin
    if(function_subtract_max)begin
     difference=$signed({input_mem[function_sent+j][31],input_mem[function_sent+j]})-$signed({maximum[31],maximum});
     if(j==0)fx0=difference< -33'sd1048576 ? -32'sd1048576:difference[31:0];
     else fx1=difference< -33'sd1048576 ? -32'sd1048576:difference[31:0];
    end else if(function_source_replay)begin if(j==0)fx0=input_mem[function_sent+j];else fx1=input_mem[function_sent+j];end
    else if(j==0)fx0=a[function_sent+j];else fx1=a[function_sent+j];
   end
  end
  for(integer l=0;l<8;l=l+1)begin
   leaf_enabled=operand_reduce_mask[l];
   leaf_value=operand_a[l];
   sum_tree[7+l]=leaf_enabled?$signed(leaf_value):64'sd0;
   square_tree[7+l]=leaf_enabled?$unsigned(product[l]):80'd0;
   max_tree[7+l]=leaf_enabled?leaf_value:32'sh80000000;
   min_tree[7+l]=leaf_enabled?leaf_value:32'sh7fffffff;
   argmax_tree[7+l]=leaf_enabled?stats_base+l:16'hffff;
   argmin_tree[7+l]=leaf_enabled?stats_base+l:16'hffff;
  end
  for(integer t=6;t>=0;t=t-1)begin
   sum_tree[t]=sum_tree[2*t+1]+sum_tree[2*t+2];square_tree[t]=square_tree[2*t+1]+square_tree[2*t+2];
   if(max_tree[2*t+1]>max_tree[2*t+2]||(max_tree[2*t+1]==max_tree[2*t+2]&&argmax_tree[2*t+1]<argmax_tree[2*t+2]))begin
    max_tree[t]=max_tree[2*t+1];argmax_tree[t]=argmax_tree[2*t+1];end
   else begin max_tree[t]=max_tree[2*t+2];argmax_tree[t]=argmax_tree[2*t+2];end
   if(min_tree[2*t+1]<min_tree[2*t+2]||(min_tree[2*t+1]==min_tree[2*t+2]&&argmin_tree[2*t+1]<argmin_tree[2*t+2]))begin
    min_tree[t]=min_tree[2*t+1];argmin_tree[t]=argmin_tree[2*t+1];end
   else begin min_tree[t]=min_tree[2*t+2];argmin_tree[t]=argmin_tree[2*t+2];end
  end
  block_sum=sum_tree[0];block_sq=square_tree[0];block_max=max_tree[0];block_min=min_tree[0];block_argmax=argmax_tree[0];block_argmin=argmin_tree[0];
  for(integer l=0;l<8;l=l+1)begin
   // Point results must not see replay/normalization address muxes through
   // the phase-selected shared multiplier operand. Same P_WRITE arithmetic,
   // explicit separate combinational selection before P_TOTAL registration.
   point_b[l]=broadcast_b?{scalar_b[31],scalar_b}:
      swap_b?{b[l^1][31],b[l^1]}:{b[l][31],b[l]};
   mul_a[l]=a[l];mul_b[l]=point_b[l];
   if(phase==S_MUL)mul_b[l]={a[l][31],a[l]};
   else if(phase==C_MUL)begin mul_a[l]=input_mem[offset+l];mul_b[l]={input_mem[offset+l][31],input_mem[offset+l]};end
   else if(phase==N_LOW||phase==N_HIGH)begin
    mul_a[l]=compose_kind==2?output_mem[offset+l]:input_mem[offset+l];
    mul_b[l]=phase==N_LOW?$signed({1'b0,factor[31:0]}):$signed({1'b0,factor[63:32]});
   end else if(phase==ROT_LOW)begin mul_a[l]=input_mem[l];mul_b[l]={b[l&6][31],b[l&6]};end
   else if(phase==ROT_HIGH)begin mul_a[l]=input_mem[l^1];mul_b[l]={b[l|1][31],b[l|1]};end
   else if(broadcast_b)mul_b[l]={scalar_b[31],scalar_b};
   else if(swap_b)mul_b[l]={b[l^1][31],b[l^1]};
   total[l]=0;
   case(point_op)
    0:total[l]=add128_grouped({{96{a[l][31]}},a[l]},{{95{point_b[l][32]}},point_b[l]},1'b0);
    1:total[l]=add128_grouped({{96{a[l][31]}},a[l]},~{{95{point_b[l][32]}},point_b[l]},1'b1);
    2:total[l]=$signed({{63{product[l][64]}},product[l]});
    3:total[l]=add128_grouped({{63{product[l][64]}},product[l]},{{96{scalar_c[31]}},scalar_c},1'b0);
    4:total[l]=$signed(a[l])>$signed(point_b[l])?$signed(a[l]):$signed(point_b[l]);
    5:total[l]=$signed(a[l])<$signed(point_b[l])?$signed(a[l]):$signed(point_b[l]);
    6:total[l]=$signed(a[l])>=$signed(point_b[l])?-128'sd1:128'sd0;
    7:total[l]=$signed({{96{a[l][31]}},a[l]})<<<point_shift;
    8:total[l]=$signed({{96{a[l][31]}},a[l]});
    9:total[l]=a[l]<0?$signed(point_b[l]):$signed({{96{scalar_c[31]}},scalar_c});
    default:total[l]=0;
   endcase
  end
  twice_remainder={2'b0,group_r}<<1;
  rounded_group={1'b0,group_q}+((twice_remainder>{2'b0,group_d})||((twice_remainder=={2'b0,group_d})&&group_q[0]));
  four_remainder={2'b0,division_remainder}<<2;
  root_increment=group_r>group_q||(group_r==group_q&&
    (four_remainder>{2'b0,group_d}||(four_remainder=={2'b0,group_d}&&group_q[0])));
 end
 integer i;reg signed [127:0] lower,upper;
 always @(posedge clk)begin
  if(reset)begin
   phase<=IDLE;mul_return<=IDLE;operand_reduce_mask<=0;rsp_valid<=0;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
   a_valid<=0;b_valid<=0;replay_valid<=0;output_count<=0;stats_valid<=0;stats_final<=0;
   id_valid<=0;top_valid<=0;function_sent<=0;function_received<=0;function_length<=0;composing<=0;function_pair_valid<=0;
   broadcast_b<=0;swap_b<=0;point_op<=0;point_shift<=0;point_width<=0;point_count<=0;
   length<=0;offset<=0;factor<=0;group_n<=0;group_d<=0;group_kind<=0;stats_context<=0;function_source_replay<=0;function_subtract_max<=0;
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    rsp_valid<=1;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
    case(cmd_op)
     0,1:begin
      if(cmd_index>1)rsp_error<=1;
      else begin for(i=0;i<4;i=i+1)if(cmd_op==0)a[4*cmd_index+i]<=cmd_data[32*i+:32];else b[4*cmd_index+i]<=cmd_data[32*i+:32];
       if(cmd_op==0)a_valid[cmd_index]<=1;else b_valid[cmd_index]<=1;end
     end
     2:begin // point op[3:0], shift[10:4], n[14:11], broadcast15, width[17:16], pair18
      if(a_valid!=3||(!cmd_data[15]&&b_valid!=3)||cmd_data[3:0]>9||(cmd_data[3:0]==7&&cmd_data[10:4]>96)||cmd_data[14:11]==0||cmd_data[14:11]>8||cmd_data[17:16]>2||cmd_data[31:19]!=0||cmd_data[127:96]!=0)rsp_error<=1;
      else begin point_op<=cmd_data[3:0];point_shift<=cmd_data[10:4];point_count<=cmd_data[14:11];broadcast_b<=cmd_data[15];point_width<=cmd_data[17:16];swap_b<=cmd_data[18];scalar_b<=cmd_data[63:32];scalar_c<=cmd_data[95:64];phase<=P_MUL;rsp_valid<=0;output_count<=0;end
     end
     3:begin // Statistics: start0, final1, n[5:2], base ID[31:16].
      if(cmd_index>1||a_valid!=3||cmd_data[5:2]==0||cmd_data[5:2]>8||cmd_data[15:6]!=0||cmd_data[127:32]!=0||
        (!cmd_data[0]&&(!stats_valid[cmd_index[0]]||stats_final[cmd_index[0]]||{1'b0,stats_count[cmd_index[0]]}+cmd_data[5:2]>65535))||{1'b0,cmd_data[31:16]}+cmd_data[5:2]>65536)rsp_error<=1;
      else begin stats_context<=cmd_index[0];stats_start<=cmd_data[0];stats_finish<=cmd_data[1];stats_n<=cmd_data[5:2];stats_base<=cmd_data[31:16];phase<=S_MUL;rsp_valid<=0;end
     end
     4:begin
      if(!stats_valid[cmd_index[2]]||cmd_index>6||cmd_index[1:0]>2)rsp_error<=1;
      else case(cmd_index[1:0])0:rsp_data<=stats_sum[cmd_index[2]];1:rsp_data<=stats_sumsq[cmd_index[2]];
       2:rsp_data<={15'b0,stats_final[cmd_index[2]],stats_count[cmd_index[2]],stats_argmin[cmd_index[2]],stats_min[cmd_index[2]],stats_argmax[cmd_index[2]],stats_max[cmd_index[2]]};endcase
     end
     5:begin
      if(a_valid!=3||cmd_data>4)rsp_error<=1;
      else begin function_kind<=cmd_data[2:0];function_sent<=0;function_received<=0;function_length<=8;composing<=0;function_source_replay<=0;function_subtract_max<=0;phase<=F_RUN;rsp_valid<=0;output_count<=0;end
     end
     6:begin // External group op: index0 reciprocal Q16, index1 rsqrt Q16.
      if(cmd_index>1||cmd_data==0)rsp_error<=1;
      else begin group_kind<=cmd_index==0?0:1;group_n<=cmd_index==0?(128'd1<<32):(128'd1<<48);group_d<=cmd_data;phase<=G_START;rsp_valid<=0;end
     end
     7:begin
      if(cmd_index>63)rsp_error<=1;
      else begin for(i=0;i<4;i=i+1)input_mem[4*cmd_index+i]<=cmd_data[32*i+:32];replay_valid[cmd_index]<=1;end
     end
     8:begin // Local composition0/1/2, or global-stat replay4/5/6.
      if((cmd_index>2&&cmd_index<4)||cmd_index>6||cmd_data[8:0]==0||cmd_data[8:0]>256||cmd_data[127:73]!=0||!replay_loaded||
         (cmd_index>=4&&(!stats_valid[0]||!stats_final[0]||stats_count[0]<cmd_data[8:0]))||
         (cmd_index==6&&(!stats_valid[1]||!stats_final[1]||stats_count[1]!=stats_count[0]||stats_sum[1]<=0)))rsp_error<=1;
      else begin
       compose_kind<=cmd_index==6?1:cmd_index[1:0];length<=cmd_data[8:0];epsilon<=cmd_data[72:9];offset<=0;
       rsp_valid<=0;output_count<=0;
       if(cmd_index<4)begin sumsq<=0;maximum<=32'sh80000000;phase<=C_MUL;end
       else if(cmd_index==6)begin group_kind<=4;group_n<=128'd1<<48;group_d<=stats_sum[1];phase<=G_START;end
       else if(stats_sumsq[0]==0&&cmd_data[72:9]==0)begin rsp_error<=1;rsp_valid<=1;end
       else begin
        group_kind<=3;group_n<=cmd_index==4?({112'b0,stats_count[0]}<<96):(128'd1<<96);
        norm_square<={48'b0,stats_sumsq[0]};norm_count<=cmd_index==4?stats_count[0]:16'd1;phase<=G_MUL;
       end
      end
     end
     9:begin // Read four S32 values or explicit packed8/packed16 point result.
      if(cmd_index<64)begin
       if(cmd_index*4>=output_count)rsp_error<=1;
       else for(i=0;i<4;i=i+1)rsp_data[32*i+:32]<=cmd_index*4+i<output_count?output_mem[cmd_index*4+i]:32'd0;
      end else if(cmd_index==64||cmd_index==65)begin
       if(output_count!=8)rsp_error<=1;
       else for(i=0;i<8;i=i+1)if(cmd_index==64)rsp_data[16*i+:16]<=output_mem[i][15:0];else rsp_data[8*i+:8]<=output_mem[i][7:0];
      end else rsp_error<=1;
     end
     10:begin // arbitrary candidate IDs, eight per beat
      if(cmd_index>4)rsp_error<=1;
      else begin for(i=0;i<8;i=i+1)top_id[8*cmd_index+i]<=cmd_data[16*i+:16];id_valid[cmd_index]<=1;top_valid<=0;end
     end
     11:begin // TopK from first N replay values; N[5:0], K[9:6].
      if(cmd_data[127:10]!=0||cmd_data[5:0]==0||cmd_data[5:0]>40||cmd_data[9:6]==0||cmd_data[9:6]>8||cmd_data[9:6]>cmd_data[5:0]||
        (cmd_data[5:0]>0&&(!replay_valid[0]||!id_valid[0]))||
        (cmd_data[5:0]>4&&!replay_valid[1])||(cmd_data[5:0]>8&&(!replay_valid[2]||!id_valid[1]))||
        (cmd_data[5:0]>12&&!replay_valid[3])||(cmd_data[5:0]>16&&(!replay_valid[4]||!id_valid[2]))||
        (cmd_data[5:0]>20&&!replay_valid[5])||(cmd_data[5:0]>24&&(!replay_valid[6]||!id_valid[3]))||
        (cmd_data[5:0]>28&&!replay_valid[7])||(cmd_data[5:0]>32&&(!replay_valid[8]||!id_valid[4]))||(cmd_data[5:0]>36&&!replay_valid[9]))rsp_error<=1;
      else begin top_n<=cmd_data[5:0];top_k<=cmd_data[9:6];selected<=0;top_round<=0;scan_index<=0;best_valid<=0;top_valid<=0;phase<=T_SCAN;rsp_valid<=0;end
     end
     12:begin
      if(!top_valid||cmd_index>=top_k)rsp_error<=1;
      else rsp_data<={80'b0,chosen_id[cmd_index],chosen_value[cmd_index]};
     end
     13:begin a_valid<=0;b_valid<=0;replay_valid<=0;stats_valid<=0;output_count<=0;id_valid<=0;top_valid<=0;end
     14:begin // Replay function, optional subtract context0 global max.
      if(cmd_index>12||cmd_index[2:0]>4||cmd_data[127:9]!=0||cmd_data[8:0]==0||cmd_data[8:0]>256||!replay_loaded||
         (cmd_index[3]&&(!stats_valid[0]||!stats_final[0]||cmd_index[2:0]!=0)))rsp_error<=1;
      else begin
       function_kind<=cmd_index[2:0];function_sent<=0;function_received<=0;function_length<=cmd_data[8:0];
       composing<=0;function_source_replay<=1;function_subtract_max<=cmd_index[3];maximum<=stats_max[0];
       phase<=F_RUN;rsp_valid<=0;output_count<=0;
      end
     end
     15:begin // Eight-element RoPE with four supplied cos/sin coefficient pairs.
      if(cmd_index!=0||cmd_data!=0||!replay_valid[0]||!replay_valid[1]||b_valid!=3)rsp_error<=1;
      else begin phase<=ROT_LOW;rsp_valid<=0;output_count<=0;end
     end
     default:rsp_error<=1;
    endcase
   end else case(phase)
    P_MUL,S_MUL,C_MUL:begin
     for(i=0;i<8;i=i+1)begin
      operand_a[i]<=mul_a[i];operand_b[i]<=mul_b[i];
      if(phase==S_MUL)operand_reduce_mask[i]<=i<stats_n;
      else if(phase==C_MUL)operand_reduce_mask[i]<=offset+i<length;
     end
     mul_return<=phase==P_MUL?P_TOTAL:phase==S_MUL?S_REDUCE:C_REDUCE;
     phase<=M_EXEC;
    end
    M_EXEC:begin
     for(i=0;i<8;i=i+1)product[i]<=operand_a[i]*operand_b[i];
     phase<=mul_return;
    end
    P_TOTAL:begin
     for(i=0;i<8;i=i+1)point_total[i]<=total[i];
     phase<=P_ROUND;
    end
    P_ROUND:begin
     for(i=0;i<8;i=i+1)point_rounded[i]<=rne(point_total[i],point_op==7?7'd0:point_shift);
     phase<=P_WRITE;
    end
    P_WRITE:begin
     lower=point_width==0?-128'sd128:point_width==1?-128'sd32768:-128'sd2147483648;
     upper=point_width==0?128'sd127:point_width==1?128'sd32767:128'sd2147483647;
     for(i=0;i<8;i=i+1)if(i<point_count)begin
      rounded=point_rounded[i];
      if(rounded<lower)begin rounded=lower;rsp_saturated<=1;end
      if(rounded>upper)begin rounded=upper;rsp_saturated<=1;end
      output_mem[i]<=rounded[31:0];
     end
     output_count<=point_count;rsp_valid<=1;phase<=IDLE;
    end
    S_REDUCE,C_REDUCE:begin
     stat_block_sum<=block_sum[63:0];stat_block_sq<=block_sq[79:0];stat_block_max<=block_max;stat_block_min<=block_min;
     stat_block_argmax<=block_argmax;stat_block_argmin<=block_argmin;phase<=phase==S_REDUCE?S_WRITE:C_ADD;
    end
    S_WRITE:begin
     stats_sum[stats_context]<=stats_start?$signed(stat_block_sum):stats_sum[stats_context]+$signed(stat_block_sum);
     stats_sumsq[stats_context]<=stats_start?stat_block_sq:stats_sumsq[stats_context]+stat_block_sq;
     if(stats_start||stat_block_max>stats_max[stats_context]||(stat_block_max==stats_max[stats_context]&&stat_block_argmax<stats_argmax[stats_context]))begin stats_max[stats_context]<=stat_block_max;stats_argmax[stats_context]<=stat_block_argmax;end
     if(stats_start||stat_block_min<stats_min[stats_context]||(stat_block_min==stats_min[stats_context]&&stat_block_argmin<stats_argmin[stats_context]))begin stats_min[stats_context]<=stat_block_min;stats_argmin[stats_context]<=stat_block_argmin;end
     stats_count[stats_context]<=stats_start?{12'b0,stats_n}:stats_count[stats_context]+stats_n;stats_final[stats_context]<=stats_finish;stats_valid[stats_context]<=1;phase<=IDLE;rsp_valid<=1;
    end
    C_ADD:begin
     sumsq<=sumsq+stat_block_sq;if(stat_block_max>maximum)maximum<=stat_block_max;
     if(offset+8>=length)phase<=C_END;else begin offset<=offset+8;phase<=C_MUL;end
    end
    C_END:begin
     if(compose_kind==2)begin composing<=1;function_source_replay<=1;function_subtract_max<=1;function_kind<=0;function_sent<=0;function_received<=0;function_length<=length;sum<=0;function_pair_valid<=0;phase<=F_RUN;end
     else if(sumsq==0&&epsilon==0)begin rsp_error<=1;rsp_valid<=1;phase<=IDLE;end
     else begin group_kind<=3;group_n<=compose_kind==0?({119'b0,length}<<96):(128'd1<<96);
      norm_square<={48'b0,sumsq};norm_count<=compose_kind==0?{7'b0,length}:16'd1;phase<=G_MUL;end
    end
    F_RUN:begin
     if(function_in)function_sent<=function_sent+2;
     if(composing)begin
      if(function_pair_valid)sum<=add128_grouped(sum,{95'b0,function_pair_sum},1'b0);
      function_pair_valid<=function_valid;
     end
     if(function_valid)begin
      output_mem[function_received]<=fy0;if(function_received+1<function_length)output_mem[function_received+1]<=fy1;
      if(function_error)rsp_error<=1;
      if(composing)function_pair_sum<={1'b0,fy0}+{1'b0,(function_received+1<function_length?fy1:32'd0)};
      function_received<=function_received+2;
      if(function_received+2>=function_length)begin
       if(composing)phase<=F_DRAIN;
       else begin output_count<=function_error||rsp_error?0:function_length;rsp_valid<=1;phase<=IDLE;end
      end
     end
    end
    F_DRAIN:begin
     if(function_pair_valid)sum<=add128_grouped(sum,{95'b0,function_pair_sum},1'b0);
     function_pair_valid<=0;phase<=F_DENOM;
    end
    F_DENOM:begin group_kind<=4;group_n<=128'd1<<48;group_d<=sum;phase<=G_START;end
    G_MUL:begin norm_product<=epsilon*norm_count;phase<=G_ADD;end
    G_ADD:begin group_d<=add128_grouped(norm_square,{48'b0,norm_product},1'b0);phase<=G_START;end
    G_START,G_ROOT:if(group_ready)phase<=phase==G_START?G_WAIT:G_ROOT_WAIT;
    G_WAIT:if(group_valid)begin
     if(group_error)begin rsp_error<=1;rsp_valid<=1;phase<=IDLE;end
     else if(group_kind==1||group_kind==3)begin division_remainder<=group_r;group_n<=group_q;phase<=G_ROOT;end
     else if(group_kind==4)begin factor<=rounded_group[63:0];offset<=0;phase<=N_LOW;end
     else begin
      if(rounded_group>2147483647)begin rsp_data<=128'd2147483647;rsp_saturated<=1;end else rsp_data<=rounded_group[127:0];
      rsp_valid<=1;phase<=IDLE;
     end
    end
    G_ROOT_WAIT:if(group_valid)begin
     if(group_kind==3)begin factor<=group_q[63:0]+root_increment;offset<=0;phase<=N_LOW;end
     else begin
      if(group_q+root_increment>2147483647)begin rsp_data<=128'd2147483647;rsp_saturated<=1;end else rsp_data<=group_q+root_increment;
      phase<=IDLE;rsp_valid<=1;
     end
    end
    N_LOW:begin
     for(i=0;i<8;i=i+1)begin operand_a[i]<=mul_a[i];operand_b[i]<=mul_b[i];end
     mul_return<=N_HIGH;phase<=M_EXEC;
    end
    N_HIGH:begin
     for(i=0;i<8;i=i+1)begin low_product[i]<=product[i];operand_a[i]<=mul_a[i];operand_b[i]<=mul_b[i];end
     mul_return<=N_WRITE;phase<=M_EXEC;
    end
    N_WRITE:begin
     for(i=0;i<8;i=i+1)if(offset+i<length)begin
      // Preserve full S128 merge and RNE; avoid a separate ripple carry before RNE.
      rounded=rne(add128_grouped($signed({{63{product[i][64]}},product[i]})<<<32,$signed({{63{low_product[i][64]}},low_product[i]}),1'b0),32);
      if(rounded< -128'sd2147483648)begin rounded=-128'sd2147483648;rsp_saturated<=1;end
      if(rounded>128'sd2147483647)begin rounded=128'sd2147483647;rsp_saturated<=1;end
      output_mem[offset+i]<=rounded[31:0];
     end
     if(offset+8>=length)begin output_count<=length;rsp_valid<=1;phase<=IDLE;end
     else begin offset<=offset+8;phase<=N_LOW;end
    end
    ROT_LOW:begin
     for(i=0;i<8;i=i+1)begin operand_a[i]<=mul_a[i];operand_b[i]<=mul_b[i];end
     mul_return<=ROT_HIGH;phase<=M_EXEC;
    end
    ROT_HIGH:begin
     for(i=0;i<8;i=i+1)begin low_product[i]<=product[i];operand_a[i]<=mul_a[i];operand_b[i]<=mul_b[i];end
     mul_return<=ROT_ROUND;phase<=M_EXEC;
    end
    ROT_ROUND:begin
     for(i=0;i<8;i=i+1)begin
      rounded=rne({{63{low_product[i][64]}},low_product[i]},16);
      if(rounded< -128'sd2147483648)begin rounded=-128'sd2147483648;rsp_saturated<=1;end
      if(rounded>128'sd2147483647)begin rounded=128'sd2147483647;rsp_saturated<=1;end
      rot_low[i]<=rounded[31:0];
      rounded=rne({{63{product[i][64]}},product[i]},16);
      if(rounded< -128'sd2147483648)begin rounded=-128'sd2147483648;rsp_saturated<=1;end
      if(rounded>128'sd2147483647)begin rounded=128'sd2147483647;rsp_saturated<=1;end
      rot_high[i]<=rounded[31:0];
     end
     phase<=ROT_COMBINE;
    end
    ROT_COMBINE:begin
     for(i=0;i<8;i=i+1)begin
      rounded=i[0]?$signed({{96{rot_low[i][31]}},rot_low[i]})+$signed({{96{rot_high[i][31]}},rot_high[i]}):
                    $signed({{96{rot_low[i][31]}},rot_low[i]})-$signed({{96{rot_high[i][31]}},rot_high[i]});
      if(rounded< -128'sd2147483648)begin rounded=-128'sd2147483648;rsp_saturated<=1;end
      if(rounded>128'sd2147483647)begin rounded=128'sd2147483647;rsp_saturated<=1;end
      output_mem[i]<=rounded[31:0];
     end
     output_count<=8;rsp_valid<=1;phase<=IDLE;
    end
    T_SCAN:begin
     if(!selected[scan_index]&&(!best_valid||input_mem[scan_index]>best_value||(input_mem[scan_index]==best_value&&top_id[scan_index]<best_id)))begin
      best_valid<=1;best_value<=input_mem[scan_index];best_id<=top_id[scan_index];best_index<=scan_index;
     end
     if(scan_index+1==top_n)phase<=T_SAVE;else scan_index<=scan_index+1;
    end
    T_SAVE:begin
     chosen_value[top_round]<=best_value;chosen_id[top_round]<=best_id;selected[best_index]<=1;
     if(top_round+1==top_k)begin top_valid<=1;rsp_valid<=1;phase<=IDLE;end
     else begin top_round<=top_round+1;scan_index<=0;best_valid<=0;phase<=T_SCAN;end
    end
    default:begin end
   endcase
  end
 end
endmodule
