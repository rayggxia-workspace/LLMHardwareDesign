// Exact eight-way S32 x (S16/S32/U32) using the unchanged frozen M.
// Five base-128 digits for S32, three for S16. Signed high digit only.
// A single 96-bit merge adder is explicitly added; no free wide arithmetic.
module c_wide_m(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [255:0] in_a,in_b,input wire [1:0] in_kind,
 output reg out_valid,input wire out_ready,
 output reg [511:0] out_data,output reg out_error,
 output wire [31:0] command_count
);
 localparam IDLE=0,LA=1,LB=2,EX=3,EW=4,RS=5,RC=6,MERGE=7,FINISH=8;
 reg [3:0] state;reg [255:0] aa,bb;reg [1:0] kind;
 reg [2:0] ai,bi,lane;reg [1:0] pair_index;
 reg signed [95:0] accum[0:7];reg signed [63:0] partial[0:7];
 reg failed;reg [31:0] commands;
 wire a_ready,b_ready,cmd_ready,rsp_valid,rsp_error,rsp_sat,m_busy;
 wire [127:0] rsp_data;reg [127:0] adata;reg [511:0] bdata;
 // Explicit indexed part select avoids expression-select extensions.
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
 always @* begin
  adata=0;bdata=0;
  for(integer l=0;l<8;l=l+1)begin
   adata[8*l+:8]=get_digit(aa[32*l+:32],ai,1'b1,1'b0);
   bdata[8*(8*l+l)+:8]=get_digit(bb[32*l+:32],bi,kind!=2,kind==0);
  end
 end
 wire [5:0] shift=7*({3'b0,ai}+{3'b0,bi});
 wire signed [95:0] term=$signed({{32{partial[lane][63]}},partial[lane]})<<<shift;
 wire signed [95:0] addition=accum[lane]+term;
 wire last_b=bi==(kind==0?2:4);
 assign in_ready=!reset&&state==IDLE&&(!out_valid||out_ready);
 assign command_count=commands;
 block_v2_m m(
  .clk(clk),.reset(reset),.a_valid(state==LA),.a_ready(a_ready),.a_bank(1'b0),.a_row(3'd0),.a_tile(2'd0),.a_wide(1'b0),.a_data(adata),
  .b_valid(state==LB),.b_ready(b_ready),.b_bank(1'b0),.b_tile(2'd0),.b_wide(1'b0),.b_half(1'b0),.b_data(bdata),
  .cmd_valid(state==EX||state==RS),.cmd_ready(cmd_ready),.cmd_op(state==EX?4'd10:4'd3),
  .cmd_index(state==EX?6'd0:{4'd0,pair_index}),
  .cmd_data(state==EX?64'h0000000000009884:64'd0),
  .rsp_valid(rsp_valid),.rsp_ready(state==EW||state==RC),.rsp_data(rsp_data),.rsp_error(rsp_error),.rsp_saturated(rsp_sat),.busy(m_busy)
 );
 integer j;
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;out_valid<=0;out_data<=0;out_error<=0;commands<=0;failed<=0;ai<=0;bi<=0;lane<=0;pair_index<=0;aa<=0;bb<=0;kind<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   case(state)
    IDLE:if(in_valid&&in_ready)begin
     aa<=in_a;bb<=in_b;kind<=in_kind;failed<=in_kind==3;commands<=0;ai<=0;bi<=0;lane<=0;pair_index<=0;
     for(j=0;j<8;j=j+1)accum[j]<=0;
     state<=in_kind==3?FINISH:LA;
    end
    LA:if(a_ready)state<=LB;
    LB:if(b_ready)state<=EX;
    EX:if(cmd_ready)begin commands<=commands+1'b1;state<=EW;end
    EW:if(rsp_valid)begin failed<=failed||rsp_error||rsp_sat;pair_index<=0;state<=RS;end
    RS:if(cmd_ready)state<=RC;
    RC:if(rsp_valid)begin
     partial[{pair_index,1'b0}]<=rsp_data[63:0];partial[{pair_index,1'b1}]<=rsp_data[127:64];
     failed<=failed||rsp_error||rsp_sat;
     if(pair_index==3)begin lane<=0;state<=MERGE;end else begin pair_index<=pair_index+1'b1;state<=RS;end
    end
    MERGE:begin
     accum[lane]<=addition;
     if(lane==7)begin
      if(last_b)begin bi<=0;if(ai==4)state<=FINISH;else begin ai<=ai+1'b1;state<=LA;end end
      else begin bi<=bi+1'b1;state<=LA;end
     end else lane<=lane+1'b1;
    end
    FINISH:begin
     out_valid<=1;out_error<=failed;
     for(j=0;j<8;j=j+1)begin out_data[64*j+:64]<=accum[j][63:0];if(accum[j][95:64]!={32{accum[j][63]}})out_error<=1;end
     state<=IDLE;
    end
   endcase
  end
 end
endmodule
