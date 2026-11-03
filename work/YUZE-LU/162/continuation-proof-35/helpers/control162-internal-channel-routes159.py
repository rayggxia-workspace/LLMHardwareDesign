"""Admit only the actual three-corner pin-bound-cleared new placement."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-openroad-route156.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
changes={"source=b/'source-156'":"source=b/'source-157'","source='source-156'":"source='source-157'",'s-ready-openroad-source156.json':'s-ready-internal-channel-openroad-source157.json','halo-native-residual-02':'internal-channel-native-residual-158','halo-native-pin-load-02':'internal-channel-native-pin-load-158',"options=[(1513,2,1,valid[1470])]":"options=[(1590,3,1,valid[1580]),(1591,6,1,valid[1580])]",'router-openroad-preflight-156':'router-openroad-effort-preflight-157','assert node==2':'assert node in (3,6)',"('dynamic-05/node2')":"('dynamic-02/node'+str(node))",'sready156openroad-':'sready159internal-',"'--route-trials',1,'--router','openroad'":"'--route-trials',1,'--router','openroad','--openroad-congestion-iterations',(5 if seed==1590 else 50)"}
for a,b in changes.items():
 assert a in q,a;q=q.replace(a,b)
start=q.index("import subprocess\nstate=json.loads((b/'dynamic-05/node2/queue-state.json')")
end=q.index('required_base.append(regression)',start)
q=q[:start]+'''pin=base/'internal-channel-native-pin-load-158';pr=json.loads((pin/'receipt.json').read_text());assert pr['passed']and pr['outputs']['native-pin-load.json']==sha(pin/'native-pin-load.json')
pd=json.loads((pin/'native-pin-load.json').read_text());assert not any(next(r for r in pd['placements']if Path(r['placement']).name=='1580')['violations'].values())
required_base.append(pin/'receipt.json')
import subprocess
for node,job in [(3,95098),(6,95101)]:
 state=json.loads((b/'dynamic-02'/('node'+str(node))/'queue-state.json').read_text());assert len(state['active'])<=3
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and ('NodeList=node'+str(node)+' ')in details
'''+q[end:]
q=q.replace('One actual235-instance/8990-net CUGR/TritonRoute candidate on existing1470 exact qualified halo placement','Two actual235-instance/8990-net CUGR/TritonRoute candidates on new1580 actual internal-channel placement, effort5/50. Only1580 clears actual native-ground plus minimum input-pin bounds at all three corners;1581/82/83 rejected with2/1/29 high-corner violations')
compile(q,'actual_internal_channel_routes159','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
