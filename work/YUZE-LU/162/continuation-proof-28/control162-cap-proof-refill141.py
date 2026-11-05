import subprocess,shlex
from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-capacity-refill140.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
q=q.replace('s-ready-capacity-refill-source140.json','s-ready-cap-proof141-refill-source140.json')
q=q.replace('[(1440,2,1420),(1441,2,1421),(1442,4,1420),(1443,4,1421),(1444,3,1422),(1445,25,1424),(1446,26,1420),(1447,26,1421),(1448,26,1422),(1449,26,1424)]','[(1450,4,1424),(1451,2,1424),(1452,4,1424),(1453,26,1424),(1454,26,1422)]')
q=q.replace('assert valid',r'''pin_receipt=base/'native-pin-load-01/receipt.json';pr=json.loads(pin_receipt.read_text());assert pr['passed']and pr['outputs']['native-pin-load.json']==sha(base/'native-pin-load-01/native-pin-load.json')
pin_report=json.loads((base/'native-pin-load-01/native-pin-load.json').read_text());allowed={int(Path(r['placement']).name)for r in pin_report['placements']if not any(r['violations'].values())};valid={n:p for n,p in valid.items()if n in allowed};assert set(valid)=={1420,1422,1424}''')
q=q.replace('\nrequired=required_base\n','\nrequired_base.append(pin_receipt)\nrequired=required_base\n')
q=q.replace('Ten additional independent seed searches for the same four cleared placements, plus60 downstream gates; dynamically fill existing own idle slots while original searches and all acceptance thresholds remain unchanged','Five independent seed searches for actual pin-bound-cleared placements1424/1422 and30 downstream gates; refill four exactly retired proven1421 searches and the completed read-only diagnostic slot. Same qualified hardware and unchanged final gates.')
assert '1454,26,1422'in q and 'required_base.append(pin_receipt)'in q
compile(q,'remote_append_only','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
