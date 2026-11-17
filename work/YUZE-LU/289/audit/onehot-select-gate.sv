module gate(input [7:0] exam,hit_i,pad_i,wait_i,eligible,input [511:0] addresses,input [23:0] hcs,ccs,output reg candidate,hit,pad,waiting,cp,output reg [1:0] cl,output reg [2:0] cc,hc,output reg [63:0] address);
wire [7:0] lane_exam=exam,lane_eligible=exam & eligible,lane_hit=hit_i,lane_pad=pad_i,lane_wait=wait_i;
wire [63:0] lane_address[0:7];wire [2:0] lane_hc[0:7],lane_cc[0:7];
generate for(genvar k=0;k<8;k=k+1)begin
 assign lane_address[k]=addresses[64*k+:64];assign lane_hc[k]=hcs[3*k+:3];assign lane_cc[k]=ccs[3*k+:3];
end endgenerate
 reg [7:0] lane_winner,lane_selected;
 reg [76:0] lane_result[0:7];
always @* begin
  for(integer j=0;j<8;j=j+1)begin
   lane_winner[j]=lane_eligible[j]&&!(|(lane_eligible & 8'((9'd1<<j)-1)));
   lane_selected[j]=lane_winner[j]||((!(|lane_eligible))&&lane_exam[j]&&!(|(lane_exam & ~8'((9'd1<<(j+1))-1))));
   lane_result[j]={lane_winner[j],
      lane_hit[j]&lane_selected[j],lane_pad[j]&lane_selected[j],lane_wait[j]&lane_selected[j],
      1'(j/4)&lane_winner[j],2'(j%4)&{2{lane_winner[j]}},
      lane_cc[j]&{3{lane_winner[j]}},lane_hc[j]&{3{lane_selected[j]}},
      lane_address[j]&{64{lane_selected[j]}}};
  end
  {candidate,hit,pad,waiting,cp,cl,cc,hc,address}=
     ((lane_result[0]|lane_result[1])|(lane_result[2]|lane_result[3]))|
     ((lane_result[4]|lane_result[5])|(lane_result[6]|lane_result[7]));
 end
endmodule
