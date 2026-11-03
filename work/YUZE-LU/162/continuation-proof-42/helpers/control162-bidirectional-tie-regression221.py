"""Run exact search regression after correcting reduced-cost zero-score ties."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-bidirectional-regression218.py');scope={};exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],'prepare218','exec'),scope);q=scope['q']
for a,b in [('source-217','source-220'),('sready218-bidirectional-regression','sready221-bidirectional-regression'),('5c4e430003382ec22ce2591f014da025956f0109','3f92e73b66473d8b77367cb3ddc9de49dcb22657'),('router-bidirectional-regression-218','router-bidirectional-regression-221')]:
 assert a in q,a;q=q.replace(a,b)
compile(q,'actual_bidirectional_tie221','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
