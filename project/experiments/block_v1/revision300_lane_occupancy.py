"""Sample real RTL phase/valid registers during the existing public schedules.

The original benchmark/reference and RTL stay unchanged. Instrumented builds
must reproduce every public result before their extra counters are accepted.
"""
import copy
import json
from pathlib import Path


MONITOR=r'''
#ifdef BENCH_RECURRENT
#include "Vblock_v1_r___024root.h"
#else
#include "Vblock_v1_v___024root.h"
#endif
static void sample_internal(Phase& p) {
 auto*r=dut.rootp;
#ifdef BENCH_RECURRENT
 unsigned state=r->block_v1_r__DOT__phase;
 ++p.internal["phase_"+std::to_string(state)];
 if(state==1||state==3||state==7||state==9||state==11||state==14||state==16)
  p.internal["product_register_write_slots"]+=8;
 if(((state==1||state==9)&&r->block_v1_r__DOT__row_valid)||state==2||state==10)
  p.internal["shadow_state_write_slots"]+=8;
 if(((state==3||state==11)&&r->block_v1_r__DOT__row_valid)||state==4||state==12||state==17)
  p.internal["dot_accumulator_write_slots"]+=8;
#else
 unsigned state=r->block_v1_v__DOT__phase;
 ++p.internal["phase_"+std::to_string(state)];
 if(state==1||state==3||state==13||state==10||state==11||state==18||state==19)
  p.internal["product_register_write_slots"]+=8;
 if(state==22||state==23)p.internal["reduction_tree_capture_cycles"]++;
 if(r->block_v1_v__DOT__function_in) {
  p.internal["function_issue_allocated_slots"]+=2;
  auto sent=r->block_v1_v__DOT__function_sent;
  auto len=r->block_v1_v__DOT__function_length;
  p.internal["function_issue_valid_elements"]+=std::min(2u,unsigned(len-sent));
 }
 if(r->block_v1_v__DOT__function_unit__DOT__valid1)p.internal["function_stage1_valid_slots"]+=2;
 if(r->block_v1_v__DOT__function_unit__DOT__valid2)p.internal["function_stage2_valid_slots"]+=2;
 if(r->block_v1_v__DOT__function_valid)p.internal["function_output_valid_slots"]+=2;
 if(r->block_v1_v__DOT__group_in&&r->block_v1_v__DOT__group_ready)p.internal["group_accepted_operations"]++;
#endif
}
'''


