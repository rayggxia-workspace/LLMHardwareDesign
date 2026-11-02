"""Fail-closed reception of a completed exact-ODB whole-die native computation."""
from pathlib import Path
from itertools import zip_longest
import hashlib,json,re

def receive(source,odb):
 sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 r=json.loads((source/'receipt.json').read_text())
 assert r['passed']is True and r['native_drc_count']==0
 assert r['original_odb_sha256']==sha(odb)
 tool=r.get('checker')
 if tool:
  assert sha(Path(tool['binary']))==tool['binary_sha256']
  assert json.loads((source/'CHECKER_IDENTITY.json').read_text())==tool
  if tool['kind']=='pinned-unmodified-upstream':
   assert sha(source/'CHECKER_BUILD_RECEIPT.json')==tool['build_receipt_sha256']
   assert sha(source/'CHECKER_UPSTREAM_SOURCES.json')==tool['sources_sha256']
   build=json.loads((source/'CHECKER_BUILD_RECEIPT.json').read_text());sources=json.loads((source/'CHECKER_UPSTREAM_SOURCES.json').read_text())
   assert build['passed']is True and build['sources']==sources and build['binary_sha256']==tool['binary_sha256']
   assert sources[0]['repository']=='The-OpenROAD-Project/OpenROAD'and sources[0]['commit']=='2eba27b2c602b3b1a8f0fdc7773a5387d58fddaa'
  else:assert tool['kind']=='original-container'
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
  if tool and tool['kind']=='pinned-unmodified-upstream':
   original=source/(name+'-original.rpt');assert row['original_report_sha256']==sha(original)
   assert sorted(re.findall(r'^violation type: (.+)$',text,re.M))==sorted(re.findall(r'^violation type: (.+)$',original.read_text(),re.M))
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
 return dict(passed=True,receipt_sha256=sha(source/'receipt.json'),source=str(source),original_odb_sha256=sha(odb),geometry_identity_rechecked=True,negative_controls_received=True,native_drc_count=0,checker=tool)
