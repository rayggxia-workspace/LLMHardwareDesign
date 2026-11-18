from pathlib import Path
import re,json,hashlib,pya
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=Path.cwd()
plan=r/'cu/c-v28-combined-size-plan.tsv'
prior=r/'audit/C-v28-cell-preflight/receipt.json'
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[plan,prior,lib,Path(__file__)];before={str(p):sha(p) for p in files}
assert sha(lib)=='7fdbd7f4e46283fdd9b9a369e1cae1a7f6f742c8e75cfe943c17f451626fe8e8'
rows=[x.split('\t') for x in plan.read_text().splitlines()[1:]];assert len(rows)==59 and len({x[0] for x in rows})==59
prior_receipt=json.loads(prior.read_text());assert prior_receipt['passed'] and prior_receipt['count']==0
for name,h in prior_receipt['files_sha256'].items():assert sha(Path(name))==h
required={'AOI221_X4'}
assert 'OAI221_X4' not in required
selected=required-set(prior_receipt['masters']);assert selected=={'AOI221_X4'},selected
changed={'frozen_59_size_plan':rows,'new_buffer_hold_masters_declared_by_CU':['CLKBUF_X1','BUF_X8','BUF_X16'],'required':sorted(required),'prior_covered':sorted(required&set(prior_receipt['masters']))}
layout=pya.Layout();layout.read(str(lib));cells={c.name:c for c in layout.each_cell()}
missing=selected-cells.keys();assert not missing, ('Changed non-library master requires separate review',missing)
assert selected and 'OAI221_X4' not in selected
top=layout.create_cell('C_TRACE_AOI221X4_ONLY');placements=[]
pitch=round(100/layout.dbu)
for i,name in enumerate(sorted(selected)):
 c=cells[name];box=c.bbox();assert box.width()<pitch//2 and box.height()<pitch//2
 x=(i%8)*pitch-box.left;y=(i//8)*pitch-box.bottom
 top.insert(pya.CellInstArray(c.cell_index(),pya.Trans(x,y)))
 placements.append(dict(master=name,translation_dbu=[x,y],bbox_dbu=str(box)))
options=pya.SaveLayoutOptions();options.select_cell(top.cell_index());target=out/'fixture.gds';layout.write(str(target),options)
# Readback every recursive layer union, hierarchy placements, and text geometry are
# retained by copying original cells unchanged; fixture adds translation refs only.
check=pya.Layout();check.read(str(target));ct=check.top_cell();assert ct.name==top.name
assert len(list(ct.each_inst()))==len(selected)
for name in selected:
 a=cells[name];b=check.cell(name);assert b is not None
 for li in layout.layer_indexes():
  info=layout.get_info(li);other=check.find_layer(info.layer,info.datatype)
  aa=pya.Region(a.begin_shapes_rec(li))
  bb=pya.Region(b.begin_shapes_rec(other)) if other is not None else pya.Region()
  assert (aa^bb).is_empty(), (name,str(info))
assert before=={str(p):sha(p) for p in files}
(out/'export-binding.json').write_text(json.dumps(dict(scope='AOI221_X4 exploratory trace sizing master; translation-only separated original-library fixture. New hold/buffer implementation remains subject to final inventory audit.',inputs_sha256=before,changed_instances=changed,masters=sorted(selected),placements=placements,gds_sha256=sha(target),recursive_material_readback_exact=True),indent=2))
print(json.dumps(dict(master_count=len(selected),masters=sorted(selected)),indent=2))
