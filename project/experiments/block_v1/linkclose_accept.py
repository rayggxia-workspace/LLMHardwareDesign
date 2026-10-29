"""Independent complete physical/functional gates for fixed interface candidates."""
import json
from pathlib import Path
from interconnect_spef import sha


def source(out,kind):
    folder=out.parent/('linkclose-pgfix-'+kind)
    if not folder.exists():folder=out.parent/('linkclose-physical-'+kind)
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']
    proof=folder/'linkclose-physical.json';assert sha(proof)==receipt['outputs'][proof.name]
    flow=json.loads(proof.read_text());assert flow['passed']
    results=folder/'flow/results/nangate45'/('bv1_'+flow['top'])/'base'
    for row in flow['files'].values():
        path=Path(row['path']);assert sha(path)==row['sha256']==receipt['outputs'][str(path.relative_to(folder))]
    return folder,receipt,flow,results


def verify(root,out,cpus,run,kind):
    from five_macro_receive import physical,drc
    from native_signal_view import export
    from native_logic_projection import export as projection
    from native_formal import inspect
    from revision300_rtl import COMPILER
    assert cpus==16
    folder,receipt,flow,results=source(out,kind)
    physical(root,out,cpus,run,kind,selected=source,sdc_override=folder/'input.sdc')
    drc(root,out,cpus,run,kind,selected=source)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    target,view=export(root,out,run,folder,receipt,results,flow['top'],lib)
    before,bp=projection(root,out,run,results/'1_synth_lec.v',lib,flow['top'],'before',constant_functions=True)
    after,ap=projection(root,out,run,target,lib,flow['top'],'after',constant_functions=True)
    cfg='format: verilog\ninput_paths:\n - '+str(before)+'\n - '+str(after)+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(out/'kepler.log')+'\n'
    (out/'kepler.yml').write_text(cfg)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    run([binary,'--config',out/'kepler.yml'],'formal.log')
    formal=inspect((out/'kepler.log').read_text());assert formal['passed']
    (out/'models.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(lib)+'\nwrite_verilog -noattr cells.v\n')
    run(['yosys','-s',out/'models.ys'],'models.log')
    controls={}
    if kind=='bridge':
        # The actual complete physical interface replaces the RTL bridge;
        # original M/T/S RTL remains unchanged, and is separately qualified.
        text=target.read_text();needle='module '+flow['top']+' '
        assert text.count(needle)==1
        gate=out/'final-bridge.v';gate.write_text(text.replace(needle,'module linkclose_bridge ',1))
        paths=[root/'project/rtl/block_library_v1/block_v1_m.sv',root/'project/rtl/block_library_v1/block_v1_s16k.sv',
               root/'project/rtl/block_v1/transaction6k.sv',root/'project/experiments/block_v1/linkclose_mts_bench.sv',
               root/'project/experiments/block_v1/test_linkclose_mts.cpp',gate,out/'cells.v']
        run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--x-initial','unique','--x-assign','unique',
             '--top-module','linkclose_mts_bench','-Mdir',out/'obj','-CFLAGS','-std=c++17 -O2']+paths,'build.log')
        for label,initial,seed in [('ones',1,121),('random121',2,121),('random122',2,122)]:
            run([out/'obj/Vlinkclose_mts_bench','+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],label+'.json')
            controls[label]=json.loads((out/(label+'.json')).read_text());assert controls[label]['passed']
        assert all(v==controls['ones'] for v in controls.values())
    # Inspect actual final output masters, rather than assuming mapped drivers
    # survive standard feed-through removal and resizing.
    expected=[('drive_'+port+'_'+str(i)) for port,count in [('response_ready',1),('write_valid',1),('write_index',10),('write_data',128)] for i in range(count)] if kind=='bridge' else ['relay_'+str(i) for i in range(flow['fixed_buf_x16'])]
    script='read_db {'+str(results/'6_final.odb')+'}\nset f [open fixed-drivers.tsv w]\n'
    for name in expected:
        script+='set i [[ord::get_db_block] findInst {'+name+'}]\nif {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X16"} {error {Fixed driver missing or changed: '+name+'}}\nputs $f "[$i getName]\\t[[$i getMaster] getName]\\t[$i getLocation]"\n'
    script+='close $f\nwrite_abstract_lef -bloat_occupied_layers candidate.lef\n'
    (out/'fixed-drivers.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'fixed-drivers.tcl'],'fixed-drivers.log')
    record=dict(passed=True,kind=kind,source=str(folder),source_receipt_sha256=sha(folder/'receipt.json'),
        physical=json.loads((out/'five-macro-physical.json').read_text()),drc=json.loads((out/'five-macro-drc.json').read_text()),
        complete_signal_view=view,strict_final_lec=formal,before_projection=bp,after_projection=ap,
        physical_bridge_protocol_runs=controls,fixed_driver_count=len(expected),fixed_drivers_sha256=sha(out/'fixed-drivers.tsv'),
        scope='Actual prefabricated interface native M1-M10 physical/PG/RC/pin/DRC/strict-LEC acceptance and final bridge protocol regression. No upper-layer combination qualification transfers automatically.')
    (out/'linkclose-accept.json').write_text(json.dumps(record,indent=2)+'\n')
