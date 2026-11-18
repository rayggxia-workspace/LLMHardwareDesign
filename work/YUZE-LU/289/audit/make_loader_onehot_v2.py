from pathlib import Path
import hashlib,json
p=Path(__file__).parent
source=p/'loader-distributed-parallel-reviewed.sv'
s=source.read_text()
start=s.index('  candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;free_owner=')
end=s.index(' always @(posedge clk)',start)
declarations=''' reg [7:0] lane_winner,lane_selected;
 reg [76:0] lane_result[0:7];
'''
s=s.replace(' reg [63:0] lane_address[0:7];',declarations+' reg [63:0] lane_address[0:7];')
start=s.index('  candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;free_owner=')
end=s.index(' always @(posedge clk)',start)
body='''  for(integer j=0;j<8;j=j+1)begin
   lane_winner[j]=lane_eligible[j]&&!(|(lane_eligible & 8'((9'd1<<j)-1)));
   lane_selected[j]=lane_winner[j]||((!(|lane_eligible))&&lane_exam[j]&&!(|(lane_exam & (8'hff << (j+1)))));
   lane_result[j]={lane_winner[j],
      lane_hit[j]&lane_selected[j],lane_pad[j]&lane_selected[j],lane_wait[j]&lane_selected[j],
      1'(j/4)&lane_winner[j],2'(j%4)&{2{lane_winner[j]}},
      lane_cc[j]&{3{lane_winner[j]}},lane_hc[j]&{3{lane_selected[j]}},
      lane_address[j]&{64{lane_selected[j]}}};
  end
  {candidate,hit,pad,waiting,cp,cl,cc,hc,address}=
     ((lane_result[0]|lane_result[1])|(lane_result[2]|lane_result[3]))|
     ((lane_result[4]|lane_result[5])|(lane_result[6]|lane_result[7]));
  free_owner=!pending[0]?0:1;
 end
'''
out=p/'loader-onehot-v2.sv';out.write_text(s[:start]+body+s[end:])
gold=(p.parent/'cu/select-gold.sv').read_text()
port=gold.split('; always @*',1)[0].replace('module gold','module gate')+';\n'
bridge='''wire [7:0] lane_exam=exam,lane_eligible=exam & eligible,lane_hit=hit_i,lane_pad=pad_i,lane_wait=wait_i;
wire [63:0] lane_address[0:7];wire [2:0] lane_hc[0:7],lane_cc[0:7];
generate for(genvar k=0;k<8;k=k+1)begin
 assign lane_address[k]=addresses[64*k+:64];assign lane_hc[k]=hcs[3*k+:3];assign lane_cc[k]=ccs[3*k+:3];
end endgenerate
'''
(p/'onehot-select-gold.sv').write_text(gold)
(p/'onehot-v2-select-gate.sv').write_text(port+bridge+declarations+'always @* begin\n'+body.replace('  free_owner=!pending[0]?0:1;\n','')+'endmodule\n')
(p/'onehot-select-proof.ys').write_text('read_verilog -sv onehot-select-gold.sv onehot-v2-select-gate.sv\nproc\nopt\nequiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_status -assert\n')
# Exhaustively verify control masks for independent arbitrary eligibility/exam masks.
for e in range(256):
 for x in range(256):
  # Eligibility is exam-qualified in real RTL. Enforce that required bridge.
  if e & ~x:continue
  chosen=next((j for j in range(8) if e>>j&1),None)
  fallback=max((j for j in range(8) if x>>j&1),default=None)
  w=[bool(e>>j&1) and not(e&((1<<j)-1)) for j in range(8)]
  z=[w[j] or (not e and bool(x>>j&1) and not(x&(~((1<<(j+1))-1)&255))) for j in range(8)]
  assert w==[j==chosen for j in range(8)]
  assert z==[j==(chosen if chosen is not None else fallback) for j in range(8)]
(p/'loader-onehot-v2-generation.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'scope':'two-state; eligibility implies exam; exhaustive control-mask check plus unchanged lane values. SAT miter and physical result pending'},indent=2))
print(out)
