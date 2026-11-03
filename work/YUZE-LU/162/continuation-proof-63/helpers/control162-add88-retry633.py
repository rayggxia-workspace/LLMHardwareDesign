import subprocess,shlex
q=r'''from pathlib import Path
import json,os
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'source-88';assert(root/'freeze-import.json').exists();base=b/'arbiter-setup-05';queue=b/'dynamic-03/node5'
def add(name,script,args,budget,requires=[],target=queue):
 p=target/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(dict(script=script,source_root=str(root),forecast_gib=budget,requires=list(map(str,requires)),args=list(map(str,args)))));os.rename(str(tmp),str(p))
producer=base/'candidate-45';gates=base/'gates-45'
add('00-k1-arbiter-physical','run.py',['--model','s_arbiter','--out',producer,'--physical','--repair-s-arbiter-data-escape','din[633]'],32)
add('00-k1-arbiter-system','run.py',['--model','system','--out',base/'system','--verify-only'],32,target=b/'dynamic-02/node6')
add('00-k2-arbiter-seal','gates.py',['seal','--producer',producer,'--out',gates/'seal','--source-root',root],16,[producer/'receipt.json'])
for op in ['physical','drc','function','formal']:
 deps=[gates/'seal/receipt.json']+([gates/'function/receipt.json']if op=='formal'else[])
 add('00-k3-arbiter-'+op,'gates.py',[op,'--producer',producer,'--out',gates/op,'--source-root',root,'--sealed',gates/'seal','--gates',gates],32,deps)
add('00-k4-arbiter-deliver','gates.py',['deliver','--producer',producer,'--out',gates/'deliver','--source-root',root,'--sealed',gates/'seal','--gates',gates],32,[gates/op/'receipt.json'for op in('physical','drc','function','formal')])
s=b/'composition-arbiter-07/selected';t=b/'composition-arbiter-07/topology'
add('00-k5-arbiter-select','select_leaves.py',['--physical',b/'composition-arbiter-04/selected/physical.json','--functions',b/'composition-arbiter-04/selected/functions.json','--replacement',gates/'deliver','--out',s],16,[gates/'deliver/receipt.json'])
add('00-k6-arbiter-topology','topology.py',['--manifest',s/'physical.json','--out',t],16,[s/'receipt.json'])
add('00-k7-arbiter-native-sta','system_sta.py',['--manifest',s/'physical.json','--functional-views',s/'functions.json','--topology',t/'topology.json','--graph',t/'boundary-graph.json','--out',b/'native-arbiter-sta-19','--stitch-native-access','--audit-native-coverage'],32,[s/'receipt.json',t/'boundary-graph.json'])
wrapper=b/'pg-arbiter-09/control_s_arbiter';checks=b/'pg-arbiter-checks-06/control_s_arbiter';delivery=b/'pg-arbiter-delivery-07/control_s_arbiter'
add('00-k8-arbiter-pg','pg_fixed_access.py',['--manifest',s/'physical.json','--leaf','control_s_arbiter','--out',wrapper],32,[s/'receipt.json'])
for mode in ['physical','timing']:
 args=['--wrapper',wrapper,'--manifest',s/'physical.json','--leaf','control_s_arbiter','--out',checks/mode]+(['--physical-only']if mode=='physical'else[])
 add('00-k9-arbiter-pg-'+mode,'pg_fixed_timing.py',args,32,[wrapper/'receipt.json'])
add('00-ka-arbiter-pg-deliver','pg_fixed_timing.py',['--wrapper',wrapper,'--manifest',s/'physical.json','--leaf','control_s_arbiter','--out',delivery,'--deliver','--physical-check',checks/'physical','--timing-check',checks/'timing'],32,[checks/mode/'receipt.json'for mode in['physical','timing']])
print('Queued continuously sampled write-mode arbiter: physical/RTL real system, four gates/sixfiles, topology, strict native RC and fixed-PG qualification.')
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
