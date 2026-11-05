"""Admit only corrected-tie source220 after actual221 passes all regressions."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-bidirectional-full219.py');scope={};exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],'prepare219','exec'),scope);q=scope['q']
for a,b in [('source-217','source-220'),('source217','source220'),('router-bidirectional-regression-218','router-bidirectional-regression-221'),('Actual218','Actual221'),('2190','2230'),('2191','2231'),('2192','2232'),('sready219bidir-','sready223bidir-')]:
 assert a in q,a;q=q.replace(a,b)
compile(q,'actual_corrected_bidirectional223','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
