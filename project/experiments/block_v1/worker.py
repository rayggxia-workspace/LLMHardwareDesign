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
for tool in [shutil.which('yosys'),shutil.which('openroad'),shutil.which('klayout'),str(VERILATOR),str(VERILATOR.parent/'verilator_bin')]:
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
    elif MODE=='reference-pilot':
        from reference_run import pilot
        pilot(ROOT,OUT,CPUS)
    elif MODE=='reference-fit':
        from reference_fit import fit
        fit(ROOT,OUT,run)
    elif MODE=='fv-install':
        from fv_reference import install
        install(ROOT,OUT,run)
    elif MODE.startswith('fv-case-'):
        from fv_reference import verify
        verify(ROOT,OUT,CPUS,run,int(MODE.rsplit('-',1)[1]))
    elif MODE.startswith('direct-view-'):
        from direct_field_view import verify
        verify(ROOT,OUT,run,int(MODE.rsplit('-',1)[1]))
    elif MODE=='heldout-rc':
        from heldout_rc import verify
        verify(ROOT,OUT,CPUS,run)
    elif MODE=='native-flow-info':
        flow=Path('/OpenROAD-flow-scripts/flow')
        selected=['Makefile','variables.yaml','scripts/floorplan.tcl','scripts/io_placement.tcl',
                  'scripts/load.tcl','scripts/global_place.tcl','scripts/detail_place.tcl',
                  'scripts/pdn.tcl','scripts/cts.tcl','scripts/global_route.tcl','scripts/detail_route.tcl',
                  'scripts/rcx.tcl','scripts/final_report.tcl','scripts/util.tcl',
                  'platforms/nangate45/config.mk','platforms/nangate45/setRC.tcl',
                  'platforms/nangate45/pdn/block_grid.tcl']
        info={}
        for relative in selected:
            path=flow/relative
            info[relative]={'exists':path.exists()}
            if path.is_file():
                assert path.stat().st_size<2*1024*1024
                target=OUT/'flow-source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target)
                info[relative]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        (OUT/'native-flow-info.json').write_text(json.dumps(info,indent=2)+'\n')
        (OUT/'native-help.tcl').write_text('\n'.join('help '+cmd for cmd in
            ['initialize_floorplan','place_pin','place_pins','set_io_pin_constraint','set_pin_length',
             'set_routing_layers','make_tracks','check_power_grid'])+'\n')
        run(['openroad','-no_init','-exit','native-help.tcl'],'native-help.log')
    elif MODE=='extraction-tool-info':
        import importlib.util
        probe=dict(python_packages={name:importlib.util.find_spec(name)is not None
                    for name in ['numpy','scipy','pyamg']},paths={})
        for name in ['/OpenROAD-flow-scripts/tools/OpenROAD',
                     '/OpenROAD-flow-scripts/tools/OpenROAD/build',
                     '/OpenROAD-flow-scripts/tools/install/OpenROAD/lib',
                     '/OpenROAD-flow-scripts/tools/install/OpenROAD/include']:
            path=Path(name)
            probe['paths'][name]=dict(exists=path.exists(),
                entries=sorted(p.name for p in path.iterdir())if path.is_dir()else [])
        # Read only exact relevant source/build files, without a recursive
        # tool-tree scan or a build on the login node.
        for relative in ['.git/HEAD','CMakeLists.txt','build/CMakeCache.txt',
                         'src/rcx/include/rcx/extMeasureRC.h','src/fsv/CMakeLists.txt']:
            path=Path('/OpenROAD-flow-scripts/tools/OpenROAD')/relative
            if path.is_file():
                target=OUT/'tool-source'/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target)
        (OUT/'extraction-tool-info.json').write_text(json.dumps(probe,indent=2)+'\n')
    elif MODE in ('geometry-reader-full','geometry-reader-pg'):
        from klayout_overlay import generate
        prior=OUT.parents[2]/'block-v1-20261027-009/tasks/route-probe'
        bound=json.loads((prior/'receipt.json').read_text());assert bound['passed']is True
        for name in ['probe/routed.odb','overlay/research12.tech.lef','probe/landing.lef']:
            assert hashlib.sha256((prior/name).read_bytes()).hexdigest()==bound['outputs'][name]
        if MODE=='geometry-reader-pg':
            import re
            technology=(prior/'overlay/research12.tech.lef').read_text()
            vias=[name for name,body in re.findall(r'(?ms)^VIA\s+(\S+)(.*?)^END\s+\1\s*$',technology)
                  if set(re.findall(r'\bLAYER\s+(\w+)\s*;',body))=={'metal1','via1','metal2'}]
            assert vias,'Native M1/M2 via missing'
            text=(prior/'probe/routed.def').read_text()
            special='SPECIALNETS 1 ;\n- VDD + USE POWER\n + ROUTED metal1 400 ( 20000 20000 ) ( 30000 20000 ) '+vias[0]
            special+=' NEW metal2 400 ( 30000 20000 ) ( 30000 30000 )\n'
            special+=' NEW metal10 1600 ( 20000 100000 ) ( 30000 100000 ) BV1_via10\n'
            special+=' NEW metal11 1600 ( 30000 100000 ) ( 40000 100000 ) BV1_via11\n'
            special+=' NEW metal12 1600 ( 40000 100000 ) ( 40000 110000 ) ;\nEND SPECIALNETS\n'
            assert re.search(r'(?m)^NETS ',text)
            text=re.sub(r'(?m)^NETS ',lambda m:special+m.group(0),text,count=1)
            (OUT/'special-fixture.def').write_text(text)
            script='read_lef {'+str(prior/'overlay/research12.tech.lef')+'}\nread_lef {'+str(prior/'probe/landing.lef')+'}\nread_def special-fixture.def\n'
        else:
            script='read_db {'+str(prior/'probe/routed.odb')+'}\n'
        script+='source {'+str(ROOT/'project/experiments/block_v1/odb_geometry.tcl')+'}\n'
        script+=r'''
set inst [lindex [[ord::get_db_block] getInsts] 0]
$inst setPlacementStatus PLACED
foreach orient {R0 R90 R180 R270 MX MY MXR90 MYR90} {
  $inst setOrient $orient
  bvgeom::export geometry-$orient.tsv
  write_def geometry-$orient.def
}
'''
        (OUT/'geometry-reader.tcl').write_text(script)
        run(['openroad','-no_init','-exit','geometry-reader.tcl'],'geometry-reader.log')
        generate(TOOLS,json.loads((ROOT/'project/experiments/block_v1/technology.json').read_text()),OUT/'klayout')
        run(['klayout','-b','-r',str(ROOT/'project/experiments/block_v1/odb_geometry_check.rb'),
             '-rd','lyt='+str(OUT/'klayout/research12.lyt'),'-rd','tech='+str(prior/'overlay/research12.tech.lef'),
             '-rd','macro='+str(prior/'probe/landing.lef'),'-rd','report='+str(OUT/'odb-geometry.json')],'geometry-mask.log')
    elif MODE=='geometry-transform-probe':
        prior=OUT.parents[2]/'block-v1-20261027-009/tasks/route-probe'
        bound=json.loads((prior/'receipt.json').read_text());assert bound['passed']is True
        path=prior/'probe/routed.odb'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==bound['outputs']['probe/routed.odb']
        script='read_db {'+str(path)+'}\n'
        script+=r'''
set inst [lindex [[ord::get_db_block] getInsts] 0]
$inst setPlacementStatus PLACED
foreach orient {R0 R90 R180 R270 MX MY MXR90 MYR90} {
  $inst setOrient $orient
  set transform [$inst getTransform]
  set point [odb::new_Point 1000 2000]
  set status [catch {$transform apply $point} result]
  puts "TRANSFORM $orient [$inst getOrigin] $status $result [$point getX] [$point getY]"
  odb::delete_Point $point
}
'''
        (OUT/'geometry-transform.tcl').write_text(script)
        run(['openroad','-no_init','-exit','geometry-transform.tcl'],'geometry-transform.log')
    elif MODE=='geometry-reader-probe':
        prior=OUT.parents[2]/'block-v1-20261027-036/tasks/direct-view-5'
        bound=json.loads((prior/'receipt.json').read_text());assert bound['passed']is True
        path=prior/'actual.odb'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==bound['outputs']['actual.odb']
        script='read_db {'+str(path)+'}\nsource {'+str(ROOT/'project/experiments/block_v1/odb_geometry.tcl')+'}\nbvgeom::export geometry.tsv\n'
        (OUT/'geometry-reader.tcl').write_text(script)
        run(['openroad','-no_init','-exit','geometry-reader.tcl'],'geometry-reader.log')
    elif MODE=='geometry-api-probe':
        # Determine the installed immutable binary's read-only geometry API
        # before choosing a full-design direct-field reader.
        binary=shutil.which('openroad')
        nm=shutil.which('nm')
        if nm:
            result=subprocess.run([nm,'-D','--defined-only',binary],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            selected=[line for line in result.stdout.splitlines()if any(name in line for name in ['dbWireShapeItr','dbShape','dbBlock','Tcl_Init'])]
            (OUT/'geometry-symbols.txt').write_text('returncode=%d\n'%result.returncode+'\n'.join(selected)+'\n')
        probe=OUT.parents[2]/'block-v1-20261027-009/tasks/route-probe'
        prior=json.loads((probe/'receipt.json').read_text());assert prior['passed']is True
        path=probe/'probe/routed.odb';assert hashlib.sha256(path.read_bytes()).hexdigest()==prior['outputs']['probe/routed.odb']
        script='read_db {'+str(path)+'}\n'
        script+=r'''
foreach pattern {odb::*Wire* odb::*Shape* odb::*Transform*} { puts "API $pattern [info commands $pattern]" }
set net [[ord::get_db_block] findNet link]
set wire [$net getWire]
catch {$wire __probe_methods} message
puts "WIRE_METHODS $message"
foreach constructor {odb::dbWireShapeItr odb::new_dbWireShapeItr odb::dbShape odb::new_dbShape} {
  if {[llength [info commands $constructor]]} {
    set code [catch {$constructor} value]
    puts "CONSTRUCTOR $constructor $code $value"
  }
}
'''
        (OUT/'geometry-api.tcl').write_text(script)
        run(['openroad','-no_init','-exit','geometry-api.tcl'],'geometry-api.log')
    elif MODE.startswith('heldout-rc-v'):
        from heldout_rc import verify
        verify(ROOT,OUT,CPUS,run,float(MODE.removeprefix('heldout-rc-v')))
    elif MODE.startswith('reference-shard-'):
        from reference_run import pilot
        pilot(ROOT,OUT,CPUS,int(MODE.rsplit('-',1)[1]))
    elif MODE.startswith('reference-receive-'):
        from reference_run import pilot
        pilot(ROOT,OUT,CPUS,int(MODE.rsplit('-',1)[1]),receive=True)
    elif MODE=='semantic-negative':
        qualified=OUT.parents[2]/'block-v1-20261027-006'
        inp=OUT.parents[2]/'block-v1-20261027-004/tasks/fixtures/upstream/input01'
        run(['python3',str(ROOT/'project/experiments/block_v1/semantic_negative.py'),str(qualified/'src'),
             str(inp),str(qualified/'tasks/committed-suite/mixed0'),str(OUT/'negative')],'negative.log')
    elif MODE=='physical-inputs':
        from physical_inputs import prepare
        prepare(ROOT,OUT,CPUS,run)
    elif MODE=='technology-audit':
        selected=[]
        for path in sorted(TOOLS.rglob('*')):
            if path.is_file() and (path.suffix in ('.map','.lyp','.lyt','.lydrc') or path.name=='config.mk'):
                assert path.stat().st_size<2*1024*1024
                relative=path.relative_to(TOOLS)
                target=OUT/'native-config'/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target)
                selected.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        assert selected
        (OUT/'native-config-index.json').write_text(json.dumps(selected,indent=2)+'\n')
        run(['klayout','-b','-r',str(ROOT/'project/experiments/block_v1/inspect_native_gds.rb'),
             '-rd','platform='+str(TOOLS),'-rd','report='+str(OUT/'native-gds-layers.json')],'native-gds.log')
    elif MODE=='probe-geometry':
        from klayout_overlay import generate
        generate(TOOLS,json.loads((ROOT/'project/experiments/block_v1/technology.json').read_text()),OUT/'klayout')
        probe=OUT.parents[2]/'block-v1-20261027-009/tasks/route-probe'
        prior=json.loads((probe/'receipt.json').read_text())
        assert prior['passed'] is True
        for name in ['probe/routed.def','probe/unrouted.def','probe/landing.lef','overlay/research12.tech.lef']:
            assert hashlib.sha256((probe/name).read_bytes()).hexdigest()==prior['outputs'][name]
        arguments=dict(lyt=OUT/'klayout/research12.lyt',tech_lef=probe/'overlay/research12.tech.lef',
                       landing_lef=probe/'probe/landing.lef',unrouted=probe/'probe/unrouted.def',routed=probe/'probe/routed.def',out=OUT)
        argv=['klayout','-b','-r',str(ROOT/'project/experiments/block_v1/probe_geometry.rb')]
        for key,value in arguments.items():argv+=['-rd',key+'='+str(value)]
        run(argv,'geometry.log')
    elif MODE=='pattern-prepare':
        from pattern_prepare import prepare
        from rc_pipeline import configuration
        folder=OUT.parents[2]/configuration(ROOT)['patterns_run']/'tasks/rcx-complete-patterns'
        prior=json.loads((folder/'receipt.json').read_text());assert prior['passed'] is True
        for name in ['patterns.odb','patterns.def','overlay/research12.tech.lef']:
            assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==prior['outputs'][name]
        script='read_db {'+str(folder/'patterns.odb')+'}\n'+r'''
set tech [ord::get_db_tech]
set stream [open pattern-ndr.json w]
puts $stream "{\"dbu_per_um\":[$tech getDbUnitsPerMicron],\"rules\":\{"
set separator ""
foreach rule [$tech getNonDefaultRules] {
  puts -nonewline $stream "$separator\"[$rule getName]\":\{"
  set inner ""
  foreach layer [$tech getLayers] {
    set entry [$rule getLayerRule $layer]
    if {$entry ne "NULL" && $entry ne ""} {
      puts -nonewline $stream "$inner\"[$layer getName]\":{\"width_dbu\":[$entry getWidth],\"spacing_dbu\":[$entry getSpacing]}"
      set inner ","
    }
  }
  puts -nonewline $stream "\}"
  set separator ","
}
puts $stream "\}\}"
close $stream
'''
        (OUT/'pattern-ndr.tcl').write_text(script)
        run(['openroad','-no_init','-exit','pattern-ndr.tcl'],'pattern-ndr.log')
        prepare(folder,OUT/'pattern-ndr.json',OUT/'reference-patterns')
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
    elif MODE in ('overlay','route-probe','rcx-patterns','rcx-classic-patterns','rcx-complete-patterns'):
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
        if MODE in ('rcx-patterns','rcx-classic-patterns','rcx-complete-patterns'):
            arguments='-v1'if MODE=='rcx-patterns'else'-met_cnt 12'
            context_distance=12 if MODE=='rcx-complete-patterns'else 3
            (OUT/'patterns.tcl').write_text('read_lef overlay/research12.tech.lef\n'
                 'bench_wires '+arguments+' -len 100 -cnt 5 -w_list {1 2} -s_list {1 2 4 8} -all '
                 '-over_dist '+str(context_distance)+' -under_dist '+str(context_distance)+'\n'
                 'write_db patterns.odb\nwrite_def patterns.def\nbench_verilog patterns.v\n'
                 'help bench_read_spef\nhelp write_rules\nhelp gen_rcx_model\n')
            run(['openroad','-no_init','-exit','patterns.tcl'],'patterns.log')
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
