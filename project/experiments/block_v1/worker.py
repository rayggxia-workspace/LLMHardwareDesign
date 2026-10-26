"""Allocation-local P1 jobs. Every mode preserves commands, input hashes and failure logs."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(sys.argv[1]).resolve()
MODE = sys.argv[2]
CPUS = int(sys.argv[3])
OUT = Path.cwd()
TOOLS = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
VERILATOR = Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
INPUTS = sorted(p for p in ROOT.rglob('*') if p.is_file())
bundle = json.loads((ROOT/'bundle-manifest.json').read_text())
for entry in bundle['files']:
    assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256'], 'source bundle hash mismatch'
receipt = {'mode':MODE, 'cpus':CPUS, 'started':time.time(), 'commands':[],
           'source_commit':bundle['source_commit'],
           'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS}}
receipt['tool_hashes']={}
for tool in [shutil.which('yosys'),shutil.which('openroad'),str(VERILATOR),str(VERILATOR.parent/'verilator_bin')]:
    if tool and Path(tool).is_file():
        receipt['tool_hashes'][tool]=hashlib.sha256(Path(tool).read_bytes()).hexdigest()


def run(argv, log):
    record = dict(argv=list(map(str,argv)), log=log, started=time.time())
    receipt['commands'].append(record)
    with (OUT/log).open('w') as stream:
        result = subprocess.run(record['argv'], stdout=stream, stderr=subprocess.STDOUT)
    record.update(returncode=result.returncode, finished=time.time())
    if result.returncode:
        raise RuntimeError('command failed; see '+log)


def rtl():
    return sorted(str(p) for p in (ROOT/'project/rtl').rglob('*.sv'))


def mapped(top, sources, destination=OUT):
    script = 'read_liberty -lib {lib}\nread_verilog -sv {sources}\nhierarchy -check -top {top}\n'
    script += 'synth -top {top} -noabc\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\nstat -liberty {lib}\n'
    script += 'write_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    script = script.format(lib=TOOLS/'lib/NangateOpenCellLibrary_typical.lib',sources=' '.join(sources),top=top)
    (destination/'map.ys').write_text(script)
    record=dict(argv=['yosys','-s',str(destination/'map.ys')],log=str(destination/'map.log'),started=time.time())
    receipt['commands'].append(record)
    with (destination/'map.log').open('w') as stream:
        result=subprocess.run(record['argv'],cwd=destination,stdout=stream,stderr=subprocess.STDOUT)
    record.update(returncode=result.returncode,finished=time.time())
    if result.returncode:
        raise RuntimeError('mapping failed: '+top)


try:
    if MODE=='transaction':
        run([str(VERILATOR),'--cc','--exe','--build','-j',str(CPUS),'-Wno-fatal',
             '--top-module','transaction6k','--Mdir',str(OUT/'obj'),'-CFLAGS','-std=c++17 -O2',
             str(ROOT/'project/rtl/block_v1/transaction6k.sv'),
             str(ROOT/'project/experiments/block_v1/test_transaction.cpp')],'build.log')
        run([str(OUT/'obj/Vtransaction6k')],'test.json')
    elif MODE=='map-stores':
        assert CPUS>=2
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[]
            for top,relative in [('store82','norm_service/store82.sv'),('transaction6k','block_v1/transaction6k.sv')]:
                destination=OUT/top
                destination.mkdir()
                jobs.append(pool.submit(mapped,top,[str(ROOT/'project/rtl'/relative)],destination))
            for job in jobs:
                job.result()
    elif MODE=='map-s16k':
        mapped('store82',[str(ROOT/'project/rtl/norm_service/store82.sv')])
    elif MODE=='map-t6k':
        mapped('transaction6k',[str(ROOT/'project/rtl/block_v1/transaction6k.sv')])
    elif MODE=='map-c8-full':
        mapped('shared121',rtl())
    elif MODE=='inventory':
        script='read_verilog -sv '+ ' '.join(rtl())+'\nhierarchy -check -top shared121\n'
        script+='proc\nopt\nmemory_dff\nopt\nmemory_collect\nopt_clean\nstat\nwrite_json generic.json\n'
        (OUT/'generic.ys').write_text(script)
        run(['yosys','-s','generic.ys'],'generic.log')
        # This maps identical production RTL bytes. The old mapped artifact is
        # separately bound rather than silently re-synthesized as a new result.
        old=OUT.parents[2]/'block-v1-20261027-004/tasks/map-c8-full'
        old_sources=json.loads((old/'receipt.json').read_text())['inputs']
        for entry in bundle['files']:
            if entry['path'].startswith('project/rtl/'):
                assert old_sources[entry['path']]==entry['sha256']
        run(['python3',str(ROOT/'project/experiments/block_v1/inventory121.py'),
             '--generic',str(OUT/'generic.json'),'--mapped',str(old/'mapped.json'),
             '--library',str(TOOLS/'lib/NangateOpenCellLibrary_typical.lib'),
             '--out',str(OUT/'inventory.json')],'inventory.log')
    elif MODE=='fsv-build':
        from fsv_build import build
        build(ROOT,OUT,CPUS,run)
    elif MODE in ('committed-suite','recovery-suite','mapped-suite'):
        driver='committed_qualification.cpp' if MODE=='recovery-suite' else 'committed_sim.cpp'
        sources=rtl()
        mapped_binding=None
        split=[]
        if MODE=='mapped-suite':
            original=OUT.parents[2]/'block-v1-20261027-004/tasks/map-c8-full'
            old=json.loads((original/'receipt.json').read_text())
            assert old['passed'] is True
            for entry in bundle['files']:
                if entry['path'].startswith('project/rtl/'):
                    assert old['inputs'][entry['path']]==entry['sha256']
            for name in ['mapped.json','mapped.v']:
                assert hashlib.sha256((original/name).read_bytes()).hexdigest()==old['outputs'][name]
            library=TOOLS/'lib/NangateOpenCellLibrary_typical.lib'
            script='read_json '+str(original/'mapped.json')+'\nwrite_verilog -noattr -noexpr mapped.v\n'
            script+='design -reset\nread_liberty -ignore_miss_func -ignore_miss_dir '+str(library)+'\nwrite_verilog -noattr cells.v\n'
            (OUT/'export.ys').write_text(script)
            run(['yosys','-s','export.ys'],'export.log')
            sources=[str(OUT/'mapped.v'),str(OUT/'cells.v')]
            split=['--output-split','12000','--output-split-cfuncs','150']
            mapped_binding=dict(flow='full-mapped-zero-delay',mapping_receipt=str(original/'receipt.json'),
                mapping_receipt_sha256=hashlib.sha256((original/'receipt.json').read_bytes()).hexdigest(),
                mapped_json=str(original/'mapped.json'),mapped_json_sha256=old['outputs']['mapped.json'],
                library=str(library),library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
                exported_models={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in sources},
                qualification='Both S16K and T6K remain mapped cells; no behavioral memory substitution; no delay/STA claim')
        run([str(VERILATOR),'--cc','--exe','--build','-j',str(CPUS),'-Wno-fatal',
             '--top-module','shared121','--prefix','Vshared121','--Mdir',str(OUT/'obj'),
             *split,'-CFLAGS','-std=c++17 -O2',*sources,str(ROOT/'project/experiments/block_v1'/driver)],'build.log')
        binary=OUT/'obj/Vshared121'
        binary_sha=hashlib.sha256(binary.read_bytes()).hexdigest()
        receipt['binary_sha256']=binary_sha
        build=dict(top='shared121',binary=str(binary),binary_sha256=binary_sha,source_commit=bundle['source_commit'],
                   source_bundle_sha256=hashlib.sha256((ROOT/'bundle-manifest.json').read_bytes()).hexdigest(),
                   command=receipt['commands'][-1],mapped_binding=mapped_binding)
        (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
        inp=OUT.parents[2]/'block-v1-20261027-004/tasks/fixtures/upstream/input01'
        assert inp.is_dir(), str(inp)
        def simulate(stall):
            destination=OUT/('mixed%d'%stall)
            destination.mkdir()
            argv=[str(binary),str(inp/'vectors.tsv'),str(destination/'actual.jsonl'),str(stall),'0']
            start=time.time()
            with (destination/'simulation.log').open('w') as log:
                result=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
            command=dict(argv=argv,exit=result.returncode,seconds=time.time()-start)
            (destination/'simulation-command.json').write_text(json.dumps(command,indent=2)+'\n')
            m=dict(schema='shared121-committed-run/1',suite='qualification-committed' if MODE=='recovery-suite' else 'mixed-committed',stall=stall,pilot=0,
                   binary_sha256=binary_sha,build_path=str(OUT/'build.json'),build_sha256=hashlib.sha256((OUT/'build.json').read_bytes()).hexdigest(),
                   source_commit=build['source_commit'],source_bundle_sha256=build['source_bundle_sha256'],
                   input_manifest_sha256=hashlib.sha256((inp/'manifest.json').read_bytes()).hexdigest())
            m['artifacts']=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in destination.iterdir()if p.is_file()]
            (destination/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
            if result.returncode:
                raise RuntimeError('committed simulation failed: '+str(destination))
            run(['python3',str(ROOT/'project/experiments/block_v1/receive121.py'),'--input',str(inp),
                 '--run',str(destination),'--out',str(destination/'received')],'receive%d.log'%stall)
        assert CPUS>=2
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(simulate,stall)for stall in [0,1]]
            for job in jobs:
                job.result()
    elif MODE=='core-build':
        run([str(VERILATOR),'--cc','--exe','--build','-j',str(CPUS),'-Wno-fatal',
             '--top-module','shared109','--prefix','Vshared109','--Mdir',str(OUT/'obj'),
             '-CFLAGS','-std=c++17 -O2',*rtl(),str(ROOT/'project/experiments/shared_gdn/sim.cpp')],'build.log')
        run([str(VERILATOR),'--lint-only','-Wno-fatal','--top-module','shared121',*rtl()],'wrapper-lint.log')
    elif MODE=='fixtures':
        archive=Path('/public/home/yuzelu/RuizhiLiang/issue109-shared-gdn-20261025/delivery01/full-results.zip')
        raw=archive.read_bytes()
        assert len(raw)==104917869
        assert hashlib.sha256(raw).hexdigest()=='9de3fc27bf2fd89fbcb8d3d1a753b26910b4a73214ee8d0f42ad0f1334a19994'
        shutil.copyfile(archive,OUT/'upstream.zip')
        with zipfile.ZipFile(OUT/'upstream.zip') as zf:
            assert len(zf.namelist())==673 and len(set(zf.namelist()))==673
            for name in zf.namelist():
                path=PurePosixPath(name)
                assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
            zf.extractall(OUT/'upstream')
            receipt['upstream_archive_members']=zf.namelist()
        receipt['upstream_archive_sha256']=hashlib.sha256(raw).hexdigest()
    elif MODE in ('overlay','route-probe'):
        run(['python3',str(ROOT/'project/experiments/block_v1/overlay.py'),
             str(TOOLS/'lef/NangateOpenCellLibrary.tech.lef'),
             str(ROOT/'project/experiments/block_v1/technology.json'),str(OUT/'overlay')],'overlay.log')
        (OUT/'read.tcl').write_text('read_lef overlay/research12.tech.lef\nwrite_db overlay.odb\n'
                                  'help bench_wires\nhelp gen_rcx_model\nhelp extract_parasitics\n')
        run(['openroad','-no_init','-exit','read.tcl'],'openroad.log')
        run(['openroad','-no_init','-exit',str(ROOT/'project/experiments/block_v1/inspect_overlay.tcl')],'database-read.log')
        if MODE=='route-probe':
            run(['python3',str(ROOT/'project/experiments/block_v1/route_probe.py'),'generate',str(OUT/'probe'),'--cpus',str(CPUS)],'probe-generate.log')
            run(['openroad','-no_init','-exit',str(OUT/'probe/route.tcl')],'route.log')
            run(['python3',str(ROOT/'project/experiments/block_v1/route_probe.py'),'audit',str(OUT/'probe')],'probe-audit.log')
    else:
        raise ValueError('unsupported mode '+MODE)
    receipt['passed']=True
except BaseException as exc:
    receipt['passed']=False
    receipt['error']=repr(exc)
    raise
finally:
    receipt['finished']=time.time()
    receipt['outputs']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in OUT.rglob('*') if p.is_file() and p.name not in ('receipt.json','job.log')
                        and 'obj' not in p.relative_to(OUT).parts}
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
