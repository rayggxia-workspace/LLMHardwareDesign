"""Package only a physically qualified candidate, including bound raw evidence."""
from pathlib import Path
import hashlib,io,json,tarfile
q=Path('QUALIFICATION.json');d=json.loads(q.read_text());assert d['passed']and all(d['checks'].values())and d['candidate']in ['B256','B1024S']
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');trial=base/d['trial']
sources={}
for name,rec in d['artifacts'].items():sources['macro/'+Path(name).name]=(Path(name),rec['sha256'])
for index,(name,digest)in enumerate(d['evidence'].items()):sources[f'evidence/{index:02d}-'+Path(name).name]=(Path(name),digest)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for path,arc in [(q,'QUALIFICATION.json'),(trial/'BUNDLE.json','provenance/physical-source-BUNDLE.json'),(trial/'evaluation'/(d['candidate']+'-full-deck.lyrdb'),'evidence/full-original-GDS-deck.lyrdb')]:sources[arc]=(path,sha(path))
for path in (trial/'project/experiments/r_architecture').rglob('*'):
 if path.is_file():sources['source/'+str(path.relative_to(trial/'project/experiments/r_architecture'))]=(path,sha(path))
manifest={arc:dict(sha256=expected,bytes=path.stat().st_size)for arc,(path,expected)in sources.items()}
assert all(sha(path)==expected for path,expected in sources.values())
readme=f'''Small R-stream research macro {d['candidate']}, Issue157 / PR160.
{d['state_entries_per_bank']} S32 entries per bank, 2 banks, 8 arithmetic lanes.
128-bit state read: latency {d['read_latency_cycles']} cycles (0 means combinational).
Nangate45 M1-M10, die {d['die_um'][0]}x{d['die_um'][1]} um, frozen typical 300 MHz standalone constraints.
See QUALIFICATION.json for measured results, exact files, scope and checks.
macro/ contains final GDS, ODB, DEF, Verilog, SDC, SPEF, abstract LEF and typical Liberty.
source/ and provenance/ retain the exact physical source bundle; evidence/ retains actual checks.
This stream ISA is not a drop-in production R replacement; global swap/commit is external.
No M11/M12/system integration or multi-corner/foundry signoff is claimed.
'''
label='R-stream256'if d['candidate']=='B256'else'R-stream1024-sync'
archive=Path(label+'-nangate45-300MHz-'+d['trial']+'.tar.gz');assert not archive.exists()
with tarfile.open(archive,'w:gz',compresslevel=1)as tar:
 for arc,(path,_)in sources.items():tar.add(path,arcname=arc,recursive=False)
 for name,data in [('MANIFEST.json',(json.dumps(manifest,indent=2)+'\n').encode()),('README.txt',readme.encode())]:
  info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
# Actual archive readback, including every large physical file.
with tarfile.open(archive,'r:gz')as tar:
 for name,rec in manifest.items():
  f=tar.extractfile(name);h=hashlib.sha256()
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  assert h.hexdigest()==rec['sha256'],name
result=dict(passed=True,archive=str(archive.resolve()),bytes=archive.stat().st_size,sha256=sha(archive),members=len(manifest),archive_readback_verified=True,qualified_trial=d['trial'])
Path('PACKAGE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
