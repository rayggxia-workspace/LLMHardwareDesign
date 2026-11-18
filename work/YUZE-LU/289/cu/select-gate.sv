module gate(input [7:0] exam,hit_i,pad_i,wait_i,eligible,input [511:0] addresses,input [23:0] hcs,ccs,output reg candidate,hit,pad,waiting,cp,output reg [1:0] cl,output reg [2:0] cc,hc,output reg [63:0] address); always @* begin candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;
for(integer j=0;j<8;j=j+1)if(exam[j]&&!candidate)begin
 address=addresses[64*j+:64];waiting=wait_i[j];hit=hit_i[j];hc=hcs[3*j+:3];pad=pad_i[j];
 if(eligible[j])begin candidate=1;cp=1'(j/4);cl=2'(j%4);cc=ccs[3*j+:3];end end
end endmodule
