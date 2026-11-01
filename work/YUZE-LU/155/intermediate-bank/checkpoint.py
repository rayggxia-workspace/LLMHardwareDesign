import pya
import json,hashlib,shutil
from pathlib import Path
out=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/checkpoint-002')
source=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-005/openram-temp/temp.gds')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(source)
target=out/'intermediate.gds';shutil.copyfile(source,target)
assert before==sha(source)==sha(target),'Producer changed the temporary GDS; snapshot rejected'
assert target.read_bytes()[-4:]==b'\x00\x04\x04\x00','Incomplete GDS stream'
layout=pya.Layout();layout.read(str(target))
tops=[dict(name=c.name,bbox_um=str(c.dbbox()))for c in layout.top_cells()]
view=pya.LayoutView();view.load_layout(str(target),0);view.max_hier();view.add_missing_layers();view.zoom_fit()
view.save_image(str(out/'intermediate.png'),1600,1000)
record=dict(scope='Intermediate generator checkpoint only; supply/pin routing and all DRC/LVS/timing/complete-S qualification remain pending',final=False,source=str(source),sha256=before,bytes=target.stat().st_size,dbu_um=layout.dbu,top_cells=tops,cells=layout.cells(),image_sha256=sha(out/'intermediate.png'))
(out/'checkpoint.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
