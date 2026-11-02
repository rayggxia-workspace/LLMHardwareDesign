"""Bind one declared physical scene to its function, PG and three RC corners.

This collector cannot turn leaf-only timing or a placement diagnostic into a
system result. The accepted scope is the exact declared six-native reference
composition; R integration remains a separate unfinished task.
"""
import json,math,re,shutil
from pathlib import Path


def audit(manifest_path,graph_path,route,config_path,out,bind):
    def read(path):
        path=Path(path);bind(path);return json.loads(path.read_text())
    def outputs(folder,receipt):
        for name,digest in receipt['outputs'].items():bind(folder/name,digest)
    config=read(config_path)
    assert set(config)=={'geometry','pg_audit','function_run','topology','signal_graph','timing'}
    assert set(config['timing'])=={'low','base','high'}
    manifest=read(manifest_path);graph=read(graph_path)
    from boundary_links import validate,verilog
    bind(Path(__file__).with_name('boundary_links.py'));validate(manifest,graph)
    geometry=Path(config['geometry']);physical=read(geometry/'receipt.json')
    assert physical['passed']and physical['actual_odb_def_readback']and physical['actual_joined_gds_readback']
    assert physical['inputs'][str(graph_path)]==bind(graph_path)
    assert physical['inputs'][str(manifest_path)]==bind(manifest_path)
    routed=read(route/'receipt.json')
    assert routed['passed']and routed['search']['final_conflicts']==0 and not routed.get('stage')
    for name,digest in routed['outputs'].items():
        bind(route/name,digest)
        assert physical['inputs'][str(route/name)]==digest
    outputs(geometry,physical)
    pg_folder=Path(config['pg_audit']);pg=read(pg_folder/'receipt.json')
    assert pg['passed']and pg['system_pg_qualified']
    assert pg['inputs'][str(geometry/'receipt.json')]==bind(geometry/'receipt.json')
    assert pg['inputs'][str(graph_path)]==bind(graph_path)
    assert pg['inputs'][str(manifest_path)]==bind(manifest_path)
    outputs(pg_folder,pg)
    signal=read(config['signal_graph']);topology=read(config['topology'])['modules']['control_system']
    validate(manifest,signal)
    assert signal['instances']==graph['instances']
    assert signal['connections']=={bit:c for bit,c in graph['connections'].items()if not bit.startswith('PG_')}
    assert {n:c['type']for n,c in topology['cells'].items()}==signal['instances']
    function_folder=Path(config['function_run']);function=read(function_folder/'receipt.json')
    assert function['passed']and function['physical_instances']==len(signal['instances'])
    for path,digest in function['inputs'].items():bind(path,digest)
    results=function['initial_results'];assert set(results)=={'initial-1-162.json','initial-2-162.json','initial-2-163.json'}
    for name,result in results.items():
        assert result==read(function_folder/name)
        assert result['passed']and result['real_compositions']==3 and result['cpu_tensor_moves']==0
        commands=[c for c in function['commands']if c['log']==name]
        assert len(commands)==1 and commands[0]['returncode']==0
        bind(function_folder/name,commands[0]['sha256'])
    actual_top=function_folder/'actual-qualified-top.v';bind(actual_top,function['inputs'][str(actual_top)])
    assert actual_top.read_text()==verilog(topology),'Function run is a different wired topology'
    hierarchical=read(function_folder/'hierarchical-inputs.json')
    assert set(hierarchical)==set(manifest['leaves'])
    views={}
    # Each PG delivery explicitly reuses function/LEC through exact complete
    # physical-functional view identity. Compare content hashes, not labels.
    for top,row in manifest['leaves'].items():
        delivery=read(row['fixed_pg_delivery']['path'])
        view=delivery['full_final_netlist'];assert view['passed']
        bind(view['full_view'],view['full_view_sha256'])
        used=hierarchical[top]
        assert used['only_compiler_partition_comment_added']
        assert used['original_sha256']==view['full_view_sha256']
        bind(used['original'],used['original_sha256'])
        assert function['inputs'][used['original']]==used['original_sha256']
        views[top]=view['full_view']
    timing={}
    for variant,folder in config['timing'].items():
        folder=Path(folder);r=read(folder/'receipt.json')
        assert r['execution_passed']and r['actual_upper_distributed_research_rc']
        assert r['research_composed_timing_passed']and r['native_coverage_audit_passed']and r['typed_native_timing_passed']
        assert r['rc_variant']==variant
        assert all(math.isfinite(r[k])and r[k]>=0 for k in ('minimum_setup_ns','minimum_hold_ns'))
        for path in (manifest_path,Path(config['signal_graph']),Path(config['topology']),geometry/'receipt.json'):
            assert r['inputs'][str(path)]==bind(path)
        outputs(folder,r)
        proof=read(folder/'native-system-audit.json');assert proof['passed']and proof['coverage']['passed']and proof['typed']['passed']
        stitch=read(folder/'native-stitch.json')
        assert stitch['passed']and stitch['mode']=='native-access-plus-actual-upper-research-rc'
        assert stitch['upper_rc']['passed']and stitch['upper_rc']['geometry']==str(geometry)and stitch['upper_rc']['variant']==variant
        assert stitch['upper_rc']['net_count']==len(signal['connections'])
        sdc=folder/'combined.sdc';bind(sdc)
        periods=re.findall(r'create_clock[^\n]*-period\s+([\d.]+)',sdc.read_text())
        assert periods and all(float(v)<=10/3+1e-8 for v in periods),'Missing 300MHz constraint'
        assert (folder/'combined.v').read_text()==actual_top.read_text()
        timing[variant]=dict(folder=str(folder),minimum_setup_ns=r['minimum_setup_ns'],minimum_hold_ns=r['minimum_hold_ns'],stitched_spef=stitch['output'],stitched_spef_sha256=stitch['output_sha256'])
    # Deliver complete hierarchical native-cell views, exact actual geometry,
    # and base RC. The low/high complete SPEFs remain in the bound index.
    with (out/'6_final.v').open('w')as stream:
        stream.write(actual_top.read_text())
        for top in sorted(views):
            with Path(views[top]).open()as source:shutil.copyfileobj(source,stream)
    base=Path(config['timing']['base'])
    for name,path in [('6_final.sdc',base/'combined.sdc'),('6_final.spef',base/'stitched-native.spef'),('6_final.def',geometry/'6_final.def'),('6_final.odb',geometry/'6_final.odb'),('6_final.gds',geometry/'6_final.gds'),('layout.png',geometry/'layout.png')]:
        bind(path);shutil.copyfile(path,out/name)
    return dict(passed=True,declared_composition_qualified=True,whole_system_qualified=True,
        qualified_scope='Exact declared six-native programmable reference composition under the unchanged research M11/M12 RC model; R integration unfinished; no manufacturing calibration or EM/IR claim.',
        R_integrated=any(t.startswith('block_v2_r')for t in signal['instances'].values()),
        instance_count=len(signal['instances']),native_types=len(manifest['leaves']),timing=timing,
        real_programs=results,actual_native_views=views,all_actual_geometry_pg_function_rc_bound=True)
