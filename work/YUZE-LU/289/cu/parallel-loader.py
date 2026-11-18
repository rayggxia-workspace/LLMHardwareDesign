from pathlib import Path
p=Path(__file__).parent
s=(p/'loader-original.sv').read_text()
start=s.index(' always @* begin')
end=s.index(' always @(posedge clk)',start)
body=''' reg [63:0] lane_address[0:7];
 reg [7:0] lane_exam,lane_hit,lane_pad,lane_wait,lane_eligible;
 reg [2:0] lane_hc[0:7],lane_cc[0:7];
 always @* begin
  for(integer j=0;j<8;j=j+1)begin
   lane_address[j]=addr(pi[j/4],2'(j%4));
   lane_exam[j]=pv[j/4]&&!pwriting[j/4]&&!pm[j/4][j%4];
   lane_wait[j]=(pending[0]&&lines[0]=={lane_address[j][63:6],6'd0})||
      (pending[1]&&lines[1]=={lane_address[j][63:6],6'd0})||
      (offer&&offer_address=={lane_address[j][63:6],6'd0});
   lane_hit[j]=0;lane_hc[j]=0;
   for(integer c=0;c<5;c=c+1)
    if(!lane_hit[j]&&cv[c]&&ca[c]=={lane_address[j][63:6],6'd0})begin
     lane_hit[j]=1;lane_hc[j]=3'(c);
    end
   lane_pad[j]=is_pad(pi[j/4],2'(j%4));
   lane_cc[j]=cache_index(pi[j/4],2'(j%4));
   lane_eligible[j]=lane_exam[j]&&(lane_pad[j]||lane_hit[j]||(!lane_wait[j]&&pending!=3&&!offer));
  end
  candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;free_owner=!pending[0]?0:1;
  for(integer j=0;j<8;j=j+1)begin
   if(lane_exam[j]&&!candidate)begin
    address=lane_address[j];waiting=lane_wait[j];hit=lane_hit[j];hc=lane_hc[j];pad=lane_pad[j];
    if(lane_eligible[j])begin candidate=1;cp=1'(j/4);cl=2'(j%4);cc=lane_cc[j];end
   end
  end
 end
'''
(p/'loader-parallel.sv').write_text(s[:start]+body+s[end:])
# Isolate only the combinational priority network; use identical arbitrary
# lane evaluations, proving selection semantics for all possible bit patterns.
ports='input [7:0] exam,hit_i,pad_i,wait_i,eligible,input [511:0] addresses,input [23:0] hcs,ccs,output reg candidate,hit,pad,waiting,cp,output reg [1:0] cl,output reg [2:0] cc,hc,output reg [63:0] address'
default='candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;'
old='''for(integer p=0;p<2;p=p+1)for(integer l=0;l<4;l=l+1)if(!candidate&&exam[p*4+l])begin
 address=addresses[64*(p*4+l)+:64];waiting=wait_i[p*4+l];hit=hit_i[p*4+l];hc=hcs[3*(p*4+l)+:3];pad=pad_i[p*4+l];
 if(eligible[p*4+l])begin candidate=1;cp=1'(p);cl=2'(l);cc=ccs[3*(p*4+l)+:3];end end'''
new='''for(integer j=0;j<8;j=j+1)if(exam[j]&&!candidate)begin
 address=addresses[64*j+:64];waiting=wait_i[j];hit=hit_i[j];hc=hcs[3*j+:3];pad=pad_i[j];
 if(eligible[j])begin candidate=1;cp=1'(j/4);cl=2'(j%4);cc=ccs[3*j+:3];end end'''
for name,logic in [('gold',old),('gate',new)]:
 (p/f'select-{name}.sv').write_text(f'module {name}({ports}); always @* begin {default}\n{logic}\nend endmodule\n')
(p/'select-proof.ys').write_text('read_verilog -sv select-gold.sv select-gate.sv\nproc\nopt\nequiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_status -assert\n')
