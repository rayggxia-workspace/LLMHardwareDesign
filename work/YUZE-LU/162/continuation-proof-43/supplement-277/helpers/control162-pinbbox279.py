import subprocess,shlex
q=r'''from pathlib import Path
import json,math
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');m=json.loads((b/'r256-composition-259/function-inputs/physical.json').read_text())
for top,row in m['leaves'].items():
 raw=json.loads(Path(row['pins']).read_text());pins=raw.get('pins',raw);coords=[]
 for pin in pins:
  if not isinstance(pin,dict):continue
  if 'xy_um'in pin:x,y=pin['xy_um']
  elif 'box_dbu'in pin:box=pin['box_dbu'];x,y=(box[0]+box[2])/4000,(box[1]+box[3])/4000
  else:continue
  coords.append((x,y))
 if coords:
  dx=max(v[0]for v in coords)-min(v[0]for v in coords);dy=max(v[1]for v in coords)-min(v[1]for v in coords);print(top,'pins',len(coords),'die',row['die_um'],'pin_bbox',round(dx,3),round(dy,3),'2layer_bbox_boundary_upper',math.ceil(dx/4+dy/4+4)*4)
 else:print(top,'schema-keys',list(raw)[:8])
'''
compile(q,'pinbbox279','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
