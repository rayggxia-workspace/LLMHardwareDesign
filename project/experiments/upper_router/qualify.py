"""Gate a complete physical handoff against actual hash-bound backend evidence.

Qualification is limited to the declared input netlist and research RC stack.
It never promotes a resource-library regression to whole-model qualification.
"""
import argparse
import json
from pathlib import Path
import shutil
from check import digest,verify
from native_inventory import sha


def qualify(manifest,out,copy=False):
    assert manifest['schema_version']=='upper-router-backend-delivery/1'
    paths={k:Path(v) for k,v in manifest['paths'].items()}
    read=lambda p:json.loads(Path(p).read_text())
    spec,routes,binding=(read(paths[k]) for k in ('spec','routes','binding'))
    verify(spec,routes);assert not routes['failed']
    assert binding['spec_sha256']==digest(spec) and binding['route_sha256']==digest(routes)
    geometry=read(paths['geometry_receipt']);assert geometry['geometry_passed'] and geometry['native_geometry_xor_zero']
    assert geometry['native_hierarchy_identity']['passed']
    assert geometry['net_count']==len(binding['nets'])
    for key,label in [('upper_def','upper.def'),('upper_odb','upper.odb'),('combined_gds','combined.gds'),('native_gds','native.gds')]:
        assert sha(paths[key])==geometry['sha256'][label],('changed geometry artifact',key)
    physical=read(paths['flat_equivalence']);assert physical['passed']
    assert physical['all_native_metal_and_pin_unions_xor_zero'] and physical['all_upper_geometry_xor_zero']
    assert physical['actual_component_placements_and_models_equal']
    assert physical['upper_nets_compared']==len(binding['nets']) and physical['binding_sha256']==sha(paths['binding'])
    for key,label in [('flat_odb','assembled.odb'),('flat_verilog','assembled.v')]:
        assert physical['artifact_sha256'][label]==sha(paths[key]),('changed flat artifact',key)
    drc=read(paths['drc_receipt'])
    assert drc['passed'] and drc['full_original_native_deck_items']==0
    assert drc['combined_gds_sha256']==sha(paths['combined_gds'])
    topology=read(paths['topology']/'topology.json')
    assert topology['passed'] and topology['source_gds']['sha256']==sha(paths['native_gds'])
    assert topology['database_sha256']==sha(paths['topology']/'native.l2n')
    from native_connectivity_audit import audit
    assert topology['inventory_sha256']==sha(paths['topology_inventory'])
    connectivity=audit(read(paths['topology_inventory']),topology)
    ends={p for n in binding['nets'].values() for p in [n['driver']]+n['sinks']}
    assert ends<=set(topology['boundary_probes'])
    scene=read(paths['scene']/'scene.json');field=read(paths['field']/'solve.json')
    assert scene['complete_native_context'] and field['passed'] and field['complete_master_coverage']
    assert scene['scene_sha256']==field['scene_sha256']==sha(paths['scene']/'scene.bin')
    assert field['rows_sha256']==sha(paths['field']/'rows.jsonl')
    assert scene['graph_sha256']==sha(paths['graph'])
    assert scene['topology_sha256']==sha(paths['topology']/'topology.json')
    rows=[json.loads(s) for s in (paths['field']/'rows.jsonl').read_text().splitlines()]
    assert [r['master'] for r in rows]==field['masters']==list(range(len(binding['nets'])))
    assert {r['net'] for r in rows}==set(binding['nets'])
    for row in rows:
        c=sum(v[0] for v in row['node_self']);error=sum(v[1] for v in row['node_self'])
        assert c>0 and 0<=error/c<=.02 and 0<=row['sigma_ff']/row['total_ff']<=.003
        assert abs(sum(v[0] for v in row['values']))<1e-8*row['total_ff']
    control=read(paths['controls']/'controls.json');built=read(paths['build']/'build.json')
    assert control['passed'] and control['binary_sha256']==built['binary_sha256']==field['binary_sha256']==sha(paths['build']/'native_field')
    assert field['controls_sha256']==sha(paths['controls']/'controls.json')
    # Recompute the final timing gate; a stale passed timing.json is not enough.
    from timing_receipt import collect
    timing=collect(paths['sta']);assert timing['passed'] and len(timing['variants'])==9
    views=read(paths['flat_views'])
    for template,v in views.items():
        for kind,refs in v['views'].items():
            for ref in refs:assert ref['sha256']==sha(ref['path']),('changed physical/electrical view',template,kind)
    delivery={'design.def':paths['flat_def'],'design.odb':paths['flat_odb'],
              'design.v':paths['flat_verilog'],'design.gds':paths['combined_gds'],
              'design.spef':paths['sta']/'distributed-coupling-1.spef','design.sdc':paths['sta']/'input.sdc'}
    out.mkdir();artifacts={}
    for name,path in delivery.items():
        fingerprint=sha(path)
        if copy:
            shutil.copyfile(path,out/name);assert sha(out/name)==fingerprint
        artifacts[name]={'path':str(out/name if copy else path),'sha256':fingerprint,'bytes':path.stat().st_size}
    gates={k:{'path':str(paths[k]),'sha256':sha(paths[k])} for k in ('geometry_receipt','flat_equivalence','drc_receipt','binding')}
    result={'passed':True,'physical_qualified':True,'net_count':len(binding['nets']),
            'coverage':manifest['coverage'],'whole_model_physical_qualified':False,
            'qualification':'declared input netlist; original TT300MHz resource constraints; explicit research M11/M12 RC stack',
            'artifacts':artifacts,'gates':gates,'timing_variants':timing['variants'],
            'manifest_sha256':digest(manifest),'native_geometry_unchanged':True,
            'native_connectivity':connectivity,
            'field_method':'fresh joint full-native-geometry field C, exact routed R, original accepted native RC; node/Miller sensitivity',
            'not_claimed':['foundry-calibrated 12-layer signoff','unexecuted model/RTL/system qualification']}
    (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--copy',action='store_true');a=p.parse_args();qualify(json.loads(a.manifest.read_text()),a.output,a.copy)
