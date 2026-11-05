"""Full actual routes on source-bound measured-budget-clear placements."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-internal-channel-routes159.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('s-ready-internal-channel-openroad-source157.json','s-ready-clear-placement-openroad-source157.json'),('internal-channel-native-residual-158','clear-placement-native-residual-161'),('internal-channel-native-pin-load-158','clear-placement-native-pin-load-161'),('options=[(1590,3,1,valid[1580]),(1591,6,1,valid[1580])]','options=[(1630,3,1,valid[1621]),(1631,6,1,valid[1622])]'),("assert not any(next(r for r in pd['placements']if Path(r['placement']).name=='1580')['violations'].values())","assert all(not any(next(r for r in pd['placements']if Path(r['placement']).name==str(n))['violations'].values())for n in [1621,1622])"),('sready159internal-','sready163clear-'),('(5 if seed==1590 else 50)','5')]:
 assert a in q,a;q=q.replace(a,b)
anchor="required_base.append(pin/'receipt.json')"
extra="""replay=b/'route-selection-102/sready161-replay-verification.json'
rp=json.loads(replay.read_text());assert rp['passed']and len(rp['pairs'])==4
for pair in rp['pairs']:
 for name,digest in pair['source_receipts'].items():assert sha(name)==digest
required_base.append(replay)
"""
assert anchor in q;q=q.replace(anchor,anchor+'\n'+extra)
q=q.replace('Two actual235-instance/8990-net CUGR/TritonRoute candidates on new1580 actual internal-channel placement, effort5/50. Only1580 clears actual native-ground plus minimum input-pin bounds at all three corners;1581/82/83 rejected with2/1/29 high-corner violations',
 'Two actual235-instance/8990-net CUGR/TritonRoute candidates on1621/1622, measured native/pin placement budgets with clear-trial selection. Actual default replay and48 measured trial outputs byte-identical, actual native-ground/input-pin low/base/high bounds must all clear. Effort5 actual comparison, full seven stages each; original source157 routing/geometry/PG/RC300MHz acceptors unchanged. Source161 only generates new placement; its exact proof/receipts/trial bytes remain bound.')
compile(q,'actual_clear_placement_routes163','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
