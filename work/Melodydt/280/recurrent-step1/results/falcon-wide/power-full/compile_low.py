"""Reuse completed Verilator C++ generation, with an independently recorded -O0 build."""
from pathlib import Path
from hashlib import sha256
import json, shutil, subprocess, os

work = Path.cwd()
source = work if (work/'generation-receipt.json').exists() else work.parent / 'power-split'
generated = source / ('obj_generated' if source==work else 'obj_dir')
dest = work / 'obj_dir'
assert (generated / 'Vcalibrate_tb_classes.mk').is_file()
assert 'vm_classes_0' not in (generated / 'Vcalibrate_tb_classes.mk').read_text()

def digest(p):
    h = sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

for name in ('commands.txt', 'segments.json', 'calibrate_tb.sv'):
    assert digest(source/name) == digest(work/name), name
if source==work:
    gen=json.loads((work/'generation-receipt.json').read_text())
    assert '--trace-underscore' in gen['command']
    for p,h in gen['inputs'].items():assert digest(Path(p))==h,p
dest.mkdir(exist_ok=False)
manifest = {}
for p in sorted(generated.iterdir()):
    if p.suffix not in ('.cpp', '.h', '.mk'): continue
    shutil.copyfile(p, dest/p.name)
    before = digest(p)
    assert before == digest(dest/p.name)
    manifest[p.name] = before
assert len(manifest) > 100
os.environ['VERILATOR_ROOT'] = '/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
args = ['make', '-C', str(dest), '-f', 'Vcalibrate_tb.mk', '-j12',
        'OPT_FAST=-O0', 'OPT_SLOW=-O0', 'Vcalibrate_tb']
compiler = Path('/usr/bin/g++')
if os.environ.get('RECURRENT_COMPILER') == 'clang':
    clang_root=Path('/public/home/yuzelu/opt/eda/clang14-mdt-20261118')
    compiler=clang_root/'usr/bin/clang++-14'
    os.environ['LD_LIBRARY_PATH']=str(clang_root/'usr/lib/x86_64-linux-gnu')+':'+str(clang_root/'usr/lib/llvm-14/lib')
    args += ['CXX='+str(compiler), 'LINK='+str(compiler),
             'CFG_CXXFLAGS_COROUTINES=-std=c++20', 'CFG_CXXFLAGS_PCH_I=-include-pch',
             'CFG_GCH_IF_CLANG=.gch']
receipt = dict(method='same Verilator C++ files; make OPT_FAST=-O0 OPT_SLOW=-O0',
               generated_source=str(generated), generated_sha256=manifest, command=args,
               compiler_sha256=digest(compiler.resolve()),
               compiler_version=subprocess.check_output([str(compiler),'--version'],text=True).strip())
(work/'low-build-input.json').write_text(json.dumps(receipt, indent=2)+'\n')
with (work/'build.log').open('w') as f:
    subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, check=True)
paths = [work.parent/'mapped.v',
    Path('/public/home/yuzelu/project-circuit/issue250-p-final-native-diode-gate-GlrL0V/cells.v'),
    work/'commands.txt', work/'segments.json', work/'calibrate_tb.sv']
receipt = dict(inputs={str(p):digest(p) for p in paths},
               binary_sha256=digest(dest/'Vcalibrate_tb'),
               build_input_sha256=digest(work/'low-build-input.json'))
(work/'prebuilt-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('LOW_OPT_BUILD_PASS', flush=True)
