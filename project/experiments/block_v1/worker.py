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
receipt = {'mode':MODE, 'cpus':CPUS, 'started':time.time(), 'commands':[],
           'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS}}


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
    elif MODE=='overlay':
        run(['python3',str(ROOT/'project/experiments/block_v1/overlay.py'),
             str(TOOLS/'lef/NangateOpenCellLibrary.tech.lef'),
             str(ROOT/'project/experiments/block_v1/technology.json'),str(OUT/'overlay')],'overlay.log')
        (OUT/'read.tcl').write_text('read_lef overlay/research12.tech.lef\nwrite_db overlay.odb\n'
                                  'help bench_wires\nhelp gen_rcx_model\nhelp extract_parasitics\n')
        run(['openroad','-no_init','-exit','read.tcl'],'openroad.log')
        (OUT/'inspect.py').write_text('''import odb,json
db=odb.dbDatabase.create()
odb.read_db(db,"overlay.odb")
tech=db.getTech()
layers=[(x.getName(),x.getRoutingLevel()) for x in tech.getLayers() if x.getRoutingLevel()>0]
assert [x[0] for x in layers]==["metal%d"%i for i in range(1,13)]
vias=[]
for name in ["BV1_via10","BV1_via11"]:
 v=tech.findVia(name)
 assert v is not None
 boxes=[(b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax()) for b in v.getBoxes()]
 assert len(boxes)==3
 vias.append(dict(name=name,boxes=boxes,resistance=v.getResistance()))
 assert v.getResistance()>0
print(json.dumps(dict(routing_layers=layers,vias=vias,dbu_per_um=tech.getDbUnitsPerMicron()),indent=2))
''')
        run(['openroad','-python','-no_init','-exit','inspect.py'],'database.json')
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
