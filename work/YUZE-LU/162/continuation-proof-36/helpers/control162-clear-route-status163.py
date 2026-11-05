from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-openroad-scene156-status.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[2].value)
for seed,node in [(1630,3),(1631,6)]:
 s=q.replace('1513',str(seed)).replace('node2','node'+str(node)).replace('dynamic-05','dynamic-02').replace('sready156openroad','sready163clear')
 print('CANDIDATE',seed)
 print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(s)],timeout=45).decode())
