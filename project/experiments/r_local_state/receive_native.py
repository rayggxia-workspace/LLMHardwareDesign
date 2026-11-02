"""Fail-closed reception of a completed exact-ODB whole-die native computation."""
from pathlib import Path
from itertools import zip_longest
import hashlib,json

def receive(source,odb):
 sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 r=json.loads((source/'receipt.json').read_text())
 assert r['passed']is True and r['native_drc_count']==0
 assert r['original_odb_sha256']==sha(odb)
 assert all(r[k]is True for k in ['original_source_unchanged','identical_geometry_and_connections','no_marker_or_rule_exclusions'])
 tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
 assert r['technology_sha256']==sha(tech)
 assert not(source/'complete.rpt').read_bytes()and r['native_report_sha256']==sha(source/'complete.rpt')
 expected={'positive':None,'short':'Short','spacing':'Metal Spacing','notch':'Metal Spacing'}
 assert set(r['controls'])==set(expected)
 for name,typ in expected.items():
  row=r['controls'][name];report=source/(name+'.rpt');text=report.read_text()
  assert row['passed']is True and row['expected']==typ and row['report_sha256']==sha(report)
  assert (not text.strip())if typ is None else('violation type: '+typ)in text
 assert sha(source/'before.def')==sha(source/'after.def')
 assert sha(source/'complete-before.def')==sha(source/'complete-after.def')
 def filtered(path,grid):
  for line in path.open('rb'):
   if line.startswith(b'GCELLGRID '):grid.append(line.decode().strip())
   else:yield line
 ga=[];gb=[];h=hashlib.sha256()
 for a,b in zip_longest(filtered(source/'before.def',ga),filtered(source/'complete-before.def',gb)):
  assert a is not None and a==b,'Physical DEF shape/connectivity mismatch';h.update(a)
 assert ga==r['before_grid']and gb==r['complete_grid']and len(gb)==2
 assert all(' DO 2 STEP 'in s for s in gb)and h.hexdigest()==r['non_grid_def_sha256']
 return dict(passed=True,receipt_sha256=sha(source/'receipt.json'),source=str(source),original_odb_sha256=sha(odb),geometry_identity_rechecked=True,negative_controls_received=True,native_drc_count=0)