def measure(root,out,cpus,run,kind,variant):
    from io_slots import file_sha
    from revision300_rtl import COMPILER,sources
    assert cpus==16 and kind in ('v','r') and variant in ('revised','extended')
    top,rtls,numeric=sources(root,kind)
    tools=root/'project/experiments/block_v1'
    prior=out.parents[2]/('block-v1-20261029-'+('268'if variant=='revised'else'269'))/'tasks'/('revision300-bench-'+kind+'-'+variant)
    prefetched=kind=='r' and 'reg operand_valid,fetch_done;' in rtls[0].read_text()
    vector_prefetched=kind=='v' and 'M_EXEC=24,P_TOTAL=25,P_ROUND=26' in rtls[0].read_text()
    vector_norm_pipeline=vector_prefetched and 'G_MUL=27,G_ADD=28;' in rtls[0].read_text()
    vector_softmax_pipeline=vector_prefetched and 'F_DRAIN=29,F_DENOM=30;' in rtls[0].read_text()
    vector_function_input=vector_prefetched and 'reg function_input_valid;' in rtls[0].read_text()
    vector_group_subtract=kind=='v' and 'function automatic [130:0] subtract130_grouped;' in (rtls[0].parent/'block_v1_v_group.sv').read_text()
    if vector_prefetched:
        policy=json.loads((tools/'revision300-v-fresh.json').read_text())
        generation='348' if vector_group_subtract else ('336' if vector_function_input else ('329' if vector_softmax_pipeline else ('321' if vector_norm_pipeline else '315')))
        assert policy['function']=='block-v1-20261029-'+generation+'/tasks/revision300-test-v'
        prior=out.parents[2]/('block-v1-20261029-'+generation+'/tasks/revision300-bench-v-'+variant)
    recurrent_base_prefetched=prefetched and 'operand_state_base[0:7],product_state_base[0:7];' in rtls[0].read_text()
    if prefetched:
        # New latency source requires new measured public results, not a
        # comparison against the old236 execution schedule.
        policy=json.loads((tools/'revision300-r-fresh.json').read_text())
        generation='342' if recurrent_base_prefetched else '309'
        assert policy['measurements']=={name:'block-v1-20261029-'+generation+'/tasks/revision300-bench-r-'+name for name in ('revised','extended')}
        prior=out.parents[2]/policy['measurements'][variant]
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']
    report=prior/'revision300-vr-benchmark.json'
    assert file_sha(report)==receipt['outputs'][report.name]
    reference=json.loads(report.read_text())
    # The extended-only additions landed after the common benchmark. Use its
    # exact execution-time benchmark instead of treating current bytes as old.
    original=prior.parents[1]/'src/project/experiments/block_v1/bench_vector_recurrent.cpp'
    assert reference['bench_sha256']==file_sha(original)
    assert reference['numeric_reference_sha256']==file_sha(numeric)
    code=original.read_text()
    assert code.count('std::map<std::string,uint64_t> reasons;')==1
    code=code.replace('std::map<std::string,uint64_t> reasons;',
        'std::map<std::string,uint64_t> reasons,internal;')
    monitor=MONITOR
    if vector_function_input:
        anchor='if(r->block_v1_v__DOT__function_unit__DOT__valid1)'
        assert monitor.count(anchor)==1
        monitor=monitor.replace(anchor,'if(r->block_v1_v__DOT__function_input_valid)p.internal["function_input_registered_valid_slots"]+=2;\n '+anchor)
    if vector_prefetched:
        old='if(state==1||state==3||state==13||state==10||state==11||state==18||state==19)'
        assert monitor.count(old)==1
        monitor=monitor.replace(old,'if(state==24)')
        anchor='if(state==22||state==23)p.internal["reduction_tree_capture_cycles"]++;'
        assert monitor.count(anchor)==1
        monitor=monitor.replace(anchor,anchor+'''
 if(state==1||state==3||state==13||state==10||state==11||state==18||state==19)
  p.internal["operand_register_write_slots"]+=8;
 if(state==25)p.internal["point_total_register_write_slots"]+=8;
 if(state==26)p.internal["point_rounded_register_write_slots"]+=8;
''')
        if vector_norm_pipeline:
            anchor='if(state==26)p.internal["point_rounded_register_write_slots"]+=8;'
            assert monitor.count(anchor)==1
            monitor=monitor.replace(anchor,anchor+'''
 if(state==27)p.internal["norm_epsilon_product_register_writes"]++;
 if(state==28)p.internal["norm_denominator_add_register_writes"]++;
''')
        if vector_softmax_pipeline:
            anchor='if(state==28)p.internal["norm_denominator_add_register_writes"]++;'
            assert monitor.count(anchor)==1
            monitor=monitor.replace(anchor,anchor+'''
 if(state==5&&r->block_v1_v__DOT__composing&&r->block_v1_v__DOT__function_valid)
  p.internal["softmax_pair_sum_register_writes"]++;
 if((state==5&&r->block_v1_v__DOT__composing||state==29)&&r->block_v1_v__DOT__function_pair_valid)
  p.internal["softmax_sum_register_writes"]++;
 if(state==30)p.internal["softmax_denominator_handoff_writes"]++;
''')
    if recurrent_base_prefetched:
        anchor='++p.internal["phase_"+std::to_string(state)];'
        assert monitor.count(anchor)==2
        extra='\n if(state==9&&!r->block_v1_r__DOT__fetch_done)p.internal["update_state_base_fetch_slots"]+=8;\n if(state==9&&r->block_v1_r__DOT__operand_valid)p.internal["update_state_base_product_slots"]+=8;'
        monitor=monitor.replace(anchor,anchor+extra,1)
    if prefetched:
        old='if(state==1||state==3||state==7||state==9||state==11||state==14||state==16)'
        assert monitor.count(old)==1
        monitor=monitor.replace(old,
            'if(((state==1||state==3||state==9||state==11)&&r->block_v1_r__DOT__operand_valid)||state==7||state==14||state==16)')
        anchor='++p.internal["phase_"+std::to_string(state)];'
        assert monitor.count(anchor)==2
        monitor=monitor.replace(anchor,anchor+'''
 if(((state==1||state==3||state==9||state==11)&&!r->block_v1_r__DOT__fetch_done)||state==21||state==22||state==23)
  p.internal["operand_register_write_slots"]+=8;
''',1)
    code=code.replace('static std::map<std::string,Phase> phases;',monitor+'\nstatic std::map<std::string,Phase> phases;')
    assert code.count('++result.reasons[reason];++result.cycles;')==1
    code=code.replace('++result.reasons[reason];++result.cycles;',
        'sample_internal(result);++result.reasons[reason];++result.cycles;')
    anchor='bool f=true;for(auto r:p.reasons)'
    assert code.count(anchor)==1
    # Emit counters as a separate phase field; the original attribution stays exact.
    field='<<",\\\"cycle_attribution\\\":{";'
    assert code.count(field)==1
    code=code.replace(field,'<<",\\\"internal_register_samples\\\":{";')
    code=code.replace(anchor,'''bool q=true;for(auto r:p.internal){if(!q)std::cout<<",";q=false;std::cout<<"\\\""<<r.first<<"\\\":"<<r.second;}
  std::cout<<"},\\\"cycle_attribution\\\":{";
  '''+anchor)
    bench=out/'instrumented.cpp';bench.write_text(code)
    flags='-std=c++17 -O2 -I'+str(tools)+(' -DBENCH_RECURRENT'if kind=='r'else'')+(' -DEXTENDED_VR'if variant=='extended'else'')
    run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--public-flat-rw',
         '--x-initial','unique','--x-assign','unique','--top-module',top,
         '-I'+str(rtls[0].parent),'-Mdir',out/'obj','-CFLAGS',flags]+rtls+[bench],'build.log')
    for path,digest in reference['rtl_sha256'].items():
        current=root/'project'/path.split('/src/project/',1)[1]
        assert file_sha(current)==digest
    result=[]
    for label,initial,seed in [('ones',1,121),('random',2,122)]:
        run([out/'obj'/('V'+top),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],label+'.json')
        value=json.loads((out/(label+'.json')).read_text());assert value['passed']
        public=copy.deepcopy(value)
        for row in public['cases']:
            for phase in row['phases'].values():
                counters=phase.pop('internal_register_samples')
                assert sum(v for k,v in counters.items()if k.startswith('phase_'))==phase['cycles']
        old=copy.deepcopy(reference['measurements'])
        for row in old['cases']:row.pop('modeled_output_gbytes_per_second_at_300mhz')
        assert public==old,'Instrumented run changed public cycles, traffic or numeric checks'
        result.append(value)
    assert result[0]==result[1]
    (out/'revision300-lane-occupancy.json').write_text(json.dumps(dict(passed=True,
        macro=kind.upper(),variant=variant,initial_runs=2,measurements=result[0],
        reference_report_sha256=file_sha(report),reference_receipt_sha256=file_sha(prior/'receipt.json'),
        original_bench_sha256=file_sha(original),instrumented_bench_sha256=file_sha(bench),
        instrument_generator_sha256=file_sha(Path(__file__)),rtl_sha256=reference['rtl_sha256'],
        prefetched_operand_pipeline=prefetched,
        vector_operand_point_pipeline=vector_prefetched,
        vector_norm_denominator_pipeline=vector_norm_pipeline,
        vector_softmax_denominator_pipeline=vector_softmax_pipeline,
        scope='Preedge actual phase/valid/row_valid and, for prefetched R, operand_valid/fetch_done samples during identical source-bound public schedules. Product slots require their actual write enable; V product writes occur only in M_EXEC, operand/total/rounded slots use their separate phases; R operand slots include pipeline fill and single-fetch phases. Function valid tokens counted for each2lane stage, allocated slots include odd tail padding. Ratios may use stated total/phase cycle denominators. These are logical enable/token occupancy, not transistor switching, power, gate-netlist occupancy, or model/system performance.'),indent=2)+'\n')
