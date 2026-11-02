"""Recheck exact pinned tool sources after the isolated build, without editing them."""
from pathlib import Path
import argparse,hashlib,json,os,tarfile
from verify_slang_source import verify
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--archives',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
root=a.root.resolve();assert root.parent==Path('/public/home/yuzelu/opt/eda')and root.name.startswith('r166-openroad-gc-cache-')
build=json.loads((root/'BUILD_RECEIPT.json').read_text());sources=json.loads((root/'UPSTREAM_SOURCES.json').read_text());assert build['passed']and build['sources']==sources
binary=root/'install/bin/openroad';assert sha(binary)==build['binary_sha256']
rows=[]
for i,dest in enumerate(['source','source/src/sta','source/third-party/abc','source/third-party/slang-elab']):
 archive=a.archives/('upstream%d.tar.gz'%i);assert sha(archive)==sources[i]['archive_sha256'];digest=hashlib.sha256();count=0
 with tarfile.open(archive)as bundle:
  for member in bundle:
   parts=Path(member.name).parts[1:]
   if not parts:continue
   actual=root.joinpath(dest,*parts)
   if member.isfile():
    original=bundle.extractfile(member).read();expected=hashlib.sha256(original).hexdigest()
    if sha(actual)!=expected:
     assert i==0 and parts==('MODULE.bazel.lock',),str(actual)
     old=json.loads(original);new=json.loads(actual.read_text());assert new['registryFileHashes']=={}
     assert {k:v for k,v in old.items()if k!='registryFileHashes'}=={k:v for k,v in new.items()if k!='registryFileHashes'}
    digest.update(('/'.join(parts)+' '+expected+'\n').encode());count+=1
   elif member.issym():assert actual.is_symlink()and os.readlink(actual)==member.linkname
 row=dict(verified_files=count,path_and_sha256_digest=digest.hexdigest())
 assert all(build['source_files'][i][k]==v for k,v in row.items());rows.append(row)
slang=verify(root/'source-checkouts/sv-lang-f04e8156',root/'source-checkouts/sv-lang-proof');assert slang==build['slang_source']
assert sha(binary)==build['binary_sha256']
Path('TOOL_SOURCE_RECHECK.json').write_text(json.dumps(dict(passed=True,root=str(root),binary_sha256=sha(binary),build_receipt_sha256=sha(root/'BUILD_RECEIPT.json'),sources=sources,source_files=rows,slang_source=slang,script_sha256=sha(Path(__file__)),scope='Post-build exact source/archive/symlink and pinned Git-tree check; no tool or hardware edits or physical qualification'),indent=2)+'\n')
