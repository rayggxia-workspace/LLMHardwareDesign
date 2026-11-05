"""Compact actual placement and unchanged necessary-bound progress."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-local-density-status165.py')
q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[1].value)
q=q.replace('range(1700,1705)','range(1960,1963)').replace('[1700,1701,1704]','[1960,1962]').replace('00-j-sready165-local-density-','00-j-sready196-strong-local-')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
p=Path(r'D:\Data\电路实验\control162-local-density-native-status166.py')
q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[1].value).replace('local-density-native-residual-165','strong-local-native-residual-196').replace('local-density-native-pin-load-165','strong-local-native-pin-load-196')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
