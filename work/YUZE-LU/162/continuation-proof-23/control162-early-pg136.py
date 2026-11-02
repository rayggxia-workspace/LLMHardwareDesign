"""Append a physical-only PG computation from immutable actual S1350 geometry."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,os
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-136'
root=b/'s-escape-pg-compute-01/1350';assert not root.exists()
sealed=b/'s-escape-gates-01/1350/sealed';physical=sealed.parent/'physical';drc=sealed.parent/'drc'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for chunk in iter(lambda:f.read(16*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
assert json.loads((sealed/'receipt.json').read_text())['passed']and json.loads((physical/'receipt.json').read_text())['passed']
flow=json.loads((sealed/'final-source.json').read_text());assert flow['top']=='block_feed_s_macro'
files=flow['final_files'];assert set(files)=={'6_final.'+s for s in ['v','sdc','def','odb','spef']}
for row in files.values():assert sha(row['path'])==row['sha256']and Path(row['path']).stat().st_size==row['bytes']
gds=drc/'gds-flow/results/nangate45/bv1_block_feed_s_macro/base/6_final.gds'
assert gds.is_file()and(drc/'full-deck.log').exists(),'Actual complete GDS generation has not finished'
assert not(drc/'native-whole-drc.rpt').read_text().strip()
files=dict(files,**{'6_final.gds':dict(path=str(gds),sha256=sha(gds),bytes=gds.stat().st_size)})
root.mkdir(parents=True)
manifest=root/'candidate-inputs.json';out=root/'wrapper'
manifest.write_text(json.dumps(dict(leaves={'block_feed_s_macro':dict(final_files=files)},native_leaf_qualified=False,whole_system_qualified=False,
 scope='Immutable actual geometry inputs for early PG computation only; no selected/qualified native leaf inferred.'),indent=2))
binding=root/'input-binding.json';binding.write_text(json.dumps(dict(passed=True,metadata_only=True,native_leaf_qualified=False,whole_system_qualified=False,
 inputs={str(p):sha(p)for p in [sealed/'receipt.json',sealed/'final-source.json',physical/'receipt.json',drc/'native-whole-drc.rpt',drc/'gds.log',manifest]},
 file_sha256={r['path']:r['sha256']for r in files.values()},scope='Hash/size binding only. Full native/function/formal and all PG/system gates still mandatory.'),indent=2))
queue=b/'dynamic-05/node2';p=queue/'pending/00-a0-s1350-pg-compute136.json';assert not p.exists()and not out.exists()
spec=dict(script='pg_fixed_access.py',source_root=str(source),forecast_gib=64,requires=[str(binding),str(sealed/'receipt.json'),str(physical/'receipt.json')],
 args=['--manifest',str(manifest),'--leaf','block_feed_s_macro','--out',str(out)])
temp=p.with_suffix('.tmp');temp.write_text(json.dumps(spec));os.rename(str(temp),str(p))
record=b/'route-selection-102/s1350-early-pg-source136.json';assert not record.exists()
record.write_text(json.dumps(dict(time=time.time(),path=str(p),sha256=sha(p),spec=spec,input_binding_sha256=sha(binding),native_leaf_qualified=False,whole_system_qualified=False,
 reason='Existing pg_fixed_access is explicitly candidate computation and performs all native/GDS checks. Start it on exact immutable physical inputs while native function/strict LEC/GDS deck run. Candidate must later match all six accepted input bytes and be joined with genuinely qualified native receipts before any PG delivery; no acceptance bypass.'),indent=2))
print(json.dumps(dict(appended=1,out=str(out),scope='candidate PG computation only',manifest=str(manifest))))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
