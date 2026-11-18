from pathlib import Path
import pya,json,hashlib
p=Path.cwd();r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');reference=r/'audit/C-v28-cell-preflight';prior=json.loads((reference/'receipt.json').read_text());assert prior['passed'] and prior['count']==0
plan=[s.split('\t') for s in (p/'plan.tsv').read_text().splitlines()[1:]]+[s.split('\t') for s in (r/'cu/c-v28-combined-size-plan.tsv').read_text().splitlines()[1:]]
masters={x[2] for x in plan};assert 'OAI221_X4' not in masters
needed=sorted(masters-set(prior['masters']));lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds');sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest();assert sha(lib)=='7fdbd7f4e46283fdd9b9a369e1cae1a7f6f742c8e75cfe943c17f451626fe8e8'
result=dict(all_planned_new_masters=sorted(masters),already_qualified=sorted(masters&set(prior['masters'])),additional_masters=needed,reference_receipt_sha256=sha(reference/'receipt.json'),source_gds_sha256=sha(lib),scope='Isolated original standard-cell fixture only; no parent layout qualification.')
if needed:
 l=pya.Layout();l.read(str(lib));top=l.create_cell('MEMWR63_ADDITIONAL_STANDARD_CELLS');pitch=round(100/l.dbu)
 for i,n in enumerate(needed):
  c=l.cell(n);assert c is not None;b=c.bbox();assert b.width()<pitch//2 and b.height()<pitch//2
  top.insert(pya.CellInstArray(c.cell_index(),pya.Trans((i%8)*pitch-b.left,(i//8)*pitch-b.bottom)))
 options=pya.SaveLayoutOptions();options.select_cell(top.cell_index());l.write(str(p/'additional-fixture.gds'),options);result['fixture_sha256']=sha(p/'additional-fixture.gds')
(p/'fixture-binding.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
