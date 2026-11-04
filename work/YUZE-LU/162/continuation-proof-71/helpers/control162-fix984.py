from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-audit982-remote.py').read_text(encoding='utf-8').replace('r256-final-chain-binding-audit-982','r256-final-chain-binding-audit-984')
a=s.index("and route['args'][route['args'].index('--route-pin-access')+1]=='ordinary-first'");z=s.index("and route['forecast_gib']==64",a)
s=s[:a]+"and route['args'][route['args'].index('--route-pin-access')+1]=='none'and '--route-native-prefix-flexible'in route['args']and '--route-native-prefix-input'in route['args']and '--route-release-pin-reservations'not in route['args']and '--route-native-refresh'not in route['args']"+s[z:]
compile(s,'audit984','exec');(h/'control162-audit984-remote.py').write_text(s,encoding='utf-8')
s=(h/'control162-refill983-remote.py').read_text(encoding='utf-8').replace('r256-final-chain-binding-audit-982','r256-final-chain-binding-audit-984').replace('982 fourteen','984 fourteen');(h/'control162-refill983-remote.py').write_text(s,encoding='utf-8');print('984 uses actual warm options; failed982 retained')
