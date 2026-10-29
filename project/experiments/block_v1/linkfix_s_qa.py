"""Independent post-patch native gates; complete unmodified DRC remains mandatory."""
import json
from pathlib import Path
from interconnect_spef import sha
from linkclose_measure import bound
from linkfix import received_source


def check(root,out,cpus,run,gate):
    assert cpus==16
    source,r,flow,results=received_source(out,'s')
    assert source.name=='linkfix-s-finish' and flow['native_whole_drc_zero_before_full_acceptance']
    if gate=='physical':
        from five_macro_receive import physical
        physical(root,out,cpus,run,'s',selected=received_source,sdc_override=source/'input.sdc')
        return
    if gate=='drc':
        from five_macro_receive import drc
        drc(root,out,cpus,run,'s',selected=received_source)
        return
    from native_signal_view import export
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    target,view=export(root,out,run,source,r,results,flow['top'],lib)
    if gate=='function':
        old_dir=out.parents[2]/'block-v1-20261029-937/tasks/linkfix-function-s'
        old,old_receipt=bound(old_dir,'five-macro-final-function.json')
        assert old['source']==flow['inherited_repaired_source']
        assert old['source_receipt_sha256']==flow['inherited_repaired_source_receipt_sha256']
        assert old['full_final_netlist']['full_view_sha256']==view['full_view_sha256']==sha(target)
        assert old['library_sha256']==sha(lib)
        bench=root/'project/experiments/block_v1/test_store_macro.cpp'
        assert old['bench_sha256']==sha(bench)
        assert len(old['initial_runs'])==3 and all(x['result']['passed']for x in old['initial_runs'].values())
        for x in old['initial_runs'].values():
            name=next(k for k,v in old['initial_runs'].items()if v is x)+'.json'
            assert sha(old_dir/name)==x['log_sha256']==old_receipt['outputs'][name]
        reuse=dict(passed=True,old_function=str(old_dir),old_receipt_sha256=sha(old_dir/'receipt.json'),
                   identical_complete_signal_view_sha256=sha(target),same_library_sha256=sha(lib),same_bench_sha256=sha(bench),
                   scope='Three actual closed simulations reused only after byte-identical complete signal netlist, library and unchanged bench proof. No geometry, RC or timing acceptance transferred.')
        result=dict(old,source=str(source),source_receipt_sha256=sha(source/'receipt.json'),full_final_netlist=view,functional_reuse=reuse)
        (out/'function-reuse.json').write_text(json.dumps(reuse,indent=2)+'\n')
        (out/'five-macro-final-function.json').write_text(json.dumps(result,indent=2)+'\n')
        return
    assert gate=='formal'
    from native_logic_projection import export as projection
    from native_formal import inspect
    before,bp=projection(root,out,run,results/'1_synth_lec.v',lib,flow['top'],'before',constant_functions=True)
    after,ap=projection(root,out,run,target,lib,flow['top'],'after',constant_functions=True)
    (out/'kepler.yml').write_text('format: verilog\ninput_paths:\n - '+str(before)+'\n - '+str(after)+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(out/'kepler.log')+'\n')
    run(['/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal','--config',out/'kepler.yml'],'formal.log')
    formal=inspect((out/'kepler.log').read_text());assert formal['passed']
    result=dict(passed=True,source=str(source),source_receipt_sha256=sha(source/'receipt.json'),complete_signal_view=view,
                strict_final_lec=formal,before_projection=bp,after_projection=ap)
    (out/'linkfix-s-formal.json').write_text(json.dumps(result,indent=2)+'\n')


def combine(root,out,cpus,run):
    source,r,flow,results=received_source(out,'s')
    reports={};bindings={}
    for gate,name in [('physical','five-macro-physical.json'),('drc','five-macro-drc.json'),('formal','linkfix-s-formal.json'),('function','five-macro-final-function.json')]:
        folder=out.parent/('linkfix-s-qa-'+gate)
        result,receipt=bound(folder,name)
        assert result['source']==str(source) and result['source_receipt_sha256']==sha(source/'receipt.json')
        reports[gate]=result;bindings[gate]=dict(receipt_sha256=sha(folder/'receipt.json'),report_sha256=sha(folder/name))
    io,ir=bound(out.parent/'linkfix-io-view-s','linkfix-io-view.json')
    assert io['source_receipt_sha256']==sha(source/'receipt.json')
    assert reports['formal']['complete_signal_view']['full_view_sha256']==reports['function']['full_final_netlist']['full_view_sha256']
    assert reports['drc']['full_deck']['total_items']==0 and not reports['drc']['native_report'].strip()
    result=dict(passed=True,kind='s',source=str(source),source_receipt_sha256=sha(source/'receipt.json'),
                physical=reports['physical'],drc=reports['drc'],complete_signal_view=reports['formal']['complete_signal_view'],
                strict_final_lec=reports['formal']['strict_final_lec'],before_projection=reports['formal']['before_projection'],
                after_projection=reports['formal']['after_projection'],independent_gates=bindings,
                actual_launch_drivers_sha256=ir['outputs']['actual-launch-drivers.tsv'],
                scope='All independent patched S native gates joined by exact immutable source receipt; full DRC has no exclusions.')
    (out/'linkfix-accept.json').write_text(json.dumps(result,indent=2)+'\n')
