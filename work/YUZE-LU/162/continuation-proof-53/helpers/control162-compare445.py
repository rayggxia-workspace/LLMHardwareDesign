from pathlib import Path
import subprocess,shlex
q="""from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359/upper-candidates';out=b/'r256-controlled-priority-comparison-445';assert not out.exists();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for i in range(16):
 a=root/'4340/route'/('trial-'+str(i));c=root/'4390/route'/('trial-'+str(i));ai=a/'input.txt';ci=c/'input.txt'
 assert ai.read_bytes()==ci.read_bytes()
 def events(p):
  return [json.loads(x)for x in p.read_text().splitlines()if x.startswith('{')]
 ar=events(a/'router.log');cr=events(c/'router.log');az=[x for x in ar if x.get('round')==0 and 'conflict_nodes'in x];cz=[x for x in cr if x.get('round')==0 and 'conflict_nodes'in x]
 if az and cz:assert az==cz
 row=dict(trial=i,input_sha256=sha(ai),input_byte_identical=True,round0_complete_both=bool(az and cz),round0_identical=bool(az and cz),baseline_completed_rounds=[x for x in ar if 'conflict_nodes'in x],candidate_completed_rounds=[x for x in cr if 'conflict_nodes'in x],candidate_priority_checks=[x for x in cr if 'constrained_priority_prefix'in x],baseline_log_snapshot_sha256=sha(a/'router.log'),candidate_log_snapshot_sha256=sha(c/'router.log'))
 rows.append(row)
data=dict(captured_at=time.time(),rows=rows,round0_identical_count=sum(r['round0_identical']for r in rows),whole_system_qualified=False,scope='Actual separate processes. All16 routed input bytes identical (same4240 placement and RNG4340); only optional per-round constrained priority CLI differs. Complete original round0 metrics must match exactly before claiming a controlled later-round comparison. Live logs are captured prefixes; no route feasibility or whole-system qualification claim.')
out.mkdir();(out/'receipt.json').write_text(json.dumps(data,indent=2));print(json.dumps(dict(round0_identical_count=data['round0_identical_count'],candidate_max_complete_round=max([x['round']for r in rows for x in r['candidate_completed_rounds']]or[-1]),candidate_priority_rounds=sorted(set(x['round']for r in rows for x in r['candidate_priority_checks'])))))
"""
h=Path(__file__).parent;(h/'control162-compare445-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
