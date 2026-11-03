"""Append unchanged actual native-ground and input-load checks for new placements."""
from pathlib import Path
import ast,subprocess,shlex
s=Path(r'D:\Data\电路实验\control162-halo-bound-chain142.py').read_text();q=ast.literal_eval(ast.parse(s).body[2].value)
for a,b in [('s-ready-halo-bounds-source142','s-ready-internal-channel-bounds158'),('sready142-halo-native-cap-config','sready158-internal-channel-native-cap-config'),("'halo-cap-candidates'","'cap-capacity-candidates'"),('[1470,1471,1472]','[1580,1581,1582,1583]'),('source-142','source-157'),('halo-native-residual-01','internal-channel-native-residual-158'),('halo-native-pin-load-01','internal-channel-native-pin-load-158'),('00-t-sready142-halo-native-residual','00-j-sready158-internal-native-residual'),('00-u-sready142-halo-native-pin-load','00-j-sready158-internal-native-pin-load'),("f=b/'dynamic-03/node5/pending'/(name+'.json')","f=b/('dynamic-02/node3/pending' if 'residual'in name else 'dynamic-02/node6/pending')/(name+'.json')"),('three immutable-scene whitespace diagnostics','four actual internal-channel placements')]:
 assert a in q,a;q=q.replace(a,b)
compile(q,'new_placement_actual_bounds158','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
