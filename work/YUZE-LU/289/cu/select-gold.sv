module gold(input [7:0] exam,hit_i,pad_i,wait_i,eligible,input [511:0] addresses,input [23:0] hcs,ccs,output reg candidate,hit,pad,waiting,cp,output reg [1:0] cl,output reg [2:0] cc,hc,output reg [63:0] address); always @* begin candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;
for(integer p=0;p<2;p=p+1)for(integer l=0;l<4;l=l+1)if(!candidate&&exam[p*4+l])begin
 address=addresses[64*(p*4+l)+:64];waiting=wait_i[p*4+l];hit=hit_i[p*4+l];hc=hcs[3*(p*4+l)+:3];pad=pad_i[p*4+l];
 if(eligible[p*4+l])begin candidate=1;cp=1'(p);cl=2'(l);cc=ccs[3*(p*4+l)+:3];end end
end endmodule
