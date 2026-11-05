import ast,subprocess,shlex,sys
from pathlib import Path
seed=int(sys.argv[1]);source=int(sys.argv[2]);assert (seed,source)in [(1340,134),(1350,135),(1350,136),(1350,137)]
for name in ['control162-queue-S-composition121.py','control162-S-residual121.py']:
 t=ast.parse((Path(r'D:\Data\电路实验')/name).read_text())
 q=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='q'for a in n.targets))
 q=q.replace('1182',str(seed)).replace('1212',str(seed+2)).replace('source-121','source-'+str(source)).replace('source121','source'+str(source)).replace('config121','config'+str(source))
 family={136:'02',137:'03'}.get(source,'01')
 q=q.replace('s-internal-qualified-02','s-escape-qualified-'+family).replace('s-internal-composition-01','s-escape-composition-'+family)
 if source in (136,137):q=q.replace('s1350','s1350-fast'+str(source))
 compile(q,'new-S-actual-composition','exec')
 print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
