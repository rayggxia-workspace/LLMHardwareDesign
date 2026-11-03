from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-placement-replay-verify161.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[2].value)
q=q.replace('[(1580,1604),(1602,1620),(1610,1621),(1611,1622)]','[(1580,1704)]').replace('len(rows)==4','len(rows)==1').replace('sready161-replay-verification.json','sready165-default-replay-verification.json')
compile(q,'default_replay_exact166','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
