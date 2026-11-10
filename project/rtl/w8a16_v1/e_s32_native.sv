`timescale 1ns/1ps
// Candidate E32 pointwise service. Four S32 lanes per 128-bit operand word;
// two arithmetic lanes, evaluated in two halves. One finite command/result.
// This is an explicit compute macro candidate, not arithmetic hidden in LC.
// There is no SRAM, FMA reassociation, or external per-lane wide data pin.
module e_s32_native(
 input wire clk,reset,
 input wire in_valid,output wire in_ready,
 input wire [3:0] in_op,in_mask,
 input wire [7:0] in_shift,
 input wire [2:0] in_minus,
 input wire [127:0] in_data,
 output reg out_valid,input wire out_ready,
 output reg [127:0] out_data,
 output reg [3:0] out_clipped,
 output reg out_error
);
 localparam [3:0] ADD2=0,ADD3=1,PRODUCT=2,CONVERT32=3,CONVERT16=4,
                  MINIMUM=5,MAXIMUM=6,CMP_LT=7,CMP_LE=8,SELECT=9,
                  MASK_ZERO=10,MASK_FLOOR=11;
 localparam [3:0] FIRST=0,SECOND=1,THIRD=2,PARTIAL=3,MID=4,TOTAL=5,
                  SCALE=6,ROUND=7,PACK=8;
 localparam signed [63:0] I32_MAX=64'sd2147483647,I32_MIN=-64'sd2147483648;
 localparam signed [63:0] I16_MAX=64'sd32767,I16_MIN=-64'sd32768;
 reg [3:0] phase,op,mask;
 reg [7:0] shift;
 reg [2:0] minus;
 reg high_half;
 reg [127:0] a,b,c;
 reg [31:0] ll[2];
 reg signed [32:0] hl[2],lh[2];
 reg signed [31:0] hh[2];
 reg signed [33:0] middle[2];
 reg signed [63:0] total[2],quotient[2],rounded[2];
 wire [31:0] clipped[2];
 reg inc[2];
 wire first_bad=in_op>MASK_FLOOR || $signed(in_shift)<-8'sd63 || $signed(in_shift)>8'sd63 ||
    ((in_op!=PRODUCT&&in_op!=CONVERT32&&in_op!=CONVERT16)&&in_shift!=0) ||
    ((in_op!=ADD2&&in_op!=ADD3)&&in_minus!=0) || (in_op==ADD2&&in_minus[2]);
 wire unary=in_op==CONVERT32||in_op==CONVERT16||in_op==MASK_ZERO||in_op==MASK_FLOOR;
 assign in_ready=!reset&&((phase==FIRST&&!out_valid)||phase==SECOND||phase==THIRD);
 wire [7:0] shift_magnitude=shift[7] ? (~shift+8'd1) : shift;
 wire [5:0] amount=shift_magnitude[5:0];
 wire [63:0] half=64'd1<<(amount-6'd1);
 wire [63:0] low_mask=(64'd1<<amount)-64'd1;
 wire narrow=op==CONVERT16||op==CMP_LT||op==CMP_LE;
 wire signed [63:0] clip_max=narrow?I16_MAX:I32_MAX,clip_min=narrow?I16_MIN:I32_MIN;
 wire signed [63:0] left_hi=I32_MAX>>>amount,left_lo=I32_MIN>>>amount;

 for(genvar lane=0;lane<2;lane=lane+1)begin: lanes
   wire [1:0] index_word={high_half,1'(lane)};
   wire signed [31:0] x=$signed(a[32*index_word+:32]);
   wire signed [31:0] y=$signed(b[32*index_word+:32]);
   wire signed [31:0] z=$signed(c[32*index_word+:32]);
   wire signed [63:0] xx={{32{x[31]}},x},yy={{32{y[31]}},y},zz={{32{z[31]}},z};
   wire signed [33:0] xsum=minus[0]?-$signed({{2{x[31]}},x}):$signed({{2{x[31]}},x});
   wire signed [33:0] ysum=minus[1]?-$signed({{2{y[31]}},y}):$signed({{2{y[31]}},y});
   wire signed [33:0] zsum=minus[2]?-$signed({{2{z[31]}},z}):$signed({{2{z[31]}},z});
   wire signed [33:0] add_value=xsum+ysum+(op==ADD3?zsum:34'sd0);
   wire signed [63:0] product_value=$signed({hh[lane],ll[lane]})+
                                  ($signed({{30{middle[lane][33]}},middle[lane]})<<<16);
   wire [63:0] remainder=$unsigned(total[lane])&low_mask;
   wire signed [63:0] floor_value=total[lane]>>>amount;
   assign clipped[lane]=32'(rounded[lane]>clip_max?clip_max:
                                 rounded[lane]<clip_min?clip_min:rounded[lane]);
   always @(posedge clk) begin
     if(!reset)begin
       case(phase)
         PARTIAL:begin
           ll[lane]<=x[15:0]*y[15:0];
           hl[lane]<=$signed(x[31:16])*$signed({1'b0,y[15:0]});
           lh[lane]<=$signed({1'b0,x[15:0]})*$signed(y[31:16]);
           hh[lane]<=$signed(x[31:16])*$signed(y[31:16]);
         end
         MID:middle[lane]<=$signed({hl[lane][32],hl[lane]})+$signed({lh[lane][32],lh[lane]});
         TOTAL:case(op)
           ADD2,ADD3:total[lane]<={{30{add_value[33]}},add_value};
           PRODUCT:total[lane]<=product_value;
           MINIMUM:total[lane]<=x<y?xx:yy;
           MAXIMUM:total[lane]<=x>y?xx:yy;
           CMP_LT:total[lane]<=x<y?64'sd1:64'sd0;
           CMP_LE:total[lane]<=x<=y?64'sd1:64'sd0;
           SELECT:total[lane]<=x!=0?yy:zz;
           MASK_ZERO,MASK_FLOOR:total[lane]<=mask[index_word]?xx:(op==MASK_FLOOR?I32_MIN:64'sd0);
           default:total[lane]<=xx;
         endcase
         SCALE:begin
           inc[lane]<=0;
           if(shift[7])begin
             // Saturation sentinels prevent an overflowing left shift. A
             // nonzero value outside S32 also necessarily overflows S16.
             if(total[lane]>left_hi)quotient[lane]<=I32_MAX+64'sd1;
             else if(total[lane]<left_lo||(amount>=32&&total[lane]<0))quotient[lane]<=I32_MIN-64'sd1;
             else quotient[lane]<=total[lane]<<<amount;
           end else begin
             quotient[lane]<=floor_value;
             inc[lane]<=amount!=0&&(remainder>half||(remainder==half&&floor_value[0]));
           end
         end
         ROUND:rounded[lane]<=quotient[lane]+$signed({63'd0,inc[lane]});
         default:begin end
       endcase
     end
   end
 end

 always @(posedge clk) begin
   if(reset)begin
     phase<=FIRST;op<=0;mask<=0;shift<=0;minus<=0;high_half<=0;
     a<=0;b<=0;c<=0;out_valid<=0;out_data<=0;out_clipped<=0;out_error<=0;
   end else begin
     if(out_valid&&out_ready)out_valid<=0;
     case(phase)
       FIRST:if(in_valid&&in_ready)begin
         op<=in_op;mask<=in_mask;shift<=in_shift;minus<=in_minus;high_half<=0;
         a<=in_data;out_data<=0;out_clipped<=0;out_error<=first_bad;
         if(first_bad)out_valid<=1;
         else phase<=unary?TOTAL:SECOND;
       end
       SECOND:if(in_valid&&in_ready)begin
         b<=in_data;
         phase<=op==ADD3||op==SELECT?THIRD:op==PRODUCT?PARTIAL:TOTAL;
       end
       THIRD:if(in_valid&&in_ready)begin c<=in_data;phase<=TOTAL;end
       PARTIAL:phase<=MID;
       MID:phase<=TOTAL;
       TOTAL:phase<=SCALE;
       SCALE:phase<=ROUND;
       ROUND:phase<=PACK;
       PACK:begin
         for(integer lane=0;lane<2;lane=lane+1)begin
           if(narrow)out_data[16*(2*int'(high_half)+lane)+:16]<=mask[2*int'(high_half)+lane]?clipped[lane][15:0]:16'd0;
           else out_data[32*(2*int'(high_half)+lane)+:32]<=
             (mask[2*int'(high_half)+lane]||op==MASK_FLOOR)?clipped[lane]:32'd0;
           out_clipped[2*int'(high_half)+lane]<=mask[2*int'(high_half)+lane]&&
             (rounded[lane]>clip_max||rounded[lane]<clip_min);
         end
         if(high_half)begin out_valid<=1;phase<=FIRST;end
         else begin high_half<=1;phase<=op==PRODUCT?PARTIAL:TOTAL;end
       end
       default:begin phase<=FIRST;out_data<=0;out_clipped<=0;out_valid<=1;out_error<=1;end
     endcase
   end
 end
 wire unused_magnitude=|shift_magnitude[7:6];
endmodule
