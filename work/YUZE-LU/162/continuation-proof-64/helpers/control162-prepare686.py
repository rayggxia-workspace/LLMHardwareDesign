from pathlib import Path
p=Path(__file__).parent;s=(p/'control162-watch662.py').read_text(encoding='utf-8')
s=s.replace("out=h/'control162-watch662'","out=h/'control162-watch686'")
s=s.replace('known={};prior=None;failure_floor=None',"known=json.loads(sorted((h/'control162-watch662').glob('*.json'))[-1].read_text())['known'];prior=None;failure_floor=None")
old="if sig!=prior:print(json.dumps(dict(event='cohort_or_gate_changed',snapshot=str(p),known_roots=len(known),active_steps=len(d['active']),changed=[r for r in sig if r['metric']or r['failures']or r['receipts']])),flush=True);prior=sig"
new="if sig!=prior:\n   changed=[r for r in sig if prior is None or r not in prior];print(json.dumps(dict(event='cohort_or_gate_changed',snapshot=str(p),known_roots=len(known),active_steps=len(d['active']),changed=[dict(seed=r['root'].rsplit('/',1)[-1],metric=r['metric'],failures=r['failures'],receipts=r['receipts'])for r in changed])),flush=True);prior=sig"
assert old in s;s=s.replace(old,new).replace('time.sleep(25)','time.sleep(45)');compile(s,'watch686','exec');(p/'control162-watch686.py').write_bytes(s.encode())
