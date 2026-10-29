from pathlib import Path
import json,hashlib,datetime
p=Path.cwd();source=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.def')
section=False;active=False;lines=[]
with source.open()as f:
 for line in f:
  if line.startswith('NETS '):section=True
  elif line.startswith('END NETS'):break
  if section and line.lstrip().startswith('- '):active=line.split()[1]=='clk'
  if active:
   lines.append(line)
   if line.rstrip().endswith(';'):break
assert lines and lines[0].split()[1]=='clk'
raw=''.join(lines).encode();(p/'clk-record.def').write_bytes(raw)
report=dict(passed=True,source_def=str(source),source_def_bytes=source.stat().st_size,source_def_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),clk_record_sha256=hashlib.sha256(raw).hexdigest(),clk_record_bytes=len(raw),rectangle_tokens=raw.count(b'RECT'),read_only=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(p/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
