// Exact reconstruction through unchanged E. Base-128 digit products fit S16,
// so E never saturates before explicit signed 96-bit reconstruction.
module c_wide_e(input wire clk,reset,in_valid,output wire in_ready,input wire [255:0] in_a,in_b,input wire [1:0] in_kind,output reg out_valid,input wire out_ready,output reg [511:0] out_data,output reg out_error,output wire [31:0] command_count);
 localparam IDLE=0,EX=1,EW=2,MERGE=3,FINISH=4;
 reg [2:0] state;reg [255:0] aa,bb;reg [1:0] kind;reg [2:0] ai,bi,lane;
 reg signed [95:0] accum[0:7];reg signed [15:0] partial[0:7];reg failed;reg [31:0] commands;
 wire e_ready,e_valid,e_error,e_saturated;wire [127:0] e_data;reg [127:0] adata,bdata;
 function automatic signed [7:0] low_digit;
  input [31:0] v;input [2:0] pos;
  reg [31:0] shifted;
  begin shifted=v>>(7*pos);low_digit={1'b0,shifted[6:0]};end
 endfunction
 function automatic signed [7:0] get_digit;
  input [31:0] v;input [2:0] pos;input signed_value;input short_value;
  begin
   if(short_value&&pos==2)get_digit={{6{v[15]}},v[15:14]};
   else if(pos==4)get_digit=signed_value?{{4{v[31]}},v[31:28]}:{4'b0,v[31:28]};
   else get_digit=low_digit(v,pos);
  end
 endfunction

 always @*begin
  adata=0;bdata=0;
  for(integer l=0;l<8;l=l+1)begin
   adata[16*l+:16]=$signed(get_digit(aa[32*l+:32],ai,1'b1,1'b0));bdata[16*l+:16]=$signed(get_digit(bb[32*l+:32],bi,kind!=2,kind==0));
  end
 end
 wire [5:0] shift=7*({3'b0,ai}+{3'b0,bi});wire signed [95:0] term=$signed({{80{partial[lane][15]}},partial[lane]})<<<shift;wire signed [95:0] addition=accum[lane]+term;wire last_b=bi==(kind==0?2:4);
 assign in_ready=!reset&&state==IDLE&&(!out_valid||out_ready);assign command_count=commands;
 block_v2_e e(.clk(clk),.reset(reset),.in_valid(state==EX),.in_ready(e_ready),.in_op(4'd2),.in_shift(5'd0),.in_a(adata),.in_b(bdata),.in_c(128'd0),.out_valid(e_valid),.out_ready(state==EW),.out_data(e_data),.out_error(e_error),.out_saturated(e_saturated));
 integer j;
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;out_valid<=0;out_data<=0;out_error<=0;failed<=0;commands<=0;aa<=0;bb<=0;kind<=0;ai<=0;bi<=0;lane<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   case(state)
    IDLE:if(in_valid&&in_ready)begin aa<=in_a;bb<=in_b;kind<=in_kind;failed<=in_kind==3;commands<=0;ai<=0;bi<=0;lane<=0;for(j=0;j<8;j=j+1)accum[j]<=0;state<=in_kind==3?FINISH:EX;end
    EX:if(e_ready)begin commands<=commands+1'b1;state<=EW;end
    EW:if(e_valid)begin for(j=0;j<8;j=j+1)partial[j]<=e_data[16*j+:16];failed<=failed||e_error||e_saturated;lane<=0;state<=MERGE;end
    MERGE:begin accum[lane]<=addition;if(lane==7)begin if(last_b)begin bi<=0;if(ai==4)state<=FINISH;else begin ai<=ai+1'b1;state<=EX;end end else begin bi<=bi+1'b1;state<=EX;end end else lane<=lane+1'b1;end
    FINISH:begin out_valid<=1;out_error<=failed;for(j=0;j<8;j=j+1)begin out_data[64*j+:64]<=accum[j][63:0];if(accum[j][95:64]!={32{accum[j][63]}})out_error<=1;end state<=IDLE;end
   endcase
  end
 end
endmodule
