"""Independent, read-only reception of the actual five-macro final leaves."""
import concurrent.futures
import json
from pathlib import Path
import shutil


def source(out,kind,original=False,repaired=False):
    from io_slots import file_sha
    assert kind in ('m','s','r','v')
    assert not (original or repaired) or kind=='m'
    number=(('189' if original else '193' if repaired else '205') if kind=='m'
            else dict(s='190',r='196',v='203')[kind])
    task=(('five-macro-route-m' if original else 'five-macro-repair-m-hold' if repaired else 'five-macro-finish-m-patch') if kind=='m'
          else 'five-macro-route-'+kind)
    folder=out.parents[2]/('block-v1-20261027-'+number+'/tasks/'+task)
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed'] is True
    proof=folder/'five-macro-native-flow.json';assert file_sha(proof)==receipt['outputs'][proof.name]
    flow=json.loads(proof.read_text());assert flow['passed'] and flow['pipeline_completed']
    top=flow['top'];results=folder/'flow/results/nangate45'/('bv1_'+top)/'base'
    for suffix in ('v','sdc','spef','def','odb'):
        p=results/('6_final.'+suffix)
        assert file_sha(p)==receipt['outputs'][str(p.relative_to(folder))]==flow['final_files'][p.name]['sha256']
    assert file_sha(folder/'config.mk')==receipt['outputs']['config.mk']==flow['config_sha256']
    assert file_sha(folder/'pins.json')==receipt['outputs']['pins.json']==flow['pins_sha256']
    return folder,receipt,flow,results


