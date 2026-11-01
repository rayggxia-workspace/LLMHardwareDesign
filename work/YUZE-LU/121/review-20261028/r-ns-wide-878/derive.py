from pathlib import Path
s=Path('.local/issue121/plan869.py').read_text(encoding='utf-8');exec(compile(s[:s.index('for i,m in enumerate(meta[\'markers\']):')],'869-setup','exec'))
boxes=[[3712660,1580530,3712860,1580670],[3712660,1580460,3712860,1580740],[3712660,1580320,3712860,1580880],[3712660,1580530,3712800,1580670],[3712660,1580460,3712800,1580740],[3712660,1580390,3712860,1580810]]
own=aliases['net131530'];coverage=[q for a,l,k,q in shapes[583]if a==own and l=='metal2'and not k.endswith('obstruction')];spacing=dimensions['metal2'][1];checks=[]
for i,box in enumerate(boxes):
 collisions=[]
 for a,l,k,q in shapes[583]:
  if a==own or l!='metal2':continue
  overlap=intersect(box,[q[0]-spacing,q[1]-spacing,q[2]+spacing,q[3]+spacing])
  if overlap and outside_area(coverage,overlap)>0:collisions.append(dict(alias=a,shape=k,bbox_dbu=q))
 checks.append(dict(case=i+3,bbox_dbu=box,added_area_dbu2=outside_area(coverage,box),collisions=collisions))
print(json.dumps(checks,indent=2));Path('.local/issue121/ns878-precheck.json').write_bytes((json.dumps(checks,indent=2)+'\n').encode())
