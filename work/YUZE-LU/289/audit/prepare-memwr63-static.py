from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-memwr63-static-v1';p.mkdir(exist_ok=False)
s=(r/'audit/c-static-greedy-models.py').read_text()
s=s.replace('C-v27-joint-e20-h30','C-v28-actual-i8-h50')
s=s.replace("t['strength']>m['strength']", "t['strength']!=m['strength']").replace(" and t['area']>m['area']",'')
# Cross-family changes belong only to the prequalified 59-plan; verify their
# exact pin semantics independently, never add them to greedy candidates.
s += '''
plan=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-v28-combined-size-plan.tsv')
rows=[line.split('\\t') for line in plan.read_text().splitlines()[1:]];assert len(rows)==59
for inst,a,b in rows:assert a in models and b in models and models[a]['pins']==models[b]['pins'] and b not in dont,(inst,a,b)
(p/'base59-function-proof.json').write_text(json.dumps(dict(passed=True,count=len(rows),plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),liberty_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),criterion='All 59 replacements are stateless and have identical actual per-pin direction/function/three-state signatures.'),indent=2))
'''
(p/'models.py').write_text(s)