def physical(root,out,cpus,run,kind):
    from io_slots import file_sha
    from native_sta import inspect as sta_audit
    from native_annotation import inspect as annotation_audit
    from native_passive_endpoint import audit as passive_audit
    from native_driver_report import inspect as driver_audit
    from constraint_readback import audit as constraints
    assert cpus==16
    folder,r,flow,results=source(out,kind)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    control=out.parents[2]/'block-v1-20261027-131/tasks/native-passive-endpoint-probe'
    cr=json.loads((control/'receipt.json').read_text());assert cr['passed']
    q=control/'native-passive-endpoint-probe.json';assert file_sha(q)==cr['outputs'][q.name]
    qualified=json.loads(q.read_text());assert qualified['passed'] and qualified['actual']['passed']
    assert file_sha(lib)==qualified['library_sha256']
    assert cr['inputs']['project/experiments/block_v1/native_passive_endpoint.py']==file_sha(root/'project/experiments/block_v1/native_passive_endpoint.py')
    sta_control=out.parents[2]/'block-v1-20261027-066/tasks/native-sta-control'
    sc=json.loads((sta_control/'receipt.json').read_text());assert sc['passed'] is True
    sp=sta_control/'native-sta-control.json';assert file_sha(sp)==sc['outputs'][sp.name]
    sq=json.loads(sp.read_text());assert sq['positive']['passed'] and not sq['bad_capacitance']['passed'] and not sq['bad_setup']['passed']
    assert sq['annotation']['positive']['passed'] and not sq['annotation']['missing_input_rc']['passed']
    for name in ('native_sta.py','native_annotation.py'):
        relative='project/experiments/block_v1/'+name;assert sc['inputs'][relative]==file_sha(root/relative)
    prefix=''.join('set ::env('+k+') {'+str(results/name)+'}\n' for k,name in [('BV1_ODB','6_final.odb'),('BV1_SDC','6_final.sdc'),('BV1_SPEF','6_final.spef')])
    for name,body in [('sta','source {'+str(root/'project/experiments/block_v1/native_sta.tcl')+'}\n'),
                      ('physical','source {'+str(root/'project/experiments/block_v1/native_physical.tcl')+'}\n'),
                      ('drivers','read_db $::env(BV1_ODB)\nset ::env(BV1_UNDRIVEN_REPORT) {used-signal-drivers.tsv}\nsource {'+str(root/'project/experiments/block_v1/native_undriven.tcl')+'}\n')]:
        (out/(name+'.tcl')).write_text(prefix+body);run(['openroad','-no_init','-exit',str(out/(name+'.tcl'))],name+'.log')
    inventory={}
    for line in (out/'passive-inventory.tsv').read_text().splitlines():
        name,master,typ,direction,net=line.split('\t');assert name not in inventory
        inventory[name]=dict(master=master,type=typ,direction=direction,net=net,pin=name.rsplit('/',1)[1])
    timing=passive_audit(out,out/'timed-endpoints',lib.read_text(),inventory)
    annotation=annotation_audit(out);drivers=driver_audit((out/'used-signal-drivers.tsv').read_text())
    summary={}
    for line in (out/'physical-summary.tsv').read_text().splitlines():
        k,*values=line.split('\t');assert k not in summary;summary[k]=values
    dbu=int(summary['dbu'][0]);assert dbu==2000
    plan=json.loads((folder/'pins.json').read_text())['pins'];wanted={p['pin']:p for p in plan};got={}
    for line in (out/'physical-pins.tsv').read_text().splitlines():
        name,layer,*xy=line.split('\t');assert name not in got;got[name]=(layer,list(map(int,xy)))
    exact=set(wanted)==set(got)
    for name,p in wanted.items():
        x,y=p['xy_um'];w,h=p['size_um'];expect=[round(z*dbu) for z in (x-w/2,y-h/2,x+w/2,y+h/2)]
        exact &= got.get(name)==('metal10',expect)
    budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    boundary=constraints((out/'constraints-readback.sdc').read_text(),plan,budget)
    masters=[];active=0;physical_area=0
    for line in (out/'physical-masters.tsv').read_text().splitlines():
        name,typ,signal,w,h,count=line.split('\t');area=int(w)*int(h)*int(count)/dbu**2
        masters.append(dict(master=name,type=typ,signal=signal=='1',count=int(count),area_um2=area))
        if signal=='1':active+=area
        else:physical_area+=area
    expected=dict(line.split('\t')[:3][::2] for line in (results/'bv1-input-diodes.tsv').read_text().splitlines())
    observed=dict(line.split('\t') for line in (out/'physical-input-diodes.tsv').read_text().splitlines())
    checks=dict(all_real_timed_endpoints=timing['passed'],rc_coverage=annotation['passed'],
                used_signal_drivers=drivers['passed'],exact_m10_pin_geometry=exact,
                exact_input_diode_roots=bool(expected) and expected==observed,
                all_pg_iterms_correct=summary['incorrect_pg_iterms']==['0'] and int(summary['pg_iterm_count'][0])>0,
                pg_vdd=summary['pg_VDD']==['1'],pg_vss=summary['pg_VSS']==['1'],
                all_placed=summary['unplaced']==['0'],no_open_signal_inputs=summary['open_signal_inputs']==['0'],
                exact_ten_layers=summary['routing_layers']==[','.join('metal'+str(i) for i in range(1,11))],
                exact_die=list(map(int,summary['die']))==[0,0,round(flow['die_um'][0]*dbu),round(flow['die_um'][1]*dbu)])
    source(out,kind)
    result=dict(passed=all(checks.values()),top=flow['top'],checks=checks,timing=timing,rc_coverage=annotation,
                used_drivers=drivers,boundary=boundary,masters=masters,active_area_um2=active,
                physical_only_area_um2=physical_area,die_um=flow['die_um'],source=str(folder),
                source_receipt_sha256=file_sha(folder/'receipt.json'),exact_final_function_qualified=False,
                independent_full_deck_drc_qualified=False,qualified_hard_macro=False,
                scope='Actual final ODB/SDC/SPEF independent full endpoint/electrical/PG/connectivity/pin/RC reception; function/full-deck/strict LEC separate')
    (out/'five-macro-physical.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']


def drc(root,out,cpus,run,kind):
    from io_slots import file_sha,slot
    from native_drc import summarize
    assert cpus==16
    folder,r,flow,results=source(out,kind);nickname='bv1_'+flow['top']
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nwrite_def before.def\n'
    script+='if {[llength [info commands ::drt::check_drc_cmd]] != 1} {error "Missing whole-chip DRC API"}\n'
    script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def after.def\n'
    (out/'native-drc.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'native-drc.tcl')],'native-drc.log')
    assert file_sha(out/'before.def')==file_sha(out/'after.def')
    target=out/'gds-flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'gds-flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
    with slot(out.parents[2]):shutil.copyfile(results/'6_final.def',target/'6_final.def')
    run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(folder/'config.mk'),
         'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
    gds=target/'6_final.gds';deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'full-deck.lyrdb'),'-r',str(deck)],'full-deck.log')
    summary=summarize(out/'full-deck.lyrdb');native=(out/'native-whole-drc.rpt').read_text()
    source(out,kind)
    result=dict(passed=summary['total_items']==0 and not native.strip(),top=flow['top'],source=str(folder),
                source_receipt_sha256=file_sha(folder/'receipt.json'),native_report=native,full_deck=summary,
                deck_sha256=file_sha(deck),gds=dict(path=str(gds),sha256=file_sha(gds),bytes=gds.stat().st_size),
                qualified_hard_macro=False,scope='Actual final full-chip native DRC and complete unmodified FreePDK45 GDS deck; no exclusions')
    (out/'five-macro-drc.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']


