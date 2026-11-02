import ast,subprocess,shlex
from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-capacity-upper140.py');tree=ast.parse(p.read_text(encoding='utf-8'))
# Execute the existing helper preparation only; preserve its remote call and
# every already queued task. This new record appends distinct seed searches.
prefix=p.read_text(encoding='utf-8').split("print(subprocess.check_output(",1)[0]
scope={};exec(compile(prefix,str(p),'exec'),scope);q=scope['q']
q=q.replace('s-ready-capacity-upper-source140.json','s-ready-capacity-refill-source140.json')
q=q.replace('assert node in (2,3,4,6)','assert node in (2,3,4,6,25,26)')
q=q.replace("(('dynamic-05/'if node in (2,4)else'dynamic-02/')+'node'+str(node))","(('dynamic-05/'if node in (2,4)else'dynamic-04/'if node==25 else'dynamic-02/')+'node'+str(node))")
q=q.replace('[(1430,2,1420),(1431,4,1421),(1432,3,1422),(1433,6,1424)]','[(1440,2,1420),(1441,2,1421),(1442,4,1420),(1443,4,1421),(1444,3,1422),(1445,25,1424),(1446,26,1420),(1447,26,1421),(1448,26,1422),(1449,26,1424)]')
q=q.replace('Four independent lower-density alternative routes and24 downstream gates','Ten additional independent seed searches for the same four cleared placements, plus60 downstream gates; dynamically fill existing own idle slots while original searches and all acceptance thresholds remain unchanged')
assert '1449,26,1424'in q and "node==25"in q
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
