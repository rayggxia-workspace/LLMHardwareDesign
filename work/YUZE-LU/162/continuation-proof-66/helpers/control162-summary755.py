from pathlib import Path
import json,time
h=Path(__file__).parent;p=sorted((h/'control162-watch734').glob('*.json'))[-1];d=json.loads(p.read_text(encoding='utf-8'));tags={'6920','6921','7200','7370','7371','6360','6361'}
print(json.dumps(dict(snapshot=str(p),age_seconds=time.time()-d['time'],active=len(d['active']),selected=[dict(candidate=r['root'].rsplit('/',1)[-1],progress=r['progress'],metric=r['latest_complete_initial16'])for r in d['rows']if r['root'].rsplit('/',1)[-1]in tags],failures=[dict(root=r['root'],failures=r['failures'])for r in d['rows']if r['failures']],receipts=[dict(root=r['root'],receipts=r['receipts'])for r in d['rows']if r['receipts']])))