def function(root,out,cpus,run,kind):
    from io_slots import file_sha
    from native_signal_view import export
    assert cpus==16
    folder,r,flow,results=source(out,kind);top=flow['top']
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    netlist,proof=export(root,out,run,folder,r,results,top,lib)
    (out/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(lib)+'\nwrite_verilog -noattr cells.v\n')
    run(['yosys','-s',str(out/'cells.ys')],'cells.log')
    bench=root/('project/experiments/block_v1/test_'+dict(m='matrix',s='store',r='recurrent',v='vector')[kind]+'_macro.cpp')
    compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    run([compiler,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module',top,'--prefix','V'+top,
         '-Mdir',str(out/'obj'),'--output-split','12000','--output-split-cfuncs','150','--threads','4',
         '--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O2',str(netlist),str(out/'cells.v'),str(bench)],'build.log')
    def simulate(case):
        name,initial,seed=case;log=name+'.json'
        run([str(out/'obj'/('V'+top)),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],log)
        result=json.loads((out/log).read_text());assert result['passed']
        return name,dict(initial=initial,seed=seed,result=result,log_sha256=file_sha(out/log))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        runs=dict(pool.map(simulate,[('all-ones',1,121),('random-121',2,121),('random-122',2,122)]))
    assert all(v['result']==runs['all-ones']['result'] for v in runs.values())
    source(out,kind)
    result=dict(passed=True,top=top,source=str(folder),source_receipt_sha256=file_sha(folder/'receipt.json'),
                full_final_netlist=proof,bench_sha256=file_sha(bench),library_sha256=file_sha(lib),
                cell_models_sha256=file_sha(out/'cells.v'),initial_runs=runs,physical_acceptance=False,
                strict_formal_qualified=False,qualified_hard_macro=False,
                scope='Full actual signal-bearing final ODB netlist including protection cells, three initial states, unchanged independent scoreboard; zero delay, STA/DRC/strict LEC separate')
    (out/'five-macro-final-function.json').write_text(json.dumps(result,indent=2)+'\n')


def formal(root,out,cpus,run,kind):
    from io_slots import file_sha
    from native_logic_projection import export
    from native_c8_qualification import composition_qualification
    from native_formal import inspect
    assert cpus==16
    folder,r,flow,results=source(out,kind);top=flow['top']
    earlier=out.parent/('five-macro-final-function-'+kind)
    receipt=json.loads((earlier/'receipt.json').read_text());assert receipt['passed'] is True
    proof=earlier/'five-macro-final-function.json';assert file_sha(proof)==receipt['outputs'][proof.name]
    fn=json.loads(proof.read_text());assert fn['passed']
    actual=Path(fn['full_final_netlist']['full_view'])
    assert file_sha(actual)==fn['full_final_netlist']['full_view_sha256']==receipt['outputs'][actual.name]
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    qualification=composition_qualification(root,out.parents[2])
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    assert file_sha(lib)==qualification['library_sha256'] and file_sha(binary)==qualification['binary_sha256']
    original=results/'1_synth_lec.v'
    assert file_sha(original)==r['outputs'][str(original.relative_to(folder))]
    # The controls prove exact constant functions and input-only protection
    # projection, including wrong-tie/wrong-clock rejection. Actual simulation
    # above always retains every physical signal-bearing cell.
    before,bproof=export(root,out,run,original,lib,top,'before',constant_functions=True)
    after,aproof=export(root,out,run,actual,lib,top,'after',constant_functions=True)
    assert bproof['removed_count']==0 and aproof['removed_count']>0
    config='format: verilog\ninput_paths:\n  - '+str(before)+'\n  - '+str(after)+'\n'
    config+='liberty_files:\n - '+str(lib)+'\nlog_file: '+str(out/'kepler.log')+'\n'
    (out/'kepler.yml').write_text(config);run([str(binary),'--config',str(out/'kepler.yml')],'formal.log')
    received=inspect((out/'kepler.log').read_text())
    source(out,kind)
    result=dict(passed=received['passed'],top=top,strict_native_lec=received,before=bproof,after=aproof,
                source=str(folder),source_receipt_sha256=file_sha(folder/'receipt.json'),
                source_final_function_receipt_sha256=file_sha(earlier/'receipt.json'),qualified_controls=qualification,
                log_sha256=file_sha(out/'kepler.log'),qualified_hard_macro=False,
                scope='Strict all-state/all-input/output positive native LEC of actual final source; audited no-function loads and exact library constants only')
    (out/'five-macro-formal.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
