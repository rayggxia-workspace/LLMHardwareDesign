"""Recover immutable own-root native M receipts and selected deliverables, SHA checked."""
import argparse,hashlib,json,re,shlex,subprocess,tarfile
from pathlib import Path
HOST='yuzelu@10.129.166.172'
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--dest',type=Path,required=True);p.add_argument('--job',type=int,required=True);p.add_argument('--index-only',action='store_true');a=p.parse_args();assert re.fullmatch(r'/public/home/yuzelu/project-circuit/issue250-m-physical-20261111-\d+',a.root);a.dest.mkdir(parents=True,exist_ok=True)
 code='''import hashlib,json,pathlib,tarfile
root=pathlib.Path(ROOT);selected=[];allfiles={}
if (root/'receipts.tar.gz').exists() and (root/'receipts-manifest.json').exists():
 manifest=json.loads((root/'receipts-manifest.json').read_text())
 for name,digest in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
 print(json.dumps(dict(files=len(manifest),SHA256=hashlib.sha256((root/'receipts.tar.gz').read_bytes()).hexdigest(),all_files_hashed=len(json.loads((root/'all-files-manifest.json').read_text())))))
 raise SystemExit(0)
for p in root.rglob('*'):
 if not p.is_file()or any(x.startswith('tmp-')for x in p.relative_to(root).parts)or 'obj'in p.parts or p.name in('receipts.tar.gz','receipts-manifest.json','all-files-manifest.json'):continue
 relative=p.relative_to(root);allfiles[str(relative)]=dict(SHA256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
 if relative.parts[0]=='source'or p.suffix in('.json','.log','.rpt','.txt','.tcl','.sdc','.mk','.tsv','.sha256','.lyrdb','.ys','.py','.sh','.png')or p.name in('6_final.gds','6_final.odb','6_final.spef','6_final.def','6_final.v')and relative.parts[0]in('deliver','delivery'):selected.append(p)
(root/'all-files-manifest.json').write_text(json.dumps(allfiles,indent=2)+'\\n');selected.append(root/'all-files-manifest.json')
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in selected};(root/'receipts-manifest.json').write_text(json.dumps(manifest,indent=2)+'\\n')
with tarfile.open(root/'receipts.tar.gz','w:gz')as tar:
 for p in selected+[root/'receipts-manifest.json']:tar.add(p,arcname=str(p.relative_to(root)))
print(json.dumps(dict(files=len(selected),SHA256=hashlib.sha256((root/'receipts.tar.gz').read_bytes()).hexdigest(),all_files_hashed=len(allfiles))))
'''.replace('ROOT',repr(a.root))
 meta=json.loads(subprocess.check_output(['ssh',HOST,'python3 -c '+shlex.quote(code)]))
 if a.index_only:
  for remote,local in(('receipts-manifest.json','remote-files.json'),('all-files-manifest.json','all-files-manifest.json')):subprocess.run(['scp','-q',HOST+':'+a.root+'/'+remote,str(a.dest/local)],check=True)
  meta.update(remote_root=a.root,job=a.job,raw_archive_remote=a.root+'/receipts.tar.gz',raw_archive_bytes=int(subprocess.check_output(['ssh',HOST,'stat -c %s '+shlex.quote(a.root+'/receipts.tar.gz')])),raw_archive_tracked_in_git=False,recover_command='scp '+HOST+':'+a.root+'/receipts.tar.gz ./receipts.tar.gz',scope='Immutable original physical archive stays on authorized project storage; manifests retained per AGENTS.md; no claim of complete local extraction')
  (a.dest/'remote-index.json').write_text(json.dumps(meta,indent=2)+'\n');(a.dest/'accounting.txt').write_bytes(subprocess.check_output(['ssh',HOST,f'sacct -j {a.job} --format=JobID,State,Elapsed,ExitCode,AllocCPUS,NodeList -P']));print(json.dumps(meta));return
 archive=a.dest/'receipts.tar.gz';subprocess.run(['scp','-q',HOST+':'+a.root+'/receipts.tar.gz',str(archive)],check=True);assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['SHA256'];expanded=a.dest/'receipts';expanded.mkdir(exist_ok=False)
 with tarfile.open(archive)as tar:
  for m in tar.getmembers():assert m.isfile()and not Path(m.name).is_absolute()and '..'not in Path(m.name).parts
  tar.extractall(expanded,filter='data')
 manifest=json.loads((expanded/'receipts-manifest.json').read_text())
 for name,digest in manifest.items():assert hashlib.sha256((expanded/name).read_bytes()).hexdigest()==digest
 (a.dest/'accounting.txt').write_bytes(subprocess.check_output(['ssh',HOST,f'sacct -j {a.job} --format=JobID,State,Elapsed,ExitCode,AllocCPUS,NodeList -P']));meta.update(remote_root=a.root,job=a.job,files_checked=len(manifest));(a.dest/'collection.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
if __name__=='__main__':main()
