"""Refill the next released node4 slot with the shorter-wire qualified placement."""
from pathlib import Path
import subprocess,shlex

p=Path(r'D:\Data\电路实验\control162-cpp-local-full185.py');scope={}
exec(compile(p.read_text(encoding='utf-8').split("if __name__=='__main__':",1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('s-ready-cpp-localdensity-source172.json','s-ready-cpp-shortwire-source172.json'),('options=[(1850,2,1,valid[1702])]','options=[(1851,4,1,valid[1700])]'),('for n in [1702]','for n in [1700]'),('assert node==2','assert node==4'),("('dynamic-05/node2')","('dynamic-05/node4')"),('for node,job in [(2,95341)]','for node,job in [(4,95391)]'),('sready185cpp-','sready187cpp-')]:
    assert a in q,a;q=q.replace(a,b)
q=q.replace('Actual235-instance/8990-net C++ negotiated router1850 with16 independent single-thread trials inside one16CPU slot, reuses exactly the same native-ground/minimum-pin-bound-cleared1702 placement as1770 FastRoute.',
 'Actual235-instance/8990-net C++ negotiated router1851 with16 independent single-thread trials in one16CPU slot; actual1700 placement clears original native-ground/minimum-pin bounds at all three corners, summed HPWL15.59m versus18.08m of1702 while its local-density peak is higher. Compare shorter-wire placement1700 against lower-local-density1702 with exact same source172/kernel and all seven original full gates.')
q=q.replace('Waits for an existing node2 slot after181 diagnostic','Waits for the next released existing node4 slot')
compile(q,'actual_shortwire_cpp_full1851','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
