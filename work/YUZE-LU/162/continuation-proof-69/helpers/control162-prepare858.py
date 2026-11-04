from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-audit835.py');s=p.read_text(encoding='utf-8-sig');s=s.replace('audit-835','audit-858').replace("old=b/'r256-endpoint-escape-regression-810';new=b/'r256-zero-maze-regression-829'","old=b/'r256-zero-maze-regression-829';new=b/'r256-native-prefix-regression-855'")
s=s.replace("len(w['cases'])==51 and len(w['rejected'])==27","len(w['cases'])==57 and len(w['rejected'])==35").replace('len(rows)==45','len(rows)==51')
s=s.replace(" if x['maze']:"," if x.get('native'):\n  assert p['native_prefix_proof']['frozen_prefix_matches_full_route']\n  assert p['distance_oracle']['independent_pin_access_matching_checks']==200\n if x['maze']and not x.get('native'):")
s=s.replace("oldsrc=b/'source-809/project/experiments/control_v1';newsrc=b/'source-828/project/experiments/control_v1'","oldsrc=b/'source-828/project/experiments/control_v1';newsrc=b/'source-854/project/experiments/control_v1'")
s=s.replace("'weighted_bidirectional.h']:","'weighted_bidirectional.h','ordinary_zero_maze.h']:")
s=s.replace('legacy45_byte_replays','legacy51_byte_replays').replace('weighted_cases=51','weighted_cases=57').replace('rejected_contexts=27','rejected_contexts=35').replace("b/'source-828/source-manifest.json'","b/'source-854/source-manifest.json'")
a=s.index("scope='Actual829");z=s.index("')\r\n",a)if "')\r\n"in s[a:]else s.index("')\n",a)
s=s[:a]+"scope='Actual855 complete57case regression,35 invalid/failing contexts including native-pass/global-fail. All51 disabled-default input/output/filtered logs match actual829 byte-for-byte.17 gate/resource/scene/prepass/pool/weighted headers, original exact class and finite-resource branch unchanged. Six native-first plus all/after-native pin cases pass independent full physical edge/occupancy/flood/wire checks and verify frozen prefix equality. Each binary additionally checks200 small neighbourhood matchings against an independent exhaustive oracle; original checks/replays retained. Reservations are search constraints, not emitted wires or a global feasibility proof. Actual full geometry/PG/3RC300MHz/system gates remain mandatory.'"+s[z+1:]
p=Path(r'D:\Data\电路实验\control162-audit858.py');p.write_bytes(s.encode());compile(s,str(p),'exec')
# Create full immutable seven-stage candidates, requiring actual regression and byte replay.
s=Path(r'D:\Data\电路实验\control162-queue829-remote.py').read_text(encoding='utf-8')
start=s.index('template=');s=s[start:]
s=s.replace('source-587','source-587').replace("[(8300,16384,'dynamic-02/node6'),(8301,65536,'dynamic-03/node5')]","[(8560,'all','dynamic-02/node6'),(8561,'after-native','dynamic-03/node5')]")
s=s.replace("['--route-weighted-bidirectional','--route-trace-phases','--route-ordinary-endpoint-escape','--route-ordinary-zero-maze',str(weight)]","['--route-weighted-bidirectional','--route-trace-phases','--route-ordinary-endpoint-escape','--route-ordinary-zero-maze','16384','--route-native-prefix-first','--route-pin-access',weight]")
s=s.replace("str(b/'r256-maze-legacy45-byte-audit-835/receipt.json')","str(b/'r256-maze-legacy45-byte-audit-858/receipt.json')").replace('sready829','sready855')
a=s.index("record.mkdir();");s=s[:a]+"record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Source854 default-off native-prefix-first, globally matched pin-access all/after-native, original finite-resource search and all final gates retained. All57cases/35negative plus51 actual byte replays required before fullscene admission. All16 active64attempts/16CPU/64GiB outer4GiB child, actual memory1.2+16 guard. Freeze native paths only after zero conflicts; native success is never full success. All selected original paths, failed attempts, raw sources retained. Node6 free slot after848/855; only own5451 node5 may be replaced after fresh identity guard.8 parents unchanged, c64 4x16/c96 6x16 dynamic refill. No system pass until all original7 stages independently pass.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[8560,8561])))\n"
pre="""from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-854';record=b/'route-selection-102/sready855-native-prefix-fullchains';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
assert (source/'freeze-import.json').exists()
def put(folder,name,spec):
 p=b/folder/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-native-prefix-regression-855'
"""
s=pre+s;compile(s,'queue856','exec');Path(r'D:\Data\电路实验\control162-queue856-remote.py').write_bytes(s.encode())
