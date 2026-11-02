"""Build a pinned upstream checker; never patch rules or replace shared tools.

Upstream 94fe8d17/2eba27b2 caches immutable polygon corner membership.
The original checker remains running until independent controls/comparison pass.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tarfile

p=argparse.ArgumentParser();p.add_argument('--archives',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');p.add_argument('--build-existing',action='store_true');p.add_argument('--fetch-only',action='store_true');a=p.parse_args()
ROOT=a.root
assert ROOT.parent==Path('/public/home/yuzelu/opt/eda')and ROOT.name.startswith('r166-openroad-gc-cache-')
if not a.build_existing:ROOT.mkdir(exist_ok=False)
records=[]
sources=[
 ('The-OpenROAD-Project/OpenROAD','2eba27b2c602b3b1a8f0fdc7773a5387d58fddaa','source'),
 ('The-OpenROAD-Project/OpenSTA','509913b1398b36eda23caa1f1f380167465dceee','source/src/sta'),
 ('The-OpenROAD-Project/abc','d527cfab4ad731b767ea0a2be2021d920d3afece','source/third-party/abc'),
 ('povik/yosys-slang','82effc8d9541be69e1ed3ec44759a4449f5d9247','source/third-party/slang-elab')]
manifest=json.loads((a.archives/'MANIFEST.json').read_text())
for i,(repo,commit,dest)in enumerate(sources):
 url='https://codeload.github.com/'+repo+'/tar.gz/'+commit
 archive=a.archives/('upstream%d.tar.gz'%i)
 row=manifest[i];digest=hashlib.sha256(archive.read_bytes()).hexdigest()
 assert row['repository']==repo and row['commit']==commit and row['url']==url and row['sha256']==digest
 if a.build_existing:
  old=json.loads((ROOT/'UPSTREAM_SOURCES.json').read_text())[i]
  assert old==dict(repository=repo,commit=commit,url=url,archive_sha256=digest)
  records.append(old);continue
 target=ROOT/dest;target.mkdir(parents=True,exist_ok=True)
 links=[]
 with tarfile.open(archive)as bundle:
  for member in bundle:
   parts=Path(member.name).parts[1:]
   assert '..'not in parts and not Path(member.name).is_absolute()and not member.islnk(),member.name
   if not parts:continue
   path=target.joinpath(*parts)
   if member.isdir():path.mkdir(parents=True,exist_ok=True)
   elif member.issym():links.append((path,member.linkname))
   elif member.isfile():
    path.parent.mkdir(parents=True,exist_ok=True)
    with bundle.extractfile(member)as src,path.open('wb')as out:out.write(src.read())
    path.chmod(member.mode&0o777)
   else:raise AssertionError(member.name)
 for path,link in links:
  assert not Path(link).is_absolute()and(ROOT/'source')in(path.parent/link).resolve().parents
  path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(link)
 records.append(dict(repository=repo,commit=commit,url=url,archive_sha256=digest))
 (ROOT/'UPSTREAM_SOURCES.json').write_text(json.dumps(records,indent=2)+'\n')
 print('SOURCE_READY',repo,commit,flush=True)
if a.prepare_only:raise SystemExit(0)
env=os.environ.copy();env['BAZELISK_HOME']=str(ROOT/'bazelisk')
if not a.fetch_only:assert len(os.sched_getaffinity(0))>=16
cmd=['/usr/local/bin/bazelisk','--nosystem_rc','--nohome_rc','--output_user_root='+str(ROOT/'bazel-output'),
     'run','--//:platform=cli','--jobs=16','--local_resources=cpu=16',
     '--disk_cache='+str(ROOT/'disk-cache'),'--repository_cache='+str(ROOT/'repository-cache'),
     '//:install','--',str(ROOT/'install')]
if a.fetch_only:
 cmd=cmd[:cmd.index('run')]+['build','--nobuild','--//:platform=cli','--jobs=1',
      '--disk_cache='+str(ROOT/'disk-cache'),'--repository_cache='+str(ROOT/'repository-cache'),'//:openroad']
else:cmd.insert(cmd.index('//:install'),'--remote_cache=');cmd.insert(cmd.index('//:install'),'--nofetch')
label='FETCH'if a.fetch_only else'BUILD'
(ROOT/(label+'_COMMAND.json')).write_text(json.dumps(cmd,indent=2)+'\n')
with(ROOT/(label.lower()+'.log')).open('w')as log:
 result=subprocess.run(cmd,cwd=ROOT/'source',env=env,stdout=log,stderr=subprocess.STDOUT)
record={'passed':result.returncode==0,'exit':result.returncode,'sources':records,'command':cmd,
        'scope':'Pinned unmodified upstream tool build only; no hardware or DRC qualification.'}
binary=ROOT/'install/bin/openroad'
if binary.is_file():record['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
(ROOT/(label+'_RECEIPT.json')).write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(result.returncode)
