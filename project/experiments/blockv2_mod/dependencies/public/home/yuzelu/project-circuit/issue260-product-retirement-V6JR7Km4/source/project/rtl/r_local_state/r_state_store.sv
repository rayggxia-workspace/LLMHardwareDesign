// Issue166: explicit 16-row, 32-bit lane-local state tiles.
// Read accepted at E0, local select E1, local data E2, merged data E3.
// Write accepted E0, local select/data E1, storage commit E2.
// Read/write same row at E2 returns pre-write data. Storage is not reset.
module r_state_store #(
 parameter WORDS=256,
 parameter ROWS=WORDS/8,
 parameter AW=$clog2(ROWS),
 parameter GROUPS=ROWS/16
)(
 input wire clk,reset,
 input wire rd_valid,input wire [AW-1:0] rd_row,
 output reg out_valid,output reg [255:0] out_bank0,out_bank1,
 input wire wr_valid,wr_bank,input wire [AW-1:0] wr_row,
 input wire [7:0] wr_mask,input wire [255:0] wr_data,
 output wire write_pending
);
 reg rv0,rv1,rv2,wv0,wv1;
 reg [AW-1:0] ra0,wa0;reg wb0;
 reg [7:0] wm0;reg [255:0] wd0;
 wire [15:0] rdecode=16'b1<<ra0[3:0];
 wire [15:0] wdecode=16'b1<<wa0[3:0];
 assign write_pending=wv0|wv1;
 wire [255:0] local_read[0:2*GROUPS-1];
 always @(posedge clk) begin
  if(reset)begin rv0<=0;rv1<=0;rv2<=0;out_valid<=0;wv0<=0;wv1<=0;end
  else begin
   rv0<=rd_valid;rv1<=rv0;rv2<=rv1;out_valid<=rv2;
   wv0<=wr_valid;wv1<=wv0;
  end
  if(rd_valid)ra0<=rd_row;
  if(wr_valid)begin wa0<=wr_row;wb0<=wr_bank;wm0<=wr_mask;wd0<=wr_data;end
 end
 for(genvar b=0;b<2;b=b+1)begin:BANK
  for(genvar g=0;g<GROUPS;g=g+1)begin:GROUP
   for(genvar l=0;l<8;l=l+1)begin:LANE
    // Scoped keep prevents identical lane select registers from remerging.
    wire [15:0] rsel_d=(!reset&&rv0&&((ra0>>4)==g))?rdecode:16'b0;
    wire [15:0] wsel_d=(!reset&&wv0&&(wb0==b)&&((wa0>>4)==g)&&wm0[l])?wdecode:16'b0;
`ifdef SYNTHESIS
    wire [15:0] rsel_q,wsel_q;
    for(genvar s=0;s<16;s=s+1)begin:SELECT_FF
     (* keep=1, dont_touch=1 *) DFF_X1 rff(.CK(clk),.D(rsel_d[s]),.Q(rsel_q[s]),.QN());
     (* keep=1, dont_touch=1 *) DFF_X1 wff(.CK(clk),.D(wsel_d[s]),.Q(wsel_q[s]),.QN());
    end
`else
    reg [15:0] rsel_q,wsel_q;
    always @(posedge clk)begin rsel_q<=rsel_d;wsel_q<=wsel_d;end
`endif
    (* keep=1 *) reg [31:0] wdata_q;
    reg [31:0] words[0:15];
    reg [31:0] rlocal_q;
    reg [31:0] selected;
    always @*begin
     selected=0;
     for(integer n=0;n<16;n=n+1)selected=selected|(words[n]&{32{rsel_q[n]}});
    end
    always @(posedge clk)begin
     if(wv0&&(wb0==b)&&((wa0>>4)==g)&&wm0[l])wdata_q<=wd0[32*l+:32];
     rlocal_q<=selected;
    end
    for(genvar n=0;n<16;n=n+1)begin:WORD
     always @(posedge clk)if(!reset&&wsel_q[n])words[n]<=wdata_q;
    end
    assign local_read[b*GROUPS+g][32*l+:32]=rlocal_q;
   end
  end
 end
 reg [255:0] merged0,merged1;
 always @*begin
  merged0=0;merged1=0;
  for(integer g=0;g<GROUPS;g=g+1)begin
   merged0=merged0|local_read[g];merged1=merged1|local_read[GROUPS+g];
  end
 end
 always @(posedge clk)begin out_bank0<=merged0;out_bank1<=merged1;end
endmodule
