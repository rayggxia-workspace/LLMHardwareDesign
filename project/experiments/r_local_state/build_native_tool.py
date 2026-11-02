"""Build a pinned upstream checker; never patch rules or replace shared tools.

Upstream 94fe8d17/2eba27b2 caches immutable polygon corner membership.
The original checker remains running until independent controls/comparison pass.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tarfile

p=argparse.ArgumentParser();p.add_argument('--archives',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');p.add_argument('--build-existing',action='store_true');p.add_argument('--fetch-only',action='store_true');p.add_argument('--svlang-checkout',type=Path);p.add_argument('--svlang-proof',type=Path);a=p.parse_args()
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
  if not a.fetch_only:
   checked=0;binding=hashlib.sha256();generated=[]
   with tarfile.open(archive)as bundle:
    for member in bundle:
     parts=Path(member.name).parts[1:]
     if not parts:continue
     actual=ROOT.joinpath(dest,*parts)
     if member.isfile():
      with bundle.extractfile(member)as src:original=src.read();expected=hashlib.sha256(original).hexdigest()
      assert actual.is_file();actual_sha=hashlib.sha256(actual.read_bytes()).hexdigest()
      if actual_sha!=expected:
       # Bazel removes HTTPS registry hashes when consuming an exact local
       # registry. Only this generated bookkeeping difference is allowed;
       # module extensions, versions, source and all build rules stay exact.
       assert i==0 and parts==('MODULE.bazel.lock',),('Upstream source changed',str(actual))
       old_lock=json.loads(original);new_lock=json.loads(actual.read_text())
       assert new_lock['registryFileHashes']=={}
       assert {k:v for k,v in old_lock.items()if k!='registryFileHashes'}=={k:v for k,v in new_lock.items()if k!='registryFileHashes'}
       generated.append(dict(path='/'.join(parts),original_sha256=expected,generated_sha256=actual_sha,change='Bazel local-registry bookkeeping: empty registryFileHashes; all other lock fields identical'))
      binding.update(('/'.join(parts)+' '+expected+'\n').encode());checked+=1
     elif member.issym():assert actual.is_symlink()and os.readlink(actual)==member.linkname
   proof=ROOT/('SOURCE_FILES_%d.json'%i)
   proof.write_text(json.dumps(dict(repository=repo,commit=commit,archive_sha256=digest,verified_files=checked,path_and_sha256_digest=binding.hexdigest(),generated_metadata=generated),indent=2)+'\n')
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
assert bool(a.svlang_checkout)==bool(a.svlang_proof)
slang=None
if a.svlang_checkout:
 from verify_slang_source import verify
 assert ROOT in a.svlang_checkout.resolve().parents and ROOT in a.svlang_proof.resolve().parents
 slang=verify(a.svlang_checkout,a.svlang_proof)
env=os.environ.copy();env['BAZELISK_HOME']=str(ROOT/'bazelisk')
if not a.fetch_only:assert len(os.sched_getaffinity(0))>=16
cmd=['/usr/local/bin/bazelisk','--nosystem_rc','--nohome_rc','--host_jvm_args=-Djava.net.preferIPv4Stack=true','--output_user_root='+str(ROOT/'bazel-output'),
     'run','--//:platform=cli','--jobs=16','--local_resources=cpu=16',
     '--disk_cache='+str(ROOT/'disk-cache'),'--repository_cache='+str(ROOT/'repository-cache'),
     '//:install','--',str(ROOT/'install')]
if a.fetch_only:
 cmd=cmd[:cmd.index('run')]+['build','--nobuild','--//:platform=cli','--jobs=1',
      '--disk_cache='+str(ROOT/'disk-cache'),'--repository_cache='+str(ROOT/'repository-cache'),'//:openroad']
else:cmd.insert(cmd.index('//:install'),'--remote_cache=');cmd.insert(cmd.index('//:install'),'--nofetch')
if(ROOT/'registry').is_dir():cmd.insert(cmd.index('//:openroad')if a.fetch_only else cmd.index('//:install'),'--registry=file://'+str(ROOT/'registry'))
target='//:openroad'if a.fetch_only else'//:install'
cmd.insert(cmd.index(target),'--experimental_scale_timeouts=10.0')
if a.svlang_checkout:cmd.insert(cmd.index(target),'--override_repository=sv-lang+='+str(a.svlang_checkout))
label='FETCH'if a.fetch_only else'BUILD'
(ROOT/(label+'_COMMAND.json')).write_text(json.dumps(cmd,indent=2)+'\n')
with(ROOT/(label.lower()+'.log')).open('w')as log:
 result=subprocess.run(cmd,cwd=ROOT/'source',env=env,stdout=log,stderr=subprocess.STDOUT)
record={'passed':result.returncode==0,'exit':result.returncode,'sources':records,'command':cmd,
        'scope':'Pinned unmodified upstream tool build only; no hardware or DRC qualification.'}
record['build_attempt']=str(Path.cwd())
if slang:
 assert verify(a.svlang_checkout,a.svlang_proof)==slang
 record['slang_source']=slang
if not a.fetch_only:record['source_files']=[json.loads((ROOT/('SOURCE_FILES_%d.json'%i)).read_text())for i in range(len(sources))]
binary=ROOT/'install/bin/openroad'
if binary.is_file():record['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
(ROOT/(label+'_RECEIPT.json')).write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(result.returncode)
