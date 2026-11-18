from pathlib import Path
import json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-main-clock4-physical-v1');m=json.loads((p/'net-localization/all-parent-marker-nets.json').read_text());l=json.loads((p/'upper-localization.json').read_text())['markers'];o=[]
for x in m['markers']:
 a=l[x['id']]
 if a['macro_bbox_intersections']==['e_s32_pipeline_128']:continue
 row=dict(id=x['id'],category=a['category'],bbox_um=a['bbox'],macro=a['macro_bbox_intersections'],hits=x['hits']);o.append(row)
 print(row['id'],row['category'],row['bbox_um'],row['macro'],sorted(set((h['net'],h['kind']) for h in x['hits'])))
assert len(o)==22
(p/'non-dot-upper-net-candidates.json').write_text(json.dumps(o,indent=2))
