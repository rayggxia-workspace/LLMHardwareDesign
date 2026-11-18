from pathlib import Path
import hashlib,json
p=Path(__file__).parent
s=(p/'loader-distributed-parallel-reviewed.sv').read_text()
c=(p/'loader-onehot-v2.sv').read_text()
g=(p/'onehot-v2-select-gate.sv').read_text()
marker='  candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;free_owner='
a=s.index(marker);b=s.index(' always @(posedge clk)',a)
ca=c.rindex('  for(integer j=0;j<8;j=j+1)begin');cb=c.index(' always @(posedge clk)',ca)
decl=' reg [7:0] lane_winner,lane_selected;\n reg [76:0] lane_result[0:7];\n'
assert c[:ca].replace(decl,'')==s[:a]
assert c[cb:]==s[b:]
body=c[ca:cb].replace('  free_owner=!pending[0]?0:1;\n','')
assert g.split('always @* begin\n')[1]==body+'endmodule\n'
assert 'lane_eligible=exam & eligible' in g
assert 'lane_eligible[j]=lane_exam[j]' in c
r={'scope':'two-state all 77 selector outputs; full lane combinational logic and all state byte-identical modulo selector declaration insertion. Model bridges actual lane_eligible=>lane_exam. Full-module SAT not claimed.', 'proof_log':'onehot-v2-119681.log','proof_result':'direct SAT all outputs SUCCESS','hashes':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['loader-distributed-parallel-reviewed.sv','loader-onehot-v2.sv','onehot-select-gold.sv','onehot-v2-select-gate.sv','onehot-v2-direct.ys']}}
(p/'onehot-v2-binding.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r,indent=2))

