import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'r256-composition-453/upper-candidates/5120/route/trial-0/input.txt';names={'net_8396','net_8498','net_8324','net_8463','net_2','net_PG_VDD','net_PG_VSS'}
with p.open()as f:
 print('grid_header',f.readline().split()[:7])
 for line in f:
  v=line.split()
  if v[0]not in names:continue
  n=int(v[1]);ends=[(int(v[2+2*i]),int(v[3+2*i]))for i in range(n)];x=[a[0]for a in ends];y=[a[1]for a in ends];dx=max(x)-min(x);dy=max(y)-min(y);print(json.dumps(dict(net=v[0],ends=n,first=ends[:2],bbox=[min(x),min(y),max(x),max(y)],span_grid=[dx,dy],span_um=[dx*4,dy*4],ordinary64_box_node_upper=2*(dx+129)*(dy+129))))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
