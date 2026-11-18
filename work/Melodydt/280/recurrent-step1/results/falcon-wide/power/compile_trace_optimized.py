"""Optimize generated trace update functions only, retaining exact gate/driver source."""
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
import json,os,shlex,shutil,subprocess,sys

work=Path.cwd()
source=work.parent/'power-full'
obj=source/'obj_dir'
dest=work/'obj_dir'
dest.mkdir(exist_ok=False)
def digest(path):
    h=sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
old=json.loads((source/'low-build-input.json').read_text())
prior=json.loads((source/'prebuilt-receipt.json').read_text())
logic_from=Path(sys.argv[2]).resolve() if len(sys.argv)==3 and sys.argv[1]=='--logic-from' else None
archive_source=obj/'Vcalibrate_tb__ALL.a'
if logic_from:
    assert logic_from.parent==work.parent and logic_from!=work
    for filename in ('low-build-input.json','prebuilt-receipt.json'):
        shutil.copyfile(logic_from/filename,work/('prior-trace-'+filename))
    trace_build=json.loads((logic_from/'low-build-input.json').read_text())
    trace_binary=json.loads((logic_from/'prebuilt-receipt.json').read_text())
    assert trace_build['generated_sha256']==old['generated_sha256']
    assert trace_binary['build_input_sha256']==digest(logic_from/'low-build-input.json')
    assert trace_binary['binary_sha256']==digest(logic_from/'obj_dir/Vcalibrate_tb')
    archive_source=logic_from/'obj_dir/Vcalibrate_tb__ALL.a'
assert prior['build_input_sha256']==digest(source/'low-build-input.json')
assert prior['binary_sha256']==digest(obj/'Vcalibrate_tb')
for p,h in prior['inputs'].items():assert digest(p)==h
for name in ('commands.txt','segments.json','calibrate_tb.sv'):
    assert digest(source/name)==digest(work/name)
for name,h in old['generated_sha256'].items():assert digest(obj/name)==h
clang=Path('/public/home/yuzelu/opt/eda/clang14-mdt-20261118/usr/bin/clang++-14')
assert digest(clang.resolve())==old['compiler_sha256']
base=clang.parents[1]
os.environ['LD_LIBRARY_PATH']=str(base/'lib/x86_64-linux-gnu')+':'+str(base/'lib/llvm-14/lib')
commands=[];pch=None
for line in (source/'build.log').read_text().splitlines():
    if not line.startswith(str(clang)+' '):continue
    args=shlex.split(line)
    if '-o' not in args:continue
    output=args[args.index('-o')+1]
    if output=='Vcalibrate_tb__pch.h.fast.gch':pch=args
    is_trace='__Trace__' in output
    is_fast='-include-pch' in args and args[args.index('-include-pch')+1].endswith('.fast.gch')
    if output.endswith('.o') and is_fast and (not is_trace if logic_from else is_trace):commands.append(args)
assert pch and len(commands)>500
def replace(args):
    args=list(args)
    assert '-O0' in args
    args[args.index('-O0')]='-O1'
    args[args.index('-o')+1]=str(dest/args[args.index('-o')+1])
    if '-include-pch' in args:args[args.index('-include-pch')+1]=str(dest/'Vcalibrate_tb__pch.h.fast.gch')
    return args
manifest=dict(method='Identical generated C++; trace update functions only -O1, all other objects retained from SHA-bound -O0 build.',
    original_build_sha256=digest(source/'low-build-input.json'),original_binary_sha256=prior['binary_sha256'],
    generated_sha256=old['generated_sha256'],compiler_sha256=old['compiler_sha256'],
    compiler_version=old['compiler_version'],pch_command=replace(pch),commands=[replace(x) for x in commands])
manifest['archive_source']=str(archive_source)
manifest['archive_source_sha256']=digest(archive_source)
if logic_from:
    manifest['method']='Identical generated C++; fast gate evaluation -O1 plus retained SHA-bound trace -O1 objects; slow initialization objects remain -O0.'
    manifest['prior_trace_build_sha256']=digest(logic_from/'low-build-input.json')
(work/'low-build-input.json').write_text(json.dumps(manifest,indent=2)+'\n')
with (work/'build.log').open('w') as log:
    subprocess.run(replace(pch),cwd=obj,stdout=log,stderr=subprocess.STDOUT,check=True)
def compile_one(item):
    index,args=item
    args=replace(args)
    with (dest/(Path(args[args.index('-o')+1]).stem+'.log')).open('w') as log:
        subprocess.run(args,cwd=obj,stdout=log,stderr=subprocess.STDOUT,check=True)
    if index%100==0:print('TRACE_OBJECT_PASS',index,len(commands),flush=True)
with ThreadPoolExecutor(max_workers=12) as pool:list(pool.map(compile_one,enumerate(commands)))
archive=dest/'Vcalibrate_tb__ALL.a'
shutil.copyfile(archive_source,archive)
assert digest(archive)==manifest['archive_source_sha256']
with (work/'build.log').open('a') as log:
    subprocess.run(['ar','r',str(archive)]+[str(dest/Path(x[x.index('-o')+1])) for x in commands],stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(clang)]+[str(obj/f) for f in ('verilated.o','verilated_vcd_c.o','verilated_timing.o','verilated_threads.o')]+
                   [str(archive),'-pthread','-lpthread','-latomic','-o',str(dest/'Vcalibrate_tb')],stdout=log,stderr=subprocess.STDOUT,check=True)
paths=[work.parent/'mapped.v',Path('/public/home/yuzelu/project-circuit/issue250-p-final-native-diode-gate-GlrL0V/cells.v'),
       work/'commands.txt',work/'segments.json',work/'calibrate_tb.sv']
(work/'prebuilt-receipt.json').write_text(json.dumps(dict(inputs={str(p):digest(p) for p in paths},
    binary_sha256=digest(dest/'Vcalibrate_tb'),build_input_sha256=digest(work/'low-build-input.json')),indent=2)+'\n')
print('TRACE_OPT_BUILD_PASS',flush=True)
