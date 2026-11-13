"""Collect immutable compact DMA unit source/log/CSV receipts, no local RTL run."""
import argparse,hashlib,json,re,shlex,subprocess,tarfile
from pathlib import Path
HOST='yuzelu@10.129.166.172'
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--dest',type=Path,required=True);p.add_argument('--job',type=int,required=True);p.add_argument('--extract-dir',type=Path,required=True);a=p.parse_args();assert re.fullmatch('/public/home/yuzelu/project-circuit/issue250-dma-20261111-[0-9]+',a.root);a.dest.mkdir(parents=True,exist_ok=True);assert not a.extract_dir.exists()
 script='''import pathlib,hashlib,json,tarfile
r=pathlib.Path(ROOT)
if not(r/'receipts.tar.gz').exists():
 files=[p for p in r.rglob('*')if p.is_file()and 'obj'not in p.parts and 'tmp'not in p.parts and p.name not in('source.tar.gz','receipts-manifest.json','receipts.tar.gz')]
 manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files};(r/'receipts-manifest.json').write_text(json.dumps(manifest,indent=2)+'\\n')
 with tarfile.open(r/'receipts.tar.gz','w:gz')as tar:
  for p in files+[r/'receipts-manifest.json']:tar.add(p,arcname=str(p.relative_to(r)))
manifest=json.loads((r/'receipts-manifest.json').read_text())
for name,digest in manifest.items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest
print(json.dumps(dict(files=len(manifest),SHA256=hashlib.sha256((r/'receipts.tar.gz').read_bytes()).hexdigest(),bytes=(r/'receipts.tar.gz').stat().st_size)))
'''.replace('ROOT',repr(a.root))
 info=json.loads(subprocess.check_output(['ssh',HOST,'python3 -c '+shlex.quote(script)]));archive=a.dest/'receipts.tar.gz';subprocess.run(['scp','-q',HOST+':'+a.root+'/receipts.tar.gz',str(archive)],check=True);assert hashlib.sha256(archive.read_bytes()).hexdigest()==info['SHA256'];a.extract_dir.mkdir(parents=True)
 with tarfile.open(archive)as tar:
  for m in tar.getmembers():assert m.isfile()and not Path(m.name).is_absolute()and '..'not in Path(m.name).parts
  tar.extractall(a.extract_dir,filter='data')
 manifest=json.loads((a.extract_dir/'receipts-manifest.json').read_text())
 for name,digest in manifest.items():assert hashlib.sha256((a.extract_dir/name).read_bytes()).hexdigest()==digest
 info.update(remote_root=a.root,job=a.job,extract_dir=str(a.extract_dir),files_checked=len(manifest));(a.dest/'collection.json').write_text(json.dumps(info,indent=2)+'\n');(a.dest/'accounting.txt').write_bytes(subprocess.check_output(['ssh',HOST,f'sacct -j {a.job} --format=JobID,State,Elapsed,ExitCode,AllocCPUS,NodeList -P']));print(json.dumps(info))
if __name__=='__main__':main()
