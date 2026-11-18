from pathlib import Path
import re,json
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');audit=R/'audit'
gate=R/'cu/runs/C-v38-close-y640-h75/legalized.v'
actual=set(re.findall(r'^\s*([A-Z][A-Z0-9]*_X\d+)\s+\S+\s*\(',gate.read_text(),re.M))
covered=set()
for n in ['C-v28-cell-preflight','C-v29-cell-preflight','C-trace-AOI221X4-fixture','C-trace-additional-fixture']:
    covered.update(json.loads((audit/n/'receipt.json').read_text())['masters'])
missing=actual-covered;assert missing and 'OAI221_X4' not in actual
out=audit/'C-v38-all-master-fixture';out.mkdir()
old=audit/'C-trace-additional-fixture'
script=(old/'export.py').read_text()
script=script.replace("required={'AOI221_X1','BUF_X32'}",'required='+repr(missing))
script=script.replace("assert selected=={'AOI221_X1','BUF_X32'},selected",'assert selected==required,selected')
script=script.replace('C_TRACE_ADDITIONAL_ONLY','C_V38_REMAINING_MASTERS').replace('AOI221_X1 and BUF_X32 exploratory trace sizing masters','All remaining actual C-v38 standard-cell masters')
(out/'export.py').write_text(script)
(out/'run.sbatch').write_text((old/'run.sbatch').read_text().replace('C-trace-additional-fixture','C-v38-all-master-fixture'))
(out/'receipt.py').write_text((old/'receipt.py').read_text())
(out/'preliminary-inventory.json').write_text(json.dumps(dict(actual=sorted(actual),missing=sorted(missing),method='Lexical netlist inventory, final authoritative inventory is Yosys physical JSON in strict proof.'),indent=2))
print(json.dumps(sorted(missing)))
