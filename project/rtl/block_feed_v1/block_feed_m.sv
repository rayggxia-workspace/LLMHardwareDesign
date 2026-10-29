// Issue130 candidate, not a physically qualified replacement of block_v1_m.
// 64 shared S8 multipliers, two banks, four K8 tiles and eight A rows per bank.
// Independent A128/B512 loading; A replacement deliberately preserves B.
// Numeric helpers/merge pipeline follow the fixed Issue121 M implementation.
module block_feed_m (
 input wire clk, reset,
 input wire a_valid, output wire a_ready,
 input wire a_bank, input wire [2:0] a_row, input wire [1:0] a_tile,
 input wire a_wide, input wire [127:0] a_data,
 input wire b_valid, output wire b_ready,
 input wire b_bank, input wire [1:0] b_tile,
 input wire b_wide, b_half, input wire [511:0] b_data,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_op, input wire [5:0] cmd_index,
 input wire [63:0] cmd_data,
 output reg rsp_valid, input wire rsp_ready,
 output reg [127:0] rsp_data, output reg rsp_error, rsp_saturated,
 output wire busy
);
 localparam IDLE=0, ISSUE=1, DRAIN=2, CHECK_ACC=3, DONE=4,
            SCALE=5, SCALE_MULT=6, SCALE_JOIN=7, ALIGN=8,
            MERGE_LOW=9, MERGE_HIGH=10, COMMIT=11,
            READ_SHIFT=12, READ_ROUND=13, READ_CLAMP=14;
 reg [3:0] state;
 reg signed [15:0] aa[0:511], bb[0:511];
 reg [63:0] av, af;
 reg [1:0] bv[0:7]; reg [7:0] bf;
 reg signed [63:0] acc[0:63];
 reg signed [127:0] merged[0:63], preview[0:7];
 reg [7:0] acc_valid, merged_valid;
 reg [15:0] k_count[0:7]; reg [3:0] n_count[0:7];
 reg execution_bank, fmt_a, fmt_b;
 reg [3:0] rows, tiles, last_k, active_n;
 reg [2:0] issue_row, product_row, reduce_row, context_row, scale_lane;
 reg [1:0] issue_tile, issue_a, issue_b;
 reg signed [7:0] lhs[0:63], rhs[0:63];
 reg signed [15:0] product[0:63];
 reg signed [18:0] reduced[0:7];
 reg product_valid, reduce_valid, product_last, reduce_last;
 reg [5:0] product_shift, reduce_shift;
 reg [7:0] sign_left, sign_right, sign_result;
 reg check_valid, accumulation_fault;
 wire observed_overflow=|((~(sign_left^sign_right))&(sign_result^sign_left));
 wire locked=state==ISSUE||state==DRAIN||state==CHECK_ACC||state==DONE;
 assign cmd_ready=!reset&&state==IDLE&&(!rsp_valid||rsp_ready);
 wire start=cmd_valid&&cmd_ready&&cmd_op==10;
 wire clear_banks=cmd_valid&&cmd_ready&&cmd_op==6;
 wire clear_bank=cmd_valid&&cmd_ready&&cmd_op==11;
 // Do not race descriptor admission/bank invalidation against a data write.
 assign a_ready=!reset&&!clear_banks&&!(clear_bank&&cmd_index[0]==a_bank)&&
                !(locked&&execution_bank==a_bank)&&!(start&&cmd_index[5]==a_bank);
 assign b_ready=!reset&&!clear_banks&&!(clear_bank&&cmd_index[0]==b_bank)&&
                !(locked&&execution_bank==b_bank)&&!(start&&cmd_index[5]==b_bank)&&
                ((!b_wide&&!b_half)||(b_wide&&(!b_half||
                  (bv[{b_bank,b_tile}][0]&&bf[{b_bank,b_tile}]))));
 assign busy=state!=IDLE||rsp_valid;

 function automatic signed [7:0] digit;
  input signed [15:0] value; input wide; input [1:0] part;
  begin
   if(!wide)digit=value[7:0];
   else case(part)
    0:digit={1'b0,value[6:0]};
    1:digit={1'b0,value[13:7]};
    default:digit={{6{value[15]}},value[15:14]};
   endcase
  end
 endfunction
 function automatic [64:0] add_s64_grouped;
  input [63:0] left,right;
  reg [8:0] subtotal[0:7]; reg [7:0] propagate;
  reg [8:0] carry; reg [64:0] result; integer g;
  begin
   for(g=0;g<8;g=g+1)begin
    subtotal[g]={1'b0,left[8*g+:8]}+{1'b0,right[8*g+:8]};
    propagate[g]=&(left[8*g+:8]^right[8*g+:8]);
   end
   carry[0]=0;
   for(g=0;g<8;g=g+1)begin
    carry[g+1]=subtotal[g][8]|(propagate[g]&carry[g]);
    result[8*g+:8]=subtotal[g][7:0]+{7'b0,carry[g]};
   end
   result[64]=left[63]^right[63]^carry[8];
   add_s64_grouped=result;
  end
 endfunction

 reg descriptor_ok; reg [16:0] descriptor_k;
 reg [5:0] ai; reg [2:0] bi;
 always @* begin
  descriptor_k=({13'b0,cmd_data[14:12]}-1)*8+{13'b0,cmd_data[7:4]};
  descriptor_ok=cmd_index[4:0]==0&&cmd_data[63:19]==0&&!cmd_data[3]&&
    cmd_data[7:4]>0&&cmd_data[7:4]<=8&&cmd_data[11:8]>0&&cmd_data[11:8]<=8&&
    cmd_data[14:12]>0&&cmd_data[14:12]<=4&&cmd_data[18:15]>0&&cmd_data[18:15]<=8;
  ai=0;bi=0;
  for(integer t=0;t<4;t=t+1)if(t<cmd_data[14:12])begin
   bi={cmd_index[5],t[1:0]};
   if(bv[bi]!=2'b11||bf[bi]!=cmd_data[1])descriptor_ok=0;
   for(integer r=0;r<8;r=r+1)if(r<cmd_data[18:15])begin
    ai={cmd_index[5],r[2:0],t[1:0]};
    if(!av[ai]||af[ai]!=cmd_data[0])descriptor_ok=0;
   end
  end
  for(integer r=0;r<8;r=r+1)if(r<cmd_data[18:15]&&!cmd_data[2])
   if(!acc_valid[r]||n_count[r]!=cmd_data[11:8]||{1'b0,k_count[r]}+descriptor_k>65535)
    descriptor_ok=0;
 end

 reg signed [18:0] sums[0:7]; reg [64:0] next_acc[0:7];
 always @* begin
  for(integer n=0;n<8;n=n+1)begin
   for(integer k=0;k<8;k=k+1)begin
    lhs[8*n+k]=0;rhs[8*n+k]=0;
    if(state==ISSUE&&n<active_n&&({2'b0,issue_tile}+4'd1<tiles||k<last_k))begin
     lhs[8*n+k]=digit(aa[int'(execution_bank)*256+int'(issue_row)*32+int'(issue_tile)*8+k],fmt_a,issue_a);
     rhs[8*n+k]=digit(bb[(int'(execution_bank)*4+int'(issue_tile))*64+8*n+k],fmt_b,issue_b);
    end
   end
   sums[n]=
    (($signed({{3{product[8*n][15]}},product[8*n]})+
      $signed({{3{product[8*n+1][15]}},product[8*n+1]}))+
     ($signed({{3{product[8*n+2][15]}},product[8*n+2]})+
      $signed({{3{product[8*n+3][15]}},product[8*n+3]})))+
    (($signed({{3{product[8*n+4][15]}},product[8*n+4]})+
      $signed({{3{product[8*n+5][15]}},product[8*n+5]}))+
     ($signed({{3{product[8*n+6][15]}},product[8*n+6]})+
      $signed({{3{product[8*n+7][15]}},product[8*n+7]})));
   next_acc[n]=add_s64_grouped(acc[int'(reduce_row)*8+n],
                        $signed({{45{reduced[n][18]}},reduced[n]})<<<reduce_shift);
  end
 end

 reg signed [31:0] scale_factor;
 reg signed [63:0] scale_operand,scale_low,scale_upper;
 reg signed [95:0] scale_product;
 reg [6:0] merge_shift; reg clear_merge, merge_error, merge_alignment_error;
 reg [127:0] merge_left,merge_right; reg [64:0] merge_low;
 reg signed [64:0] merge_upper;
 wire signed [64:0] merge_high=merge_upper+$signed({64'b0,merge_low[64]});
 wire signed [255:0] aligned_scale=$signed({{160{scale_product[95]}},scale_product})<<<merge_shift;
 wire alignment_error=aligned_scale[255:127]!={129{aligned_scale[127]}};
 reg read_index; reg [6:0] read_shift; reg [1:0] read_width;
 reg signed [127:0] read_q[0:3],read_r[0:3]; reg [3:0] read_increment;
 function automatic round_increment;
  input signed [127:0] value; input [6:0] shift;
  reg [127:0] remainder,half;
  begin
   remainder=$unsigned(value)&({128{1'b1}}>>(128-shift));
   half=128'd1<<(shift-1);
   round_increment=shift!=0&&(remainder>half||
     (remainder==half&&(($unsigned(value) >> shift)&128'd1)!=0));
  end
 endfunction
 reg [127:0] read_data; reg read_saturated;
 reg signed [127:0] rounded,lo,hi;
 always @* begin
  read_data=0;read_saturated=0;rounded=0;
  case(read_width)
   0:begin lo=-128;hi=127;end
   1:begin lo=-32768;hi=32767;end
   default:begin lo=-128'sd2147483648;hi=2147483647;end
  endcase
  for(integer j=0;j<4;j=j+1)begin
   rounded=read_r[j];
   if(rounded<lo)begin rounded=lo;read_saturated=1;end
   else if(rounded>hi)begin rounded=hi;read_saturated=1;end
   read_data[32*j+:32]=rounded[31:0];
  end
 end
 task automatic respond;
  input [127:0] data; input error,saturated;
  begin rsp_valid<=1;rsp_data<=data;rsp_error<=error;rsp_saturated<=saturated;state<=IDLE;end
 endtask

 integer i;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;rsp_valid<=0;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
   av<=0;af<=0;bf<=0;acc_valid<=0;merged_valid<=0;
   execution_bank<=0;fmt_a<=0;fmt_b<=0;rows<=0;tiles<=0;last_k<=0;active_n<=0;
   issue_row<=0;issue_tile<=0;issue_a<=0;issue_b<=0;product_row<=0;reduce_row<=0;
   product_valid<=0;reduce_valid<=0;product_last<=0;reduce_last<=0;
   product_shift<=0;reduce_shift<=0;check_valid<=0;accumulation_fault<=0;
   sign_left<=0;sign_right<=0;sign_result<=0;context_row<=0;scale_lane<=0;
   scale_factor<=0;scale_operand<=0;scale_low<=0;scale_upper<=0;scale_product<=0;
   merge_shift<=0;clear_merge<=0;merge_error<=0;merge_alignment_error<=0;
   merge_left<=0;merge_right<=0;merge_low<=0;merge_upper<=0;
   read_index<=0;read_shift<=0;read_width<=0;read_increment<=0;
   for(i=0;i<8;i=i+1)begin bv[i]<=0;k_count[i]<=0;n_count[i]<=0;end
   // Operand/result payload is deliberately not reset; validity gates all use.
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(a_valid&&a_ready)begin
    av[{a_bank,a_row,a_tile}]<=1;af[{a_bank,a_row,a_tile}]<=a_wide;
    for(i=0;i<8;i=i+1)aa[int'({a_bank,a_row,a_tile})*8+i]<=
      a_wide?$signed(a_data[16*i+:16]):$signed({{8{a_data[8*i+7]}},a_data[8*i+:8]});
   end
   if(b_valid&&b_ready)begin
    bf[{b_bank,b_tile}]<=b_wide;
    if(!b_wide)begin
     bv[{b_bank,b_tile}]<=2'b11;
     for(i=0;i<64;i=i+1)bb[int'({b_bank,b_tile})*64+i]<=$signed({{8{b_data[8*i+7]}},b_data[8*i+:8]});
    end else begin
     bv[{b_bank,b_tile}]<=b_half?2'b11:2'b01;
     for(i=0;i<32;i=i+1)bb[int'({b_bank,b_tile})*64+int'(b_half)*32+i]<=$signed(b_data[16*i+:16]);
    end
   end
   check_valid<=0;
   if(check_valid)accumulation_fault<=accumulation_fault|observed_overflow;
   case(state)
    IDLE:if(cmd_valid&&cmd_ready)case(cmd_op)
     3:if(acc_valid[cmd_index[5:3]]&&cmd_index[2:0]<4&&cmd_data==0)
        respond({acc[int'(cmd_index[5:3])*8+2*int'(cmd_index[1:0])+1],
                 acc[int'(cmd_index[5:3])*8+2*int'(cmd_index[1:0])]},0,0);
       else respond(0,1,0);
     4:if(cmd_index[2:0]!=0||!acc_valid[cmd_index[5:3]]||
              (!cmd_data[39]&&!merged_valid[cmd_index[5:3]])||cmd_data[38:32]>63||cmd_data[63:40]!=0)
        respond(0,1,0);
       else begin context_row<=cmd_index[5:3];scale_lane<=0;
        scale_factor<=cmd_data[31:0];merge_shift<=cmd_data[38:32];
        clear_merge<=cmd_data[39];merge_error<=0;state<=SCALE;end
     5:if(merged_valid[cmd_index[5:3]]&&cmd_index[2:0]<2&&cmd_data[9:8]<3&&
           cmd_data[63:10]==0&&!cmd_data[7])begin
        context_row<=cmd_index[5:3];read_index<=cmd_index[0];read_shift<=cmd_data[6:0];
        read_width<=cmd_data[9:8];state<=READ_SHIFT;
       end else respond(0,1,0);
     6:if(cmd_index!=0||cmd_data!=0)respond(0,1,0);
       else begin av<=0;for(i=0;i<8;i=i+1)begin bv[i]<=0;k_count[i]<=0;n_count[i]<=0;end
        acc_valid<=0;merged_valid<=0;respond(0,0,0);end
     10:if(!descriptor_ok)respond(0,1,0);
       else begin
        execution_bank<=cmd_index[5];fmt_a<=cmd_data[0];fmt_b<=cmd_data[1];
        last_k<=cmd_data[7:4];active_n<=cmd_data[11:8];tiles<={1'b0,cmd_data[14:12]};rows<=cmd_data[18:15];
        issue_tile<=0;issue_row<=0;issue_a<=0;issue_b<=0;
        product_valid<=0;reduce_valid<=0;check_valid<=0;accumulation_fault<=0;
        for(i=0;i<8;i=i+1)if(i<cmd_data[18:15])begin
         acc_valid[i]<=0;n_count[i]<=cmd_data[11:8];
         k_count[i]<=cmd_data[2]?descriptor_k[15:0]:k_count[i]+descriptor_k[15:0];
         if(cmd_data[2])for(integer n=0;n<8;n=n+1)acc[8*i+n]<=0;
        end
        state<=ISSUE;
       end
     11:if(cmd_index[5:1]!=0||cmd_data!=0)respond(0,1,0);
       else begin
        for(i=0;i<32;i=i+1)av[int'(cmd_index[0])*32+i]<=0;
        for(i=0;i<4;i=i+1)bv[int'(cmd_index[0])*4+i]<=0;
        respond(0,0,0);
       end
     default:respond(0,1,0);
    endcase
    ISSUE,DRAIN:begin
     product_valid<=state==ISSUE;reduce_valid<=product_valid;
     if(state==ISSUE)begin
      for(i=0;i<64;i=i+1)product[i]<=lhs[i]*rhs[i];
      product_row<=issue_row;product_shift<=7*({4'b0,issue_a}+{4'b0,issue_b});
      product_last<={2'b0,issue_tile}+4'd1==tiles&&{1'b0,issue_row}+4'd1==rows&&
                    issue_a==(fmt_a?2:0)&&issue_b==(fmt_b?2:0);
      if({1'b0,issue_row}+4'd1==rows)begin
       issue_row<=0;
       if(issue_b==(fmt_b?2:0))begin
        issue_b<=0;
        if(issue_a==(fmt_a?2:0))begin
         issue_a<=0;
         if({2'b0,issue_tile}+4'd1==tiles)state<=DRAIN;else issue_tile<=issue_tile+1'b1;
        end else issue_a<=issue_a+1'b1;
       end else issue_b<=issue_b+1'b1;
      end else issue_row<=issue_row+1'b1;
     end
     if(product_valid)begin
      for(i=0;i<8;i=i+1)reduced[i]<=sums[i];
      reduce_row<=product_row;reduce_shift<=product_shift;reduce_last<=product_last;
     end
     if(reduce_valid)begin
      check_valid<=1;
      for(i=0;i<8;i=i+1)begin
       acc[int'(reduce_row)*8+i]<=next_acc[i][63:0];
       sign_left[i]<=acc[int'(reduce_row)*8+i][63];
       sign_right[i]<=reduced[i][18];sign_result[i]<=next_acc[i][63];
      end
      if(reduce_last)state<=CHECK_ACC;
     end
    end
    CHECK_ACC:state<=DONE;
    DONE:begin
     for(i=0;i<8;i=i+1)if(i<rows)acc_valid[i]<=!accumulation_fault;
     respond(128'h80000000000000000000000000000000,accumulation_fault,0);
    end
    SCALE:begin scale_operand<=acc[int'(context_row)*8+int'(scale_lane)];state<=SCALE_MULT;end
    SCALE_MULT:begin
     scale_low<=$signed({1'b0,scale_operand[31:0]})*scale_factor;
     scale_upper<=$signed(scale_operand[63:32])*scale_factor;state<=SCALE_JOIN;
    end
    SCALE_JOIN:begin
     scale_product<=$signed({{32{scale_low[63]}},scale_low})+$signed({scale_upper,32'b0});state<=ALIGN;
    end
    ALIGN:begin
     merge_left<=clear_merge?128'd0:merged[int'(context_row)*8+int'(scale_lane)];
     merge_right<=aligned_scale[127:0];merge_alignment_error<=alignment_error;state<=MERGE_LOW;
    end
    MERGE_LOW:begin
     merge_low<={1'b0,merge_left[63:0]}+{1'b0,merge_right[63:0]};
     merge_upper<=$signed({merge_left[127],merge_left[127:64]})+
                  $signed({merge_right[127],merge_right[127:64]});state<=MERGE_HIGH;
    end
    MERGE_HIGH:begin
     preview[scale_lane]<={merge_high[63:0],merge_low[63:0]};
     merge_error<=merge_error|merge_alignment_error|(merge_high[64]!=merge_high[63]);
     if(scale_lane==7)state<=COMMIT;else begin scale_lane<=scale_lane+1'b1;state<=SCALE;end
    end
    COMMIT:begin
     if(!merge_error)begin
      for(i=0;i<8;i=i+1)merged[int'(context_row)*8+i]<=preview[i];
      merged_valid[context_row]<=1;
     end
     respond(0,merge_error,0);
    end
    READ_SHIFT:begin
     for(i=0;i<4;i=i+1)begin
      read_q[i]<=merged[int'(context_row)*8+4*int'(read_index)+i]>>>read_shift;
      read_increment[i]<=round_increment(merged[int'(context_row)*8+4*int'(read_index)+i],read_shift);
     end
     state<=READ_ROUND;
    end
    READ_ROUND:begin for(i=0;i<4;i=i+1)read_r[i]<=read_q[i]+$signed({127'b0,read_increment[i]});state<=READ_CLAMP;end
    READ_CLAMP:respond(read_data,0,read_saturated);
    default:begin acc_valid<=0;merged_valid<=0;respond(0,1,0);end
   endcase
  end
 end
endmodule
