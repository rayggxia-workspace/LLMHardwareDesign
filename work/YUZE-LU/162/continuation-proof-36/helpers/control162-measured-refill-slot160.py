"""Verify existing refill specs, then release one exact own duplicate child."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-internal-channel-preflight158.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[2].value)
for a,b in [("source=b/'source-157'","source=b/'source-160'"),('fbb61e6fb3e1bb7dbff94d3189c33420fe629690','7a02d7a8eae39733b4c43fcdcdfbb1d95e713df0'),('sready158-internal-channel-preflight','sready160-refill-slot1493-retired'),('[(3,95098,1432),(6,95101,1433)]','[(6,95101,1493)]'),("name='00-k-sready140-route-'","name='00-k-sready143cache-route-'"),("b/'source-140'","b/'source-143'"),("source-140/project/experiments","source-143/project/experiments")]:
 assert a in q,a;q=q.replace(a,b)
start=q.index(' for seed,gap in ');end=q.index('record.mkdir()',start);q=q[:start]+q[end:]
q=q.replace('Actual large-halo mature routes still hundreds of thousands of shorts; effort50 changes overflow only about3percent. Compare smaller density objective .35 with actual internal gaps64/256/512/1024 while retaining all native masks and209 Link8 rigid offsets. Replace only two verified own duplicate source140 searches; other identical placement controls and all three mature routes continue. No physical gate change, no parent/R/other task changes.',
 'Node6 currently has four actual running jobs including1591, so the earlier refill record wording free slot describes intended reuse, not an already idle slot. The two immutable short1610/1611 diagnostics are queued first. Verify and release only exact own source143 duplicate1493 to provide the second concurrent measured-budget placement slot, preserving other1420/1422/1424 controls, all five mature routes, parents, partial evidence and R/other tasks. No physical gate change.')
start=q.index('rows=[]\nfor f,spec,seed,gap in newtasks:');end=q.index("(record/'tasks.json')",start)
replacement="""refill=b/'route-selection-102/sready160-measured-placement-refill1610-1611.json';rd=json.loads(refill.read_text());rows=rd['tasks'];assert len(rows)==2
for row in rows:
 f=Path(row['spec']);assert sha(f)==row['spec_sha256'];assert json.loads(f.read_text())['source_root']==str(source)
"""
# Validate all replacement records before creating a ledger or cancelling.
pos=q.index('record.mkdir()');q=q[:pos]+replacement+q[pos:]
start=q.index('rows=[]\nfor f,spec,seed,gap in newtasks:');end=q.index("(record/'tasks.json')",start);q=q[:start]+q[end:]
compile(q,'exact_refill_slot1493_retirement','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
