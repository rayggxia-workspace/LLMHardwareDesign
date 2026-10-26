"""Build the pinned unmodified standalone solver; test against its FD goldens.

Invoked only inside an allocated compute worker. No downloaded build scripts run.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ARCHIVE_SHA='b2eaefce378aba09cccb966b3c56486412f1958e0a83ff3fb313fd35b3dfe2a7'
COMMIT='6ea4ca224f3589dd91809933f50f39af66053634'


def build(root,out,cpus,run):
    archive=root.parent/'fsv-source.tar'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==ARCHIVE_SHA
    prefix=Path('/public/home/yuzelu/opt/eda')/('llhd-fsv-i121-'+root.parent.name)
    prefix.mkdir(exist_ok=False)
    with tarfile.open(archive)as tar:
        names=tar.getnames()
        assert len(names)==54 and len(set(names))==54
        for member in tar.getmembers():
            path=Path(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
        tar.extractall(prefix)
    manifest=json.loads((prefix/'source-manifest.json').read_text())
    assert manifest['commit']==COMMIT and len(manifest['files'])==53
    for entry in manifest['files']:
        data=(prefix/entry['path']).read_bytes()
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
    compiler=Path(shutil.which('g++')).resolve()
    compiler_sha=hashlib.sha256(compiler.read_bytes()).hexdigest()
    run([str(compiler),'--version'],'compiler.log')
    flags=['-std=c++20','-O3','-pthread','-I'+str(prefix/'src/fsv/include'),
           '-I'+str(prefix/'src/fsv/src'),'-I'+str(prefix/'src/fsv/test/cpp')]
    sources=sorted((prefix/'src/fsv/src').glob('*.cpp'))
    assert len(sources)==16
    sources += [prefix/'src/fsv/test/cpp/Structures.cpp',root/'project/experiments/block_v1/fsv_client.cpp']
    objects=[]
    def compile(source):
        obj=prefix/(source.stem+'.o')
        run([str(compiler),*flags,'-c',str(source),'-o',str(obj)],'compile-'+source.stem+'.log')
        return obj
    with concurrent.futures.ThreadPoolExecutor(max_workers=cpus)as pool:
        objects=list(pool.map(compile,sources))
    binary=prefix/'llhd-fsv'
    run([str(compiler),'-pthread',*map(str,objects),'-o',str(binary)],'link.log')
    # The author's parser resolves golden data relative to the working directory.
    # We copy immutable source data to this task directory, keeping install intact.
    shutil.copytree(prefix/'src/fsv/test/golden',out/'src/fsv/test/golden')
    assert cpus>=2
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        futures=[pool.submit(run,[str(binary),mode,str(cpus//2)],mode+'.jsonl')
                 for mode in ['golden2d','golden3d']]
        for future in futures:future.result()
    run([str(binary),'determinism',str(cpus)],'determinism.jsonl')
    record=dict(schema='block-v1-fsv-qualified/1',upstream_commit=COMMIT,
                upstream_archive_sha256=ARCHIVE_SHA,compiler=str(compiler),compiler_sha256=compiler_sha,
                flags=flags,binary=str(binary),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                tests=['9 2D master rows: upstream planar/conformal FD reference bounds',
                       '6 3D master rows: upstream crossing/end FD reference bounds',
                       'fixed walks: thread invariance and epsilon linear scaling'],
                scope='Standalone reference solver subset; not integrated OpenROAD extraction or process signoff')
    (out/'fsv-qualified.json').write_text(json.dumps(record,indent=2)+'\n')

