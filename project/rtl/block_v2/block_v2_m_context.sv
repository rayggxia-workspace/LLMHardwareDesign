// Isolated Issue247 candidate; original op10 eight-row mode is preserved.
// M v2: 64 S8 multipliers; row-first K32 segment; 16 S40 partial slots.
// Two scale lanes sustain one pair/cycle, with S64 per-row atomic commit.
// Segments are scaled without rounding; a shared quantization scale therefore
// distributes exactly across K segments. RNE occurs only at final readout.
module block_v2_m_context #(parameter integer CONTEXTS=8,parameter integer A_WORDS_PER_BEAT=1)(
 input wire clk,reset,
 input wire [A_WORDS_PER_BEAT-1:0] a_valid,output wire a_ready,input wire a_bank,
 input wire [3*A_WORDS_PER_BEAT-1:0] a_row,input wire [2*A_WORDS_PER_BEAT-1:0] a_tile,
 input wire a_wide,input wire [128*A_WORDS_PER_BEAT-1:0] a_data,
 input wire b_valid,output wire b_ready,input wire b_bank,input wire [1:0] b_tile,
 input wire b_wide,b_half,input wire [511:0] b_data,
 input wire cmd_valid,output wire cmd_ready,input wire [3:0] cmd_op,
 input wire [5:0] cmd_index,input wire [63:0] cmd_data,
 output reg rsp_valid,input wire rsp_ready,output reg [127:0] rsp_data,
 output reg rsp_error,rsp_saturated,output wire busy
);
 localparam IDLE=0,ISSUE=1,WAIT_BANK=2,DRAIN=3,READ_SHIFT=4,READ_ROUND=5,READ_CLAMP=6;
 reg [2:0] state;
 reg signed [15:0] aa[0:511],bb[0:511];reg [63:0] av,af;
 reg [1:0] bv[0:7];reg [7:0] bf;
 // New mode reuses the existing eight result rows as eight N8 contexts.
 // No new operand, partial, preview, or S64 result payload arrays are added.
 localparam [1:0] CTX_FREE=0,CTX_ACTIVE=1,CTX_COMPLETE=2;
 reg [1:0] context_state[0:7],context_format[0:7];
 reg [15:0] context_next_k[0:7],context_tag[0:7];
 wire [7:0] context_live;
 for(genvar c=0;c<8;c=c+1)begin: context_liveness
  assign context_live[c]=context_state[c]!=CTX_FREE;
 end
 reg context_execution,context_final;
 reg [2:0] context_source_row;
 reg [15:0] context_end_k,context_group_tag;
 wire [2:0] operand_row=context_execution?context_source_row:issue_row;
 initial begin
  if(CONTEXTS!=1&&CONTEXTS!=2&&CONTEXTS!=8)$fatal(1,"CONTEXTS must be 1, 2, or 8");
  if(A_WORDS_PER_BEAT!=1&&A_WORDS_PER_BEAT!=2)$fatal(1,"A_WORDS_PER_BEAT must be 1 or 2");
 end
 reg execution_bank,fmt_a,fmt_b,clear_result;
 reg [3:0] rows,tiles,last_k,active_n;
 reg [2:0] issue_row;reg issue_bank;
 reg [1:0] issue_tile,issue_a,issue_b;
 reg [1:0] bank_busy,bank_done,bank_fault,partial_valid;
 reg [2:0] bank_owner[0:1];
 reg signed [39:0] partial[0:15];
 reg signed [63:0] merged[0:63],preview[0:7];
 reg [7:0] merged_valid;reg [3:0] result_n[0:7];
 reg [7:0] fault_rows;reg [3:0] committed;
 reg signed [15:0] scale_factor;reg [4:0] scale_shift;

 function automatic signed [7:0] digit;
  input signed [15:0] v;input wide;input [1:0] part;
  begin if(!wide)digit=v[7:0];else case(part)
   0:digit={1'b0,v[6:0]};1:digit={1'b0,v[13:7]};default:digit={{6{v[15]}},v[15:14]};
  endcase end
 endfunction
 wire clear_banks=cmd_valid&&cmd_ready&&cmd_op==6;
 wire clear_bank=cmd_valid&&cmd_ready&&cmd_op==11;
 wire start=cmd_valid&&cmd_ready&&(cmd_op==10||cmd_op==13);
 wire locked=state==ISSUE||state==WAIT_BANK||state==DRAIN;
 // One atomic handshake accepts a prefix of lanes sharing bank and format.
 // A sparse mask or duplicate {row,tile} rejects the whole beat until corrected.
 wire a_shape_ok;
 generate if(A_WORDS_PER_BEAT==2)begin: dual_a_shape
  assign a_shape_ok=!a_valid[1]||(a_valid[0]&&{a_row[5:3],a_tile[3:2]}!={a_row[2:0],a_tile[1:0]});
 end else begin: single_a_shape
  assign a_shape_ok=1'b1;
 end endgenerate
 assign cmd_ready=!reset&&state==IDLE&&(!rsp_valid||rsp_ready);
 assign busy=!cmd_ready;
 assign a_ready=a_shape_ok&&!reset&&!clear_banks&&!(clear_bank&&cmd_index[0]==a_bank)&&!(locked&&execution_bank==a_bank)&&!(start&&cmd_index[5]==a_bank);
 assign b_ready=!reset&&!clear_banks&&!(clear_bank&&cmd_index[0]==b_bank)&&!(locked&&execution_bank==b_bank)&&!(start&&cmd_index[5]==b_bank)&&
  ((!b_wide&&!b_half)||(b_wide&&(!b_half||(bv[{b_bank,b_tile}][0]&&bf[{b_bank,b_tile}]))));

 reg descriptor_ok;reg [5:0] ai;reg [2:0] bi;
 always @* begin
  descriptor_ok=cmd_index[4:0]==0&&cmd_data[63:19]==0&&!cmd_data[3]&&
   cmd_data[7:4]>=1&&cmd_data[7:4]<=8&&cmd_data[11:8]>=1&&cmd_data[11:8]<=8&&
   cmd_data[14:12]>=1&&cmd_data[14:12]<=4&&cmd_data[18:15]>=1&&cmd_data[18:15]<=8;
  ai=0;bi=0;
  for(integer t=0;t<4;t=t+1)if(t<cmd_data[14:12])begin
   bi={cmd_index[5],t[1:0]};if(bv[bi]!=3||bf[bi]!=cmd_data[1])descriptor_ok=0;
   for(integer r=0;r<8;r=r+1)if(r<cmd_data[18:15])begin
    ai={cmd_index[5],r[2:0],t[1:0]};if(!av[ai]||af[ai]!=cmd_data[0])descriptor_ok=0;
   end
  end
  if(!cmd_data[2])for(integer r=0;r<8;r=r+1)if(r<cmd_data[18:15])
   if(!merged_valid[r]||result_n[r]!=cmd_data[11:8])descriptor_ok=0;
 end

 // op13: index={operand_bank,2'b0,destination_context}.
 // data: Awide[0],Bwide[1],first[2],final[3],lastK[7:4],N[11:8],
 // tiles[14:12],sourceArow[17:15],Koffset[33:18],group_tag[49:34].
 // A/B payload and bank locks are exactly those of the original native M.
 reg context_descriptor_ok;
 reg [16:0] context_end;
 always @* begin
  context_end={1'b0,cmd_data[33:18]}+
   (({14'd0,cmd_data[14:12]}-17'd1)<<3)+{13'd0,cmd_data[7:4]};
  context_descriptor_ok=cmd_index[4:3]==0&&32'(cmd_index[2:0])<CONTEXTS&&
   cmd_data[63:50]==0&&cmd_data[7:4]>=1&&cmd_data[7:4]<=8&&
   cmd_data[11:8]>=1&&cmd_data[11:8]<=8&&cmd_data[14:12]>=1&&cmd_data[14:12]<=4&&
   !context_end[16];
  for(integer t=0;t<4;t=t+1)if(t<cmd_data[14:12])begin
   if(bv[{cmd_index[5],t[1:0]}]!=3||bf[{cmd_index[5],t[1:0]}]!=cmd_data[1])context_descriptor_ok=0;
   if(!av[{cmd_index[5],cmd_data[17:15],t[1:0]}]||
      af[{cmd_index[5],cmd_data[17:15],t[1:0]}]!=cmd_data[0])context_descriptor_ok=0;
  end
  if(cmd_data[2])begin
   if(context_state[cmd_index[2:0]]!=CTX_FREE||cmd_data[33:18]!=0)context_descriptor_ok=0;
  end else begin
   if(context_state[cmd_index[2:0]]!=CTX_ACTIVE||
      context_next_k[cmd_index[2:0]]!=cmd_data[33:18]||context_tag[cmd_index[2:0]]!=cmd_data[49:34]||
      context_format[cmd_index[2:0]]!=cmd_data[1:0]||
      !merged_valid[cmd_index[2:0]]||result_n[cmd_index[2:0]]!=cmd_data[11:8])context_descriptor_ok=0;
  end
 end

 reg signed [7:0] lhs[0:63],rhs[0:63];reg signed [15:0] product[0:63];
 reg signed [18:0] sums[0:7],reduced[0:7];
 reg product_valid,reduce_valid,product_bank,reduce_bank,product_last,reduce_last;
 reg [5:0] product_shift,reduce_shift;
 wire last_issue={2'd0,issue_tile}+4'd1==tiles&&issue_a==(fmt_a?2:0)&&issue_b==(fmt_b?2:0);
 reg [40:0] next_partial[0:7];reg [7:0] partial_overflow;
 always @* begin
  for(integer n=0;n<8;n=n+1)begin
   for(integer k=0;k<8;k=k+1)begin
    lhs[8*n+k]=0;rhs[8*n+k]=0;
    if(state==ISSUE&&n<active_n&&({2'd0,issue_tile}+4'd1<tiles||k<last_k))begin
     lhs[8*n+k]=digit(aa[32'(execution_bank)*256+32'(operand_row)*32+32'(issue_tile)*8+k],fmt_a,issue_a);
     rhs[8*n+k]=digit(bb[(32'(execution_bank)*4+32'(issue_tile))*64+8*n+k],fmt_b,issue_b);
    end
   end
   sums[n]=
    (($signed({{3{product[8*n][15]}},product[8*n]})+$signed({{3{product[8*n+1][15]}},product[8*n+1]}))+
     ($signed({{3{product[8*n+2][15]}},product[8*n+2]})+$signed({{3{product[8*n+3][15]}},product[8*n+3]})))+
    (($signed({{3{product[8*n+4][15]}},product[8*n+4]})+$signed({{3{product[8*n+5][15]}},product[8*n+5]}))+
     ($signed({{3{product[8*n+6][15]}},product[8*n+6]})+$signed({{3{product[8*n+7][15]}},product[8*n+7]})));
   next_partial[n]=$signed({partial[32'(reduce_bank)*8+n][39],partial[32'(reduce_bank)*8+n]})+
    ($signed({{22{reduced[n][18]}},reduced[n]})<<<reduce_shift);
   partial_overflow[n]=next_partial[n][40]!=next_partial[n][39];
  end
 end

 reg scale_bank;reg [1:0] scale_pair;
 wire fetch_scale=locked&&bank_done[scale_bank];
 reg fv,mv,av_scale,sv;
 reg [2:0] frow,mrow,arow,srow;reg [1:0] fpair,mpair,apair,spair;
 reg ferr,merr,aerr,serr,row_error;
 reg signed [39:0] fp[0:1];reg signed [55:0] mp[0:1];
 reg signed [63:0] fold[0:1],mold[0:1],aold[0:1],anew[0:1],snew[0:1];
 wire signed [87:0] aligned[0:1];wire [1:0] alignment_fault,addition_fault;
 wire signed [64:0] addition[0:1];
 for(genvar l=0;l<2;l=l+1)begin: scale_lane
  assign aligned[l]=$signed({{32{mp[l][55]}},mp[l]})<<<scale_shift;
  assign alignment_fault[l]=aligned[l][87:63]!={25{aligned[l][63]}};
  assign addition[l]=$signed({aold[l][63],aold[l]})+$signed({anew[l][63],anew[l]});
  assign addition_fault[l]=addition[l][64]!=addition[l][63];
 end
 reg [2:0] read_row;reg read_half;reg [5:0] read_shift;reg [1:0] read_width;
 reg signed [63:0] read_q[0:3],read_r[0:3];reg [3:0] read_increment;
 reg [127:0] formatted;reg clipped;reg signed [63:0] value,lo,hi;
 function automatic increment;
  input signed [63:0] v;input [5:0] shift;
  reg [63:0] mask,remn,half;
  begin
   mask=(64'd1<<shift)-1;remn=$unsigned(v)&mask;half=64'd1<<(shift-1);
   increment=shift!=0&&(remn>half||(remn==half&&v[shift]));
  end
 endfunction
 always @* begin
  formatted=0;clipped=0;value=0;
  case(read_width)0:begin lo=-128;hi=127;end 1:begin lo=-32768;hi=32767;end default:begin lo=-64'sd2147483648;hi=2147483647;end endcase
  for(integer l=0;l<4;l=l+1)begin
   value=read_r[l];if(value<lo)begin value=lo;clipped=1;end else if(value>hi)begin value=hi;clipped=1;end
   formatted[32*l+:32]=value[31:0];
  end
 end
 task automatic respond;
  input [127:0] data;input error,saturation;
  begin rsp_valid<=1;rsp_data<=data;rsp_error<=error;rsp_saturated<=saturation;state<=IDLE;end
 endtask
 integer i;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;rsp_valid<=0;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
   av<=0;af<=0;bf<=0;merged_valid<=0;bank_busy<=0;bank_done<=0;bank_fault<=0;partial_valid<=0;
   product_valid<=0;reduce_valid<=0;fv<=0;mv<=0;av_scale<=0;sv<=0;
   scale_factor<=1;scale_shift<=0;scale_bank<=0;scale_pair<=0;committed<=0;fault_rows<=0;row_error<=0;
   context_execution<=0;context_final<=0;context_source_row<=0;context_end_k<=0;context_group_tag<=0;
   for(i=0;i<8;i=i+1)begin
    bv[i]<=0;result_n[i]<=0;context_state[i]<=CTX_FREE;context_format[i]<=0;context_next_k[i]<=0;context_tag[i]<=0;
   end
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if((|a_valid)&&a_ready)begin
    for(integer a_lane=0;a_lane<A_WORDS_PER_BEAT;a_lane=a_lane+1)if(a_valid[a_lane])begin
     av[{a_bank,a_row[3*a_lane+:3],a_tile[2*a_lane+:2]}]<=1;
     af[{a_bank,a_row[3*a_lane+:3],a_tile[2*a_lane+:2]}]<=a_wide;
     for(i=0;i<8;i=i+1)aa[32'({a_bank,a_row[3*a_lane+:3],a_tile[2*a_lane+:2]})*8+i]<=
      a_wide?$signed(a_data[128*a_lane+16*i+:16]):$signed({{8{a_data[128*a_lane+8*i+7]}},a_data[128*a_lane+8*i+:8]});
    end
   end
   if(b_valid&&b_ready)begin
    bf[{b_bank,b_tile}]<=b_wide;
    if(!b_wide)begin bv[{b_bank,b_tile}]<=3;for(i=0;i<64;i=i+1)bb[32'({b_bank,b_tile})*64+i]<=$signed({{8{b_data[8*i+7]}},b_data[8*i+:8]});end
    else begin bv[{b_bank,b_tile}]<=b_half?3:1;for(i=0;i<32;i=i+1)bb[32'({b_bank,b_tile})*64+32'(b_half)*32+i]<=$signed(b_data[16*i+:16]);end
   end
   product_valid<=state==ISSUE;reduce_valid<=product_valid;
   if(state==ISSUE)begin
    for(i=0;i<64;i=i+1)product[i]<=lhs[i]*rhs[i];
    product_bank<=issue_bank;product_shift<=7*({4'd0,issue_a}+{4'd0,issue_b});product_last<=last_issue;
   end
   if(product_valid)begin
    for(i=0;i<8;i=i+1)reduced[i]<=sums[i];
    reduce_bank<=product_bank;reduce_shift<=product_shift;reduce_last<=product_last;
   end
   if(reduce_valid)begin
    for(i=0;i<8;i=i+1)partial[32'(reduce_bank)*8+i]<=next_partial[i][39:0];
    bank_fault[reduce_bank]<=bank_fault[reduce_bank]||(|partial_overflow);
    if(reduce_last)begin bank_done[reduce_bank]<=1;partial_valid[reduce_bank]<=1;end
   end
   // Complete pairs stream through fetch/multiply/align/add/commit stages.
   fv<=fetch_scale;mv<=fv;av_scale<=mv;sv<=av_scale;
   if(fetch_scale)begin
    frow<=bank_owner[scale_bank];fpair<=scale_pair;ferr<=bank_fault[scale_bank];
    for(i=0;i<2;i=i+1)begin
     fp[i]<=partial[32'(scale_bank)*8+32'(scale_pair)*2+i];
     fold[i]<=clear_result?64'sd0:merged[32'(bank_owner[scale_bank])*8+32'(scale_pair)*2+i];
    end
    if(scale_pair==3)begin bank_done[scale_bank]<=0;bank_busy[scale_bank]<=0;scale_bank<=!scale_bank;scale_pair<=0;end
    else scale_pair<=scale_pair+1'b1;
   end
   if(fv)begin
    mrow<=frow;mpair<=fpair;merr<=ferr;
    for(i=0;i<2;i=i+1)begin mp[i]<=fp[i]*scale_factor;mold[i]<=fold[i];end
   end
   if(mv)begin
    arow<=mrow;apair<=mpair;aerr<=merr||(|alignment_fault);
    for(i=0;i<2;i=i+1)begin anew[i]<=aligned[i][63:0];aold[i]<=mold[i];end
   end
   if(av_scale)begin
    srow<=arow;spair<=apair;serr<=aerr||(|addition_fault);
    for(i=0;i<2;i=i+1)snew[i]<=addition[i][63:0];
   end
   if(sv)begin
    for(i=0;i<2;i=i+1)preview[32'(spair)*2+i]<=snew[i];
    row_error<=spair==0?serr:row_error||serr;
    if(spair==3)begin
     committed<=committed+1'b1;
     if(row_error||serr)fault_rows[srow]<=1;
     else begin
      for(i=0;i<6;i=i+1)merged[32'(srow)*8+i]<=preview[i];
      merged[32'(srow)*8+6]<=snew[0];merged[32'(srow)*8+7]<=snew[1];merged_valid[srow]<=1;result_n[srow]<=active_n;
      // Advance metadata only on the original atomic S64 row commit.
      // Overflow leaves the entire previous payload and lifecycle unchanged.
      if(context_execution)begin
       context_state[srow]<=context_final?CTX_COMPLETE:CTX_ACTIVE;
       context_next_k[srow]<=context_end_k;context_tag[srow]<=context_group_tag;
       context_format[srow]<={fmt_b,fmt_a};
      end
     end
    end
   end
   case(state)
    IDLE:if(cmd_valid&&cmd_ready)case(cmd_op)
     3:if(context_state[cmd_index[5:3]]!=CTX_ACTIVE&&merged_valid[cmd_index[5:3]]&&cmd_index[2:0]<4&&cmd_data==0)
      respond({merged[32'(cmd_index[5:3])*8+2*32'(cmd_index[1:0])+1],merged[32'(cmd_index[5:3])*8+2*32'(cmd_index[1:0])]},0,0);else respond(0,1,0);
     4:if(cmd_index!=0||cmd_data[63:21]!=0)respond(0,1,0);
      else begin scale_factor<=cmd_data[15:0];scale_shift<=cmd_data[20:16];respond(0,0,0);end
     5:if(context_state[cmd_index[5:3]]!=CTX_ACTIVE&&merged_valid[cmd_index[5:3]]&&cmd_index[2:0]<2&&cmd_data[63:10]==0&&cmd_data[9:8]<3&&cmd_data[7:6]==0)begin
      read_row<=cmd_index[5:3];read_half<=cmd_index[0];read_shift<=cmd_data[5:0];read_width<=cmd_data[9:8];state<=READ_SHIFT;
     end else respond(0,1,0);
     6:if(cmd_index!=0||cmd_data!=0)respond(0,1,0);else begin
      av<=0;for(i=0;i<8;i=i+1)begin bv[i]<=0;context_state[i]<=CTX_FREE;end merged_valid<=0;partial_valid<=0;respond(0,0,0);
     end
     10:if((|context_live)||!descriptor_ok)respond(0,1,0);else begin
      context_execution<=0;
      execution_bank<=cmd_index[5];fmt_a<=cmd_data[0];fmt_b<=cmd_data[1];clear_result<=cmd_data[2];
      last_k<=cmd_data[7:4];active_n<=cmd_data[11:8];tiles<={1'b0,cmd_data[14:12]};rows<=cmd_data[18:15];
      issue_row<=0;issue_bank<=0;issue_tile<=0;issue_a<=0;issue_b<=0;
      bank_busy<=1;bank_done<=0;bank_fault<=0;partial_valid<=0;bank_owner[0]<=0;
      for(i=0;i<8;i=i+1)partial[i]<=0;
      scale_bank<=0;scale_pair<=0;committed<=0;fault_rows<=0;row_error<=0;state<=ISSUE;
     end
     13:if(!context_descriptor_ok)respond(0,1,0);else begin
      context_execution<=1;context_source_row<=cmd_data[17:15];context_final<=cmd_data[3];
      context_end_k<=context_end[15:0];context_group_tag<=cmd_data[49:34];
      execution_bank<=cmd_index[5];fmt_a<=cmd_data[0];fmt_b<=cmd_data[1];clear_result<=cmd_data[2];
      last_k<=cmd_data[7:4];active_n<=cmd_data[11:8];tiles<={1'b0,cmd_data[14:12]};rows<=1;
      issue_row<=0;issue_bank<=0;issue_tile<=0;issue_a<=0;issue_b<=0;
      bank_busy<=1;bank_done<=0;bank_fault<=0;partial_valid<=0;bank_owner[0]<=cmd_index[2:0];
      for(i=0;i<8;i=i+1)partial[i]<=0;
      scale_bank<=0;scale_pair<=0;committed<=0;fault_rows<=0;row_error<=0;state<=ISSUE;
     end
     // op14 explicitly releases a completed context or aborts a live one.
     // A matching tag is mandatory even on abort; no outstanding execute can exist in IDLE.
     14:if(cmd_index[5:3]!=0||32'(cmd_index[2:0])>=CONTEXTS||cmd_data[63:17]!=0||
       context_state[cmd_index[2:0]]==CTX_FREE||context_tag[cmd_index[2:0]]!=cmd_data[16:1]||
       (!cmd_data[0]&&context_state[cmd_index[2:0]]!=CTX_COMPLETE))respond(0,1,0);
      else begin context_state[cmd_index[2:0]]<=CTX_FREE;merged_valid[cmd_index[2:0]]<=0;respond(0,0,0);end
     11:if(cmd_index[5:1]!=0||cmd_data!=0)respond(0,1,0);else begin
      for(i=0;i<32;i=i+1)av[32'(cmd_index[0])*32+i]<=0;
      for(i=0;i<4;i=i+1)bv[32'(cmd_index[0])*4+i]<=0;respond(0,0,0);
     end
     12:if(cmd_data==0&&cmd_index[2:0]<4&&partial_valid[cmd_index[3]]&&bank_owner[cmd_index[3]]==cmd_index[5:3])
      respond({{24{partial[32'(cmd_index[3])*8+2*32'(cmd_index[1:0])+1][39]}},partial[32'(cmd_index[3])*8+2*32'(cmd_index[1:0])+1],
               {24{partial[32'(cmd_index[3])*8+2*32'(cmd_index[1:0])][39]}},partial[32'(cmd_index[3])*8+2*32'(cmd_index[1:0])]},0,0);
      else respond(0,1,0);
     default:respond(0,1,0);
    endcase
    ISSUE:begin
     if(last_issue)begin
      issue_tile<=0;issue_a<=0;issue_b<=0;
      if({1'b0,issue_row}+4'd1==rows)state<=DRAIN;
      else begin issue_row<=issue_row+1'b1;issue_bank<=!issue_bank;state<=WAIT_BANK;end
     end else if(issue_b==(fmt_b?2:0))begin
      issue_b<=0;if(issue_a==(fmt_a?2:0))begin issue_a<=0;issue_tile<=issue_tile+1'b1;end else issue_a<=issue_a+1'b1;
     end else issue_b<=issue_b+1'b1;
    end
    WAIT_BANK:if(!bank_busy[issue_bank])begin
     bank_busy[issue_bank]<=1;bank_fault[issue_bank]<=0;partial_valid[issue_bank]<=0;bank_owner[issue_bank]<=issue_row;
     for(i=0;i<8;i=i+1)partial[32'(issue_bank)*8+i]<=0;state<=ISSUE;
    end
    DRAIN:if(committed==rows)respond({120'd0,fault_rows},|fault_rows,0);
    READ_SHIFT:begin
     for(i=0;i<4;i=i+1)begin
      read_q[i]<=merged[32'(read_row)*8+4*32'(read_half)+i]>>>read_shift;
      read_increment[i]<=increment(merged[32'(read_row)*8+4*32'(read_half)+i],read_shift);
     end
     state<=READ_ROUND;
    end
    READ_ROUND:begin for(i=0;i<4;i=i+1)read_r[i]<=read_q[i]+$signed({63'd0,read_increment[i]});state<=READ_CLAMP;end
    READ_CLAMP:respond(formatted,0,clipped);
    default:respond(0,1,0);
   endcase
  end
 end
endmodule
