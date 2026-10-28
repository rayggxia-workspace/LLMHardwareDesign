"""Actual unchanged-M measurements at repository model dimensions, six groups."""
import json
from pathlib import Path


def measure(root,out,cpus,run,group):
    from io_slots import file_sha
    from revision300_rtl import COMPILER
    assert cpus==16 and group in range(6)
    specification=root/'project/experiments/block_v1/revision300-model-m-shapes.json'
    spec=json.loads(specification.read_text())
    assert spec['schema']=='revision300-model-m-shapes/1'
    shapes=spec['groups'][group]
    assert len(shapes) in (3,4) and all(k>0 and 0<n<=8 for k,n in shapes)
    source=root/'project/experiments/block_v1/bench_matrix_macro.cpp'
    text=source.read_text()
    needle='const std::array<std::array<unsigned,2>,4> shapes={{{1024,8},{65,7},{9,1},{3072,8}}};'
    assert text.count(needle)==1
    replacement='const std::array<std::array<unsigned,2>,%d> shapes={{'%len(shapes)
    replacement+=','.join('{%d,%d}'%tuple(s)for s in shapes)+'}};'
    generated=out/'model-shape-bench.cpp'
    generated.write_text(text.replace(needle,replacement))
    assert generated.read_text().replace(replacement,needle)==text
    rtl=root/'project/rtl/block_library_v1/block_v1_m.sv'
    accepted=out.parents[2]/'block-v1-20261029-258/tasks/revision300-final-source-m'
    receipt=json.loads((accepted/'receipt.json').read_text());assert receipt['passed']
    proof=accepted/'revision300-final-source.json'
    assert file_sha(proof)==receipt['outputs'][proof.name]
    native=json.loads(proof.read_text())
    assert file_sha(rtl)==native['rtl_sha256'][str(rtl.relative_to(root))]
    run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--public-flat-rw',
         '--x-initial','unique','--x-assign','unique','--top-module','block_v1_m',
         '-Mdir',out/'obj','-CFLAGS','-std=c++17 -O2 -DBENCH_REVISED',rtl,generated],'build.log')
    observed=[]
    for label,initial,seed in [('ones',1,121),('random',2,122)]:
        run([out/'obj/Vblock_v1_m','packed','+verilator+rand+reset+'+str(initial),
             '+verilator+seed+'+str(seed)],label+'.json')
        d=json.loads((out/(label+'.json')).read_text())
        assert d['passed'] and len(d['cases'])==16*len(shapes)
        keys=set()
        for row in d['cases']:
            shape=[row['logical_k'],row['logical_n']];assert shape in shapes
            key=tuple(shape)+(row['format_a_bits'],row['format_b_bits'],row['scenario'])
            assert key not in keys;keys.add(key)
            phases=[row[x]for x in ('preload','work','finalization_and_readback')]
            assert row['total_cycles']==sum(p['cycles']for p in phases)
            assert row['logical_macs']==shape[0]*shape[1]
            for p in phases:
                assert p['cycles']==sum(p['cycle_attribution'].values())
                assert p['accepted_commands']==p['retired_responses']
                assert p['command_container_bytes']==16*p['accepted_commands']
                assert p['response_container_bytes']==16*p['retired_responses']
            assert row['work']['resource_occupancy_may_overlap']['valid_s8_digit_products']==row['logical_macs']*row['base_s8_products_per_logical_mac']
        observed.append(d)
    assert observed[0]==observed[1]
    result=dict(passed=True,group=group,shapes=shapes,initial_runs=2,
        specification_sha256=file_sha(specification),original_bench_sha256=file_sha(source),
        generated_bench_sha256=file_sha(generated),only_shape_array_changed=True,
        rtl_sha256=file_sha(rtl),accepted_m_source_receipt_sha256=file_sha(accepted/'receipt.json'),
        compiler_sha256=file_sha(Path(COMPILER)),measurements=observed[0],
        model_performance_qualified=False,model_integer_quality_qualified=False,
        scope=spec['logical_scope'])
    (out/'revision300-model-m-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
