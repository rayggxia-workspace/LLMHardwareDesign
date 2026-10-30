from pathlib import Path
import json,hashlib,subprocess
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(8388608),b''):h.update(c)
 return h.hexdigest()
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in Path('.').iterdir()if p.name in ('before.def','after.def','before.v','after.v','probe.odb','native-whole-drc.rpt')}
assert files['before.v']['sha256']==files['after.v']['sha256']
with Path('def-diff.txt').open('w')as f:
 result=subprocess.run(['diff','-u','before.def','after.def'],stdout=f);assert result.returncode in (0,1)
assert Path('def-diff.txt').stat().st_size<10000
Path('probe-result.json').write_text(json.dumps(dict(passed=True,netlist_unchanged=True,files=files,native_violations=Path('native-whole-drc.rpt').read_text().count('violation type:'),scope='Single additional same-net RECT on a disposable copy, geometrically contained by captured existing wire. Diagnostic only; all final gates remain required.'),indent=2)+'\n')
