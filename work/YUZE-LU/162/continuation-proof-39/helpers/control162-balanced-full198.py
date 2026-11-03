"""Matched actual FastRoute/C++ routes; all seven original gates each."""
from pathlib import Path
import subprocess,shlex
home=Path(r'D:\Data\电路实验')
for kind in ['fast','cpp']:
 scope={}
 name='control162-fastroute-full177.py'if kind=='fast'else'control162-cpp-local-full185.py'
 s=(home/name).read_text(encoding='utf-8')
 if kind=='cpp':s=s.split("if __name__=='__main__':",1)[0]
 else:s=s.rsplit('\nprint(subprocess.check_output',1)[0]
 exec(compile(s,name,'exec'),scope);q=scope['q']
 oldseed,node,job,seed,record,prefix=(1770,3,95098,1980,'s-ready-balanced-fast-source172.json','sready198fast-')if kind=='fast'else(1850,6,95101,1981,'s-ready-balanced-cpp-source172.json','sready198cpp-')
 oldnode=4 if kind=='fast'else 2;oldjob=95391 if kind=='fast'else 95341
 pairs=[('s-ready-fastroute24phase-source172.json'if kind=='fast'else's-ready-cpp-localdensity-source172.json',record),
 ('local-density-native-residual-165','strong-local-native-residual-197'),('local-density-native-pin-load-165','strong-local-native-pin-load-197'),
 (f'options=[({oldseed},{oldnode},1,valid[1702])]',f'options=[({seed},{node},{1 if kind=="fast"else 4},valid[1970])]'),
 ('for n in [1702]','for n in [1970]'),('sready165-default-replay-verification.json','sready197-default-replay-verification.json'),
 (f'assert node=={oldnode}',f'assert node=={node}'),(f"('dynamic-05/node{oldnode}')",f"('dynamic-02/node{node}')"),
 (f'for node,job in [({oldnode},{oldjob})]',f'for node,job in [({node},{job})]'),
 ("b/'dynamic-05'/('node'+str(node))","b/'dynamic-02'/('node'+str(node))"),
 ('sready177fast-'if kind=='fast'else'sready185cpp-',prefix)]
 for a,b in pairs:
  assert a in q,(kind,a)
  q=q.replace(a,b)
 # Only the descriptive scope changes below; admissions and seven gates remain.
 start=q.index("scope='")+len('scope=');end=q.index("'",start+1)
 q=q[:start]+repr('Actual235-instance/8990-net matched1970 placement through original source172 '+kind+' kernel. Actual32 strong balanced placement cost oracles and default16 byte replay must pass, actual native-ground/minimum-pin low/base/high violations must all be zero before admission. Search-only congestion cost does not qualify hardware. Reuse exact original source172 physical acceptors and regression binding, all seven final geometry/PG/three-RC300MHz/delivery gates. Existing free own16CPU slot, no new node/cancellation/R/foreign changes; preserve all previous failures.')+q[end+1:]
 compile(q,'balanced_actual_full198_'+kind,'exec')
 print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
