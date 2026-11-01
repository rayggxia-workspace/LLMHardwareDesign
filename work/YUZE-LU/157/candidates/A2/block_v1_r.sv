// Finite eight-lane recurrent engine. S32 state; Q1.14 Q/K/B/C;
// unsigned Q1.31 decay/beta (0x80000000 = 1); S32 Q16.16 skip.
// Each operation is staged into shadow storage and explicitly committed.
module block_v1_r(
 input wire clk,reset,cmd_valid,output wire cmd_ready,
 input wire [3:0] cmd_op,input wire [9:0] cmd_index,input wire [127:0] cmd_data,
 output reg rsp_valid,input wire rsp_ready,output reg [127:0] rsp_data,
 output reg rsp_error,output wire busy
);
 localparam IDLE=0,DEC_MUL=1,DEC_WRITE=2,PRED_MUL=3,PRED_ADD=4,
 PRED_END=5,ERR_PREP=6,ERR_MUL=7,ERR_WRITE=8,UP_MUL=9,UP_WRITE=10,
 READ_MUL=11,READ_ADD=12,READ_END=13,SKIP_MUL=14,SKIP_WRITE=15,
 CONV_MUL=16,CONV_ADD=17,CONV_END=18,FINISH=19,COPY=20,
 ERR_FETCH=21,SKIP_FETCH=22,CONV_FETCH=23;
 reg [4:0] phase;
 reg signed [31:0] bank0[0:2047],bank1[0:2047];
 reg bank_role;
 wire [8:0] state_read_row=phase==IDLE?cmd_index[9:1]:row;
 wire signed [31:0] active_row[0:7],shadow_row[0:7];
 genvar read_lane;
 generate for(read_lane=0;read_lane<8;read_lane=read_lane+1)begin: state_read
  wire signed [31:0] group_active[0:31],group_shadow[0:31];
  for(genvar group_id=0;group_id<32;group_id=group_id+1)begin: group_read
   wire signed [31:0] first=bank0[group_id*64+state_read_row[2:0]*8+read_lane];
   wire signed [31:0] second=bank1[group_id*64+state_read_row[2:0]*8+read_lane];
   assign group_active[group_id]=bank_role?second:first;
   assign group_shadow[group_id]=bank_role?first:second;
  end
  assign active_row[read_lane]=group_active[state_read_row[8:3]];
  assign shadow_row[read_lane]=group_shadow[state_read_row[8:3]];
 end endgenerate
 reg row_valid;reg [8:0] product_row;
 reg signed [15:0] key[0:255],query[0:255];
 reg signed [31:0] x[0:7],inject[0:7],skip[0:7],error_value[0:7],output_value[0:7];
 reg signed [31:0] history[0:23],history_next[0:23];
 reg signed [15:0] taps[0:31];
 // <=256 products of S32 by S16 need at most55 signed bits.
 reg signed [63:0] dot[0:7];
 reg signed [31:0] mul_a[0:7];reg signed [32:0] mul_b[0:7];
 // Isolate dynamic state/history selection from the shared multipliers.
 // Row loops still accept one operand row per cycle; only fill/drain grows.
 reg signed [31:0] operand_a[0:7];reg signed [32:0] operand_b[0:7];
 reg operand_valid,fetch_done;reg [8:0] operand_row;
 // Carry the old S32 state with its operand/product instead of selecting it
 // through product_row in the update-add/overflow retirement path.
 reg signed [31:0] operand_state_base[0:7],product_state_base[0:7];
 reg signed [64:0] product[0:7];
 reg [511:0] active_valid,decay_valid;
 reg [31:0] key_valid,query_valid;
 reg [3:0] x_valid,tap_valid;reg [1:0] skip_valid;reg [5:0] history_valid;
 reg context_valid,param_valid,failed,output_valid,pending_state,pending_history;
 reg [31:0] owner,epoch,position,decay,beta,next_position;
 reg [8:0] length,row;reg [1:0] mode,tap;
 assign cmd_ready=!reset&&phase==IDLE&&(!rsp_valid||rsp_ready);
 assign busy=!cmd_ready;
 function automatic signed [127:0] rne;
  input signed [127:0] v;input [6:0] sh;
  reg signed [127:0] q;reg [127:0] remn,half;
  begin
   if(sh==0)rne=v;
   else begin q=v>>>sh;remn=$unsigned(v)&({128{1'b1}}>>(128-sh));
    half=128'd1<<(sh-1);rne=q+((remn>half)||((remn==half)&&q[0]));end
  end
 endfunction
 function automatic fits32;
  input signed [127:0] v;
  begin fits32=v[127:31]=={97{v[31]}};end
 endfunction
 reg loaded,coefficient_loaded,factor_loaded;
 reg signed [127:0] value[0:7];reg value_error;
 always @* begin
  loaded=1;coefficient_loaded=1;factor_loaded=1;
  for(integer n=0;n<256;n=n+1)if(n<length)begin
   if(!active_valid[2*n]||!active_valid[2*n+1])loaded=0;
   if(!key_valid[n/8]||!query_valid[n/8])coefficient_loaded=0;
   if(!decay_valid[2*n]||!decay_valid[2*n+1])factor_loaded=0;
  end
  value_error=0;
  for(integer l=0;l<8;l=l+1)begin
   mul_a[l]=0;mul_b[l]=0;value[l]=0;
   case(phase)
    DEC_MUL:begin mul_a[l]=active_row[l];mul_b[l]=mode==0?$signed({1'b0,decay}):$signed({1'b0,shadow_row[l]});end
    PRED_MUL:begin mul_a[l]=shadow_row[l];mul_b[l]={{17{key[row][15]}},key[row]};end
    ERR_FETCH:begin mul_a[l]=error_value[l];mul_b[l]=$signed({1'b0,beta});end
    UP_MUL:begin mul_a[l]=mode==0?error_value[l]:inject[l];mul_b[l]={{17{key[row][15]}},key[row]};end
    READ_MUL:begin mul_a[l]=shadow_row[l];mul_b[l]={{17{query[row][15]}},query[row]};end
    SKIP_FETCH:begin mul_a[l]=x[l];mul_b[l]={skip[l][31],skip[l]};end
    CONV_FETCH:begin mul_a[l]=tap==0?x[l]:history[(tap-1)*8+l];mul_b[l]={{17{taps[tap*8+l][15]}},taps[tap*8+l]};end
    default:begin end
   endcase
   case(phase)
    DEC_MUL,DEC_WRITE,ERR_WRITE:value[l]=rne({{63{product[l][64]}},product[l]},31);
    PRED_END,READ_END,CONV_END:value[l]=rne(dot[l],14);
    ERR_PREP:value[l]=$signed({{96{x[l][31]}},x[l]})-$signed({{96{error_value[l][31]}},error_value[l]});
    UP_MUL,UP_WRITE:value[l]=$signed({{96{product_state_base[l][31]}},product_state_base[l]})+rne({{63{product[l][64]}},product[l]},14);
    SKIP_WRITE:value[l]=$signed({{96{output_value[l][31]}},output_value[l]})+rne({{63{product[l][64]}},product[l]},16);
    default:value[l]=0;
   endcase
   if(!fits32(value[l]))value_error=1;
  end
 end
 integer i;
 always @(posedge clk)begin
  if(reset)begin
   phase<=IDLE;rsp_valid<=0;rsp_data<=0;rsp_error<=0;context_valid<=0;
   active_valid<=0;decay_valid<=0;key_valid<=0;query_valid<=0;x_valid<=0;
   tap_valid<=0;history_valid<=0;skip_valid<=0;param_valid<=0;
   output_valid<=0;pending_state<=0;pending_history<=0;failed<=0;
   owner<=0;epoch<=0;position<=0;length<=0;row<=0;mode<=0;tap<=0;
   bank_role<=0;row_valid<=0;product_row<=0;
   operand_valid<=0;fetch_done<=0;operand_row<=0;
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    rsp_valid<=1;rsp_data<=0;rsp_error<=0;
    case(cmd_op)
     0:begin // OPEN: length[8:0], owner[40:9], epoch[72:41], position[104:73]
      if(cmd_data[8:0]==0||cmd_data[8:0]>256||cmd_data[127:105]!=0||pending_state||pending_history)rsp_error<=1;
      else begin length<=cmd_data[8:0];owner<=cmd_data[40:9];epoch<=cmd_data[72:41];position<=cmd_data[104:73];context_valid<=1;
       active_valid<=0;decay_valid<=0;key_valid<=0;query_valid<=0;x_valid<=0;tap_valid<=0;history_valid<=0;skip_valid<=0;param_valid<=0;output_valid<=0;end
     end
     1,15:begin // State halves / SSM decay halves. Shadow is reused, no hidden factor RAM.
      if(!context_valid||cmd_index>=2*length||pending_state||pending_history||
         (cmd_op==15&&(cmd_data[31:0]>32'h80000000||cmd_data[63:32]>32'h80000000||cmd_data[95:64]>32'h80000000||cmd_data[127:96]>32'h80000000)))rsp_error<=1;
      else begin
       for(integer write_group=0;write_group<32;write_group=write_group+1)if(cmd_index[9:4]==write_group)begin
        for(i=0;i<4;i=i+1)if((cmd_op==1)^bank_role)bank0[write_group*64+cmd_index[3:0]*4+i]<=cmd_data[32*i+:32];else bank1[write_group*64+cmd_index[3:0]*4+i]<=cmd_data[32*i+:32];
       end
       if(cmd_op==1)active_valid[cmd_index]<=1;else decay_valid[cmd_index]<=1;
      end
     end
     2,3:begin
      if(!context_valid||cmd_index>31||pending_state)rsp_error<=1;
      else begin for(i=0;i<8;i=i+1)if(cmd_op==2)key[cmd_index*8+i]<=cmd_data[16*i+:16];else query[cmd_index*8+i]<=cmd_data[16*i+:16];
       if(cmd_op==2)key_valid[cmd_index]<=1;else query_valid[cmd_index]<=1;end
     end
     4:begin
      if(!context_valid||cmd_index>3||pending_state)rsp_error<=1;
      else begin for(i=0;i<4;i=i+1)if(cmd_index<2)x[cmd_index*4+i]<=cmd_data[32*i+:32];else inject[(cmd_index-2)*4+i]<=cmd_data[32*i+:32];x_valid[cmd_index]<=1;end
     end
     5:begin
      if(!context_valid||pending_state||cmd_index>2)rsp_error<=1;
      else if(cmd_index==0)begin
       if(cmd_data[127:64]!=0||cmd_data[31:0]>32'h80000000||cmd_data[63:32]>32'h80000000)rsp_error<=1;
       else begin decay<=cmd_data[31:0];beta<=cmd_data[63:32];param_valid<=1;end
      end else begin for(i=0;i<4;i=i+1)skip[(cmd_index-1)*4+i]<=cmd_data[32*i+:32];skip_valid[cmd_index-1]<=1;end
     end
     6:begin // EXEC 0 GDN, 1 SSM, 2 conv; exact command owner/epoch/position.
      if(!context_valid||pending_state||cmd_data[127:98]!=0||cmd_data[33:2]!=owner||cmd_data[65:34]!=epoch||cmd_data[97:66]!=position||cmd_data[1:0]>2||
       (cmd_data[1:0]==2&&(pending_history||x_valid[1:0]!=3||tap_valid!=15||history_valid!=63))||
       (cmd_data[1:0]<2&&(!loaded||!coefficient_loaded||!param_valid||x_valid[1:0]!=3))||
       (cmd_data[1:0]==1&&(!factor_loaded||x_valid!=15||skip_valid!=3)))rsp_error<=1;
      else begin
       mode<=cmd_data[1:0];row<=0;row_valid<=0;tap<=0;failed<=0;output_valid<=0;rsp_valid<=0;
       operand_valid<=0;fetch_done<=0;
       for(i=0;i<8;i=i+1)dot[i]<=0;
       if(cmd_data[1:0]==2)begin
        phase<=CONV_FETCH;
        for(i=0;i<8;i=i+1)begin history_next[i]<=x[i];history_next[8+i]<=history[i];history_next[16+i]<=history[8+i];end
       end else begin phase<=DEC_MUL;decay_valid<=0;end
      end
     end
     7:begin // COMMIT: owner, expected epoch, expected position, caller next position.
      if(!context_valid||(!pending_state&&!pending_history)||cmd_data[31:0]!=owner||cmd_data[63:32]!=epoch||cmd_data[95:64]!=position||epoch==32'hffffffff)rsp_error<=1;
      else begin
       next_position<=cmd_data[127:96];row<=0;rsp_valid<=0;phase<=COPY;
      end
     end
     8:begin pending_state<=0;pending_history<=0;output_valid<=0;decay_valid<=0;end
     9:begin
      if(!context_valid||cmd_index>5||pending_history||pending_state)rsp_error<=1;
      else begin for(i=0;i<4;i=i+1)history[cmd_index*4+i]<=cmd_data[32*i+:32];history_valid[cmd_index]<=1;end
     end
     10:begin
      if(!context_valid||cmd_index>3||pending_history||pending_state)rsp_error<=1;
      else begin for(i=0;i<8;i=i+1)taps[cmd_index*8+i]<=cmd_data[16*i+:16];tap_valid[cmd_index]<=1;end
     end
     11:begin
      if(!context_valid||cmd_index>=2*length||!active_valid[cmd_index])rsp_error<=1;
      else for(i=0;i<4;i=i+1)rsp_data[32*i+:32]<=active_row[cmd_index[0]*4+i];
     end
     12:begin
      if(!output_valid||cmd_index>1)rsp_error<=1;
      else for(i=0;i<4;i=i+1)rsp_data[32*i+:32]<=output_value[cmd_index*4+i];
     end
     13:rsp_data<={position,epoch,owner,20'b0,output_valid,pending_history,pending_state,length};
     14:begin
      if(!context_valid||cmd_index>5||history_valid[cmd_index]!=1)rsp_error<=1;
      else for(i=0;i<4;i=i+1)rsp_data[32*i+:32]<=history[cmd_index*4+i];
     end
     default:rsp_error<=1;
    endcase
   end else case(phase)
    DEC_MUL,UP_MUL,PRED_MUL,READ_MUL:begin
     // Fetch row n, multiply buffered row n-1, retire product n-2.
     // SSM factors are captured before that same shadow row is overwritten.
     if(!fetch_done)begin
      for(i=0;i<8;i=i+1)begin
       operand_a[i]<=mul_a[i];operand_b[i]<=mul_b[i];
       if(phase==UP_MUL)operand_state_base[i]<=shadow_row[i];
      end
      operand_row<=row;operand_valid<=1;
      if(row+1==length)fetch_done<=1;else row<=row+1;
     end else operand_valid<=0;
     if(operand_valid)begin
      for(i=0;i<8;i=i+1)begin
       product[i]<=operand_a[i]*operand_b[i];
       if(phase==UP_MUL)product_state_base[i]<=operand_state_base[i];
      end
      product_row<=operand_row;
     end
     row_valid<=operand_valid;
     if(row_valid)begin
      if(phase==DEC_MUL||phase==UP_MUL)begin
       failed<=failed||value_error;
       for(integer write_group=0;write_group<32;write_group=write_group+1)if(product_row[8:3]==write_group)begin
        for(i=0;i<8;i=i+1)if(bank_role)bank0[write_group*64+product_row[2:0]*8+i]<=value[i][31:0];else bank1[write_group*64+product_row[2:0]*8+i]<=value[i][31:0];
       end
      end else for(i=0;i<8;i=i+1)dot[i]<=dot[i]+$signed(product[i]);
     end
     if(operand_valid&&operand_row+1==length)
      phase<=phase==DEC_MUL?DEC_WRITE:phase==UP_MUL?UP_WRITE:phase==PRED_MUL?PRED_ADD:READ_ADD;
    end
    DEC_WRITE,UP_WRITE:begin
     failed<=failed||value_error;
     for(integer write_group=0;write_group<32;write_group=write_group+1)if(product_row[8:3]==write_group)begin
        for(i=0;i<8;i=i+1)if(bank_role)bank0[write_group*64+product_row[2:0]*8+i]<=value[i][31:0];else bank1[write_group*64+product_row[2:0]*8+i]<=value[i][31:0];
       end
     row<=0;row_valid<=0;operand_valid<=0;fetch_done<=0;
     for(i=0;i<8;i=i+1)dot[i]<=0;
     if(phase==DEC_WRITE)phase<=mode==0?PRED_MUL:UP_MUL;else phase<=READ_MUL;
    end
    PRED_ADD,READ_ADD:begin
     for(i=0;i<8;i=i+1)dot[i]<=dot[i]+$signed(product[i]);
     row<=0;row_valid<=0;operand_valid<=0;fetch_done<=0;phase<=phase==PRED_ADD?PRED_END:READ_END;
    end
    ERR_FETCH,SKIP_FETCH,CONV_FETCH:begin
     for(i=0;i<8;i=i+1)begin operand_a[i]<=mul_a[i];operand_b[i]<=mul_b[i];end
     phase<=phase==ERR_FETCH?ERR_MUL:phase==SKIP_FETCH?SKIP_MUL:CONV_MUL;
    end
    ERR_MUL,SKIP_MUL,CONV_MUL:begin
     for(i=0;i<8;i=i+1)product[i]<=operand_a[i]*operand_b[i];
     phase<=phase==ERR_MUL?ERR_WRITE:phase==SKIP_MUL?SKIP_WRITE:CONV_ADD;
    end
    PRED_END,ERR_PREP,ERR_WRITE:begin
     failed<=failed||value_error;for(i=0;i<8;i=i+1)error_value[i]<=value[i][31:0];
     phase<=phase==PRED_END?ERR_PREP:phase==ERR_PREP?ERR_FETCH:UP_MUL;
    end
    READ_END:begin
     failed<=failed||value_error;for(i=0;i<8;i=i+1)output_value[i]<=value[i][31:0];
     phase<=mode==0?FINISH:SKIP_FETCH;
    end
    SKIP_WRITE,CONV_END:begin
     failed<=failed||value_error;for(i=0;i<8;i=i+1)output_value[i]<=value[i][31:0];phase<=FINISH;
    end
    CONV_ADD:begin
     for(i=0;i<8;i=i+1)dot[i]<=dot[i]+$signed({{63{product[i][64]}},product[i]});
     if(tap==3)phase<=CONV_END;else begin tap<=tap+1;phase<=CONV_FETCH;end
    end
    FINISH:begin
     rsp_valid<=1;rsp_error<=failed;rsp_data<=0;phase<=IDLE;output_valid<=!failed;
     if(!failed)begin if(mode==2)pending_history<=1;else pending_state<=1;end
     // A failed combined state calculation revokes only its state candidate;
     // a previously completed convolution remains explicitly revocable.
    end
    COPY:begin
     // Atomic active/shadow ownership exchange, including SSM's reused decay
     // storage. Every later SSM step must reload its inactive-bank factors.
     if(pending_state)bank_role<=!bank_role;
     if(pending_history)for(i=0;i<24;i=i+1)history[i]<=history_next[i];
     pending_state<=0;pending_history<=0;position<=next_position;epoch<=epoch+1;
     x_valid<=0;output_valid<=0;phase<=IDLE;rsp_valid<=1;rsp_error<=0;rsp_data<=0;
    end
    default:begin end
   endcase
  end
 end
endmodule
