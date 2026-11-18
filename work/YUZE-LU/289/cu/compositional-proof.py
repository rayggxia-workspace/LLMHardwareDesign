"""Check the structural obligations supplementing select-proof.ys.

This certificate is separate from the still-running whole-module SAT proof.
No behavioral claim is based on an unproven or timed-out solver run.
"""
from pathlib import Path
import hashlib,json
import re
p=Path(__file__).parent
a=(p/'loader-original.sv').read_text();b=(p/'loader-parallel.sv').read_text()
def functions(s):return s[s.index(' function automatic [10:0] flat'):s.index(' // Search only finite')]
def sequential(s):return s[s.index(' always @(posedge clk)'):]
assert functions(a)==functions(b),'Lane evaluators changed'
assert sequential(a)==sequential(b),'State transitions changed'
header=a[:a.index(' always @* begin')]
assert b.startswith(header),'Ports, state, assigns, or declarations changed'
compact=lambda s:re.sub(r'\s+','',s)
default="candidate=0;hit=0;pad=0;waiting=0;cp=0;cl=0;cc=0;hc=0;address=0;free_owner=!pending[0]?0:1;"
assert compact(a).count(default)==1 and compact(b).count(default)==1,'Default values changed'
old_wait="(pending[0]&&lines[0]=={address[63:6],6'd0})||(pending[1]&&lines[1]=={address[63:6],6'd0})||(offer&&offer_address=={address[63:6],6'd0})"
assert 'waiting='+old_wait+';' in compact(a)
assert 'lane_wait[j]='+old_wait.replace('address[','lane_address[j][')+';' in compact(b)
assert "if(pad||hit||(!waiting&&pending!=3&&!offer))" in compact(a)
assert "if(!hit&&cv[c]&&ca[c]=={address[63:6],6'd0})beginhit=1;hc=3'(c);end" in compact(a)
assert "if(!lane_hit[j]&&cv[c]&&ca[c]=={lane_address[j][63:6],6'd0})beginlane_hit[j]=1;lane_hc[j]=3'(c);end" in compact(b)
assert 'reg[63:0]lane_address[0:7];' in compact(b)
assert 'reg[2:0]lane_hc[0:7],lane_cc[0:7];' in compact(b)
assert [(j//4,j%4) for j in range(8)]==[(q,l) for q in range(2) for l in range(4)]
assert 'if(!candidate&&pv[p]&&!pwriting[p]&&!pm[p][l])' in a
assert "lane_exam[j]=pv[j/4]&&!pwriting[j/4]&&!pm[j/4][j%4];" in b
assert "lane_address[j]=addr(pi[j/4],2'(j%4));" in b
assert "lane_pad[j]=is_pad(pi[j/4],2'(j%4));" in b
assert "lane_cc[j]=cache_index(pi[j/4],2'(j%4));" in b
for key in ['lane_eligible[j]=lane_exam[j]&&(lane_pad[j]||lane_hit[j]||(!lane_wait[j]&&pending!=3&&!offer));','if(lane_exam[j]&&!candidate)']:
 assert key in b
proof=p/'select-proof-recovery.log'
if not proof.exists():proof=p/'select-proof.log'
log=proof.read_text()
assert '77 are proven and 0 are unproven' in log and 'Equivalence successfully proven!' in log
sha=lambda x:hashlib.sha256(x).hexdigest()
result={'selector_formal_equivalence_bits':77,'pure_lane_evaluator_functions_byte_equal':True,'all_sequential_always_blocks_byte_equal':True,'ports_state_and_continuous_assigns_byte_equal':True,'lane_order_bijection':'j=4*p+l; p=0..1,l=0..3','scope':'Structural obligations plus arbitrary-input selector formal proof; whole-module SAT status is reported separately','original_sha256':sha(a.encode()),'parallel_sha256':sha(b.encode()),'selector_log_sha256':sha(proof.read_bytes()),'functions_sha256':sha(functions(a).encode()),'sequential_sha256':sha(sequential(a).encode())}
(p/'compositional-obligations.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
