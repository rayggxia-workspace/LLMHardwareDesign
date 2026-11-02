// Eight-wide recurrent pass engine. Global dot/error survive tile replacement.
// Two physical state banks, each WORDS S32. No per-tile transaction commit.
module r_stream #(parameter WORDS=256)(
 input wire clk,reset,
 input wire load_valid,output wire load_ready,input wire [2:0] load_target,
 input wire [9:0] load_index,input wire [127:0] load_data,
 input wire rd_bank,input wire [9:0] rd_index,output wire [127:0] rd_data,
 input wire cmd_valid,output wire cmd_ready,input wire [2:0] cmd_op,
 input wire [8:0] cmd_rows,input wire cmd_role,cmd_clear,input wire [1:0] cmd_mode,
 output reg rsp_valid,input wire rsp_ready,output reg rsp_error,output reg [511:0] rsp_data
);
 localparam IDLE=0,PASS=1,EPREP=2,EFETCH=3,EWAIT=4,FPREP=5,SFETCH=6,SWAIT=7,FRESP=8;
 reg [3:0] phase;reg [2:0] op;reg [1:0] mode;reg role,failed;
 reg [8:0] rows,issue_row,operand_row,product_row;
 reg signed [31:0] bank0[0:WORDS-1],bank1[0:WORDS-1];
 reg signed [15:0] key[0:WORDS/8-1],query[0:WORDS/8-1];
 reg signed [31:0] x[0:7],update[0:7],skip[0:7],hist[0:23];reg signed [15:0] taps[0:31];
 reg [31:0] decay,beta;reg signed [63:0] dot[0:7];reg signed [31:0] output_value[0:7];
 reg signed [31:0] oa[0:7],obase[0:7],pbase[0:7];reg signed [32:0] ob[0:7];reg signed [64:0] product[0:7];
 reg operand_valid,product_valid;
 reg signed [127:0] value[0:7],pred_value[0:7];reg bad;
 function automatic signed [127:0] rne;
  input signed [127:0] v;input [6:0] shift;
  reg signed [127:0] q;reg [127:0] remn,half,mask;
  begin q=v>>>shift;mask=(128'd1<<shift)-1;remn=$unsigned(v)&mask;half=128'd1<<(shift-1);rne=q+$signed({127'd0,(remn>half)||((remn==half)&&q[0])});end
 endfunction
 function automatic fits32;input signed [127:0] v;begin fits32=v[127:31]=={97{v[31]}};end endfunction
 wire signed [31:0] arow[0:7],brow[0:7];
 for(genvar l=0;l<8;l=l+1)begin
  wire signed [31:0] first=bank0[issue_row*8+l],second=bank1[issue_row*8+l];
  assign arow[l]=role?second:first;assign brow[l]=role?first:second;
 end
 assign cmd_ready=!reset&&phase==IDLE&&(!rsp_valid||rsp_ready);
 assign load_ready=cmd_ready&&!cmd_valid;
 for(genvar r=0;r<4;r=r+1)begin
  wire [31:0] first=bank0[rd_index*4+r],second=bank1[rd_index*4+r];
  assign rd_data[32*r+:32]=rd_bank?second:first;
 end
 always @*begin
  bad=0;
  for(integer l=0;l<8;l=l+1)begin
   value[l]=0;pred_value[l]=rne({{64{dot[l][63]}},dot[l]},14);
   if(phase==PASS)begin
    if(op==0)value[l]=rne({{63{product[l][64]}},product[l]},31);
    else if(op==2)value[l]=$signed({{96{pbase[l][31]}},pbase[l]})+rne({{63{product[l][64]}},product[l]},14);
   end else if(phase==EPREP)begin value[l]=$signed({{96{x[l][31]}},x[l]})-$signed({{96{pred_value[l][31]}},pred_value[l][31:0]});if(!fits32(pred_value[l]))bad=1;end
   else if(phase==EWAIT)value[l]=rne({{63{product[l][64]}},product[l]},31);
   else if(phase==FPREP)value[l]=rne({{64{dot[l][63]}},dot[l]},14);
   else if(phase==SWAIT)value[l]=$signed({{96{output_value[l][31]}},output_value[l]})+rne({{63{product[l][64]}},product[l]},16);
   if(!fits32(value[l]))bad=1;
  end
 end
 integer i;
 always @(posedge clk)begin
  if(reset)begin phase<=IDLE;rsp_valid<=0;rsp_data<=0;rsp_error<=0;failed<=0;operand_valid<=0;product_valid<=0;issue_row<=0;rows<=0;role<=0;mode<=0;op<=0;decay<=0;beta<=0;end
  else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(load_valid&&load_ready)begin
    case(load_target)
     0,1:if(load_index<WORDS/4)for(i=0;i<4;i=i+1)begin if(load_target==0)bank0[load_index*4+i]<=load_data[32*i+:32];else bank1[load_index*4+i]<=load_data[32*i+:32];end
     2,3:for(i=0;i<8;i=i+1)if(load_index*8+i<WORDS/8)begin if(load_target==2)key[load_index*8+i]<=load_data[16*i+:16];else query[load_index*8+i]<=load_data[16*i+:16];end
     4:if(load_index<6)for(i=0;i<4;i=i+1)case(load_index[9:1])
      0:x[load_index[0]*4+i]<=load_data[32*i+:32];1:update[load_index[0]*4+i]<=load_data[32*i+:32];2:skip[load_index[0]*4+i]<=load_data[32*i+:32];
     endcase
     5:begin decay<=load_data[31:0];beta<=load_data[63:32];end
     6:if(load_index<6)for(i=0;i<4;i=i+1)hist[load_index*4+i]<=load_data[32*i+:32];
     7:if(load_index<4)for(i=0;i<8;i=i+1)taps[load_index*8+i]<=load_data[16*i+:16];
    endcase
   end
   if(operand_valid)begin for(i=0;i<8;i=i+1)begin product[i]<=oa[i]*ob[i];pbase[i]<=obase[i];end product_row<=operand_row;end
   product_valid<=operand_valid;operand_valid<=0;
   case(phase)
    IDLE:if(cmd_valid&&cmd_ready)begin
     op<=cmd_op;mode<=cmd_mode;role<=cmd_role;rows<=cmd_rows;issue_row<=0;operand_valid<=0;product_valid<=0;
     rsp_data<=0;rsp_error<=failed;
     case(cmd_op)
      0,1,2,3:if(cmd_rows==0||cmd_rows>WORDS/8)begin rsp_valid<=1;rsp_error<=1;end else begin phase<=PASS;if(cmd_clear)for(i=0;i<8;i=i+1)dot[i]<=0;end
      4:phase<=EPREP;
      5:phase<=FPREP;
      6:begin rows<=4;phase<=PASS;for(i=0;i<8;i=i+1)dot[i]<=0;end
      7:begin failed<=0;rsp_valid<=1;rsp_error<=0;for(i=0;i<8;i=i+1)dot[i]<=0;end
     endcase
    end
    PASS:begin
     if(issue_row<rows)begin
      operand_valid<=1;operand_row<=issue_row;issue_row<=issue_row+1'b1;
      for(i=0;i<8;i=i+1)begin
       if(op==0)begin oa[i]<=arow[i];ob[i]<=mode==1?{1'b0,$unsigned(brow[i])}:{1'b0,decay};end
       else if(op==1||op==3)begin oa[i]<=brow[i];ob[i]<=op==1?$signed(key[issue_row]):$signed(query[issue_row]);end
       else if(op==2)begin oa[i]<=update[i];ob[i]<=$signed(key[issue_row]);obase[i]<=brow[i];end
       else begin oa[i]<=issue_row==0?x[i]:hist[(issue_row-1)*8+i];ob[i]<=$signed(taps[issue_row*8+i]);end
      end
     end
     if(product_valid)begin
      if(op==0||op==2)begin
       failed<=failed||bad;
       for(i=0;i<8;i=i+1)begin if(role)bank0[product_row*8+i]<=value[i][31:0];else bank1[product_row*8+i]<=value[i][31:0];end
      end else for(i=0;i<8;i=i+1)dot[i]<=dot[i]+$signed(product[i]);
      if(product_row+1==rows)begin
       phase<=IDLE;rsp_valid<=1;rsp_error<=failed||((op==0||op==2)&&bad);
       for(i=0;i<8;i=i+1)rsp_data[64*i+:64]<=op==0||op==2?{{32{value[i][31]}},value[i][31:0]}:dot[i]+$signed(product[i]);
      end
     end
    end
    EPREP:begin
     failed<=failed||bad;for(i=0;i<8;i=i+1)update[i]<=value[i][31:0];phase<=EFETCH;
    end
    EFETCH:begin for(i=0;i<8;i=i+1)begin oa[i]<=update[i];ob[i]<={1'b0,beta};end operand_valid<=1;phase<=EWAIT;end
    EWAIT:if(product_valid)begin failed<=failed||bad;for(i=0;i<8;i=i+1)update[i]<=value[i][31:0];rsp_valid<=1;rsp_error<=failed||bad;phase<=IDLE;end
    FPREP:begin failed<=failed||bad;for(i=0;i<8;i=i+1)output_value[i]<=value[i][31:0];phase<=mode==1?SFETCH:FRESP;end
    SFETCH:begin for(i=0;i<8;i=i+1)begin oa[i]<=x[i];ob[i]<=$signed(skip[i]);end operand_valid<=1;phase<=SWAIT;end
    SWAIT:if(product_valid)begin failed<=failed||bad;for(i=0;i<8;i=i+1)output_value[i]<=value[i][31:0];phase<=FRESP;end
    FRESP:begin for(i=0;i<8;i=i+1)rsp_data[64*i+:64]<={{32{output_value[i][31]}},output_value[i]};rsp_valid<=1;rsp_error<=failed;phase<=IDLE;end
   endcase
  end
 end
endmodule
