"""Compile, independently check and compare a complete 3B finite-loop plan."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from canonicalize import canonicalize
from frontend import import_onnx
from leaf_catalog import read_profiles
from loop_dp import optimize,search
from streaming_ir import compile_graph
from verify_loop_dp import verify
from stream_addresses import check_program_addresses,check_primitive_addresses
from verify_primitive_cost import verify as verify_native_cost


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def replicated_inventory(hardware):
    """Declared #176 resource-count experiment; not new physical acceptance."""
    h=deepcopy(hardware)
    for source,target in [('P0','P1'),('P0','P2'),('U0','U1'),('J0','J1')]:
        meta=deepcopy(h['leaf_inventory'][source]);meta['site']=target+'.S';meta['io_resource']=target+'.S.IO'
        meta['memory_group']=len(h['leaf_inventory']);h['leaf_inventory'][target]=meta
        h['sites'][target+'.S']=deepcopy(h['sites'][source+'.S']);h['sites'][target+'.S'].update(
            io_resource=meta['io_resource'],memory_group=meta['memory_group'])
        for key,value in list(h['resources'].items()):
            if key.startswith(source+'.'):h['resources'][target+key[len(source):]]=value
        for key,value in list(h['nets'].items()):
            if key.startswith(source+'.'):h['nets'][target+key[len(source):]]=deepcopy(value)
    return h


def main():
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('hardware',type=Path)
    p.add_argument('numeric',type=Path);p.add_argument('qualification',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--width',type=int,default=8);p.add_argument('--primitive-program',type=Path,required=True)
    p.add_argument('--read-cache',action='store_true');p.add_argument('--state-cost',action='store_true')
    p.add_argument('--prepare-reuse',action='store_true')
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    m=canonicalize(import_onnx(a.model));h=json.loads(a.hardware.read_text());numeric=json.loads(a.numeric.read_text())
    if numeric['status']!='full_integer_numeric_passed' or numeric['source_sha256']!=m['sha256']:
        raise ValueError('complete real model numerical qualification missing/mismatched')
    # The numerical reference trace has three invocations; types use first run.
    trace=numeric['trace'][:len(m['tasks'])]
    # Generated calibration is compiler state, not another hand-maintained
    # architecture/model input. Preserve real per-weight exponent provenance.
    weight_paths=[Path(f) for f in numeric['inputs'] if f.endswith('/calibration.json')]
    if len(weight_paths)!=1:raise ValueError('quantized weight provenance missing')
    weights=json.loads(weight_paths[0].read_text())
    for name,entry in weights['parameters'].items():
        key='model.'+name
        if key in m['values']:m['values'][key]['numeric_format']=entry['format']
    for t in m.get('offline_weight_recipes',[]):
        src=m['values'][t['inputs'][0]].get('numeric_format')
        if src:m['values'][t['outputs'][0]]['numeric_format']=src.copy()
    for t,row in zip(m['tasks'],trace):
        if t['id']!=row['id']:raise ValueError('numerical trace order differs')
        if row['exponent'] is not None:
            m['values'][t['outputs'][0]]['numeric_format']={'bits':32,'exponent':row['exponent'],'lanes':1,
                'implementation':'S32 records; arithmetic decomposed into native S16 commands'}
    profile=read_profiles([(a.qualification/f'native-{n}.log').read_text() for n in range(3)])
    primitive=None;primitive_numeric=numeric
    if a.primitive_program:
        primitive=json.loads(a.primitive_program.read_text());primitive_numeric=json.loads((a.primitive_program.parent/'report.json').read_text())
        if primitive_numeric['status']!='primitive_program_passed' or primitive['source_sha256']!=m['sha256']:
            raise ValueError('primitive program not numerically qualified for this input')
        if hashlib.sha256(a.primitive_program.read_bytes()).hexdigest()!=primitive_numeric['program_sha256']:
            raise ValueError('qualified primitive program hash differs')
    results=[]
    for label,arch in [('five-groups',h),('nine-groups-count-experiment',replicated_inventory(h))]:
        began=time.monotonic();ir=compile_graph(m,arch,trace,profile,primitive)
        all_spill=search(ir['tasks'],ir['hardware'],width=1)
        all_spill_audit=verify(ir['tasks'],ir['hardware'],all_spill)
        if a.prepare_reuse:
            from preparation_reuse import lower
            ir['all_spill_reference_tasks']=deepcopy(ir['tasks'])
            lower(ir)
        if a.read_cache:
            from dot_cache import variants
            variants(ir,state_cost=a.state_cost)
            ir['optimization_scope']=ir['read_cache_scope']['scope']
        if a.prepare_reuse:
            ir['optimization_scope']+='; '+ir['preparation_reuse_scope']['scope']
        ir['address_check']=check_program_addresses(m,ir['external_regions'])
        if primitive:
            ir['primitive_address_check']=check_primitive_addresses(m,primitive,ir['external_regions'],ir['primitive_regions'],
                [sample['ids'] for sample in primitive_numeric['samples']])
            ir['native_cost_check']=verify_native_cost(ir)
        write(a.output/(label+'-ir.json'),ir)
        # Save the source graph in the IR; replay no longer reads ONNX to pick
        # a different graph or uses floating execution as an unsupported fallback.
        tasks=ir['tasks'];hardware=ir['hardware'];base=search(tasks,hardware,width=1)
        if base['status']!='planned':raise ValueError('full baseline failed '+label)
        base_audit=verify(tasks,hardware,base)
        plan=optimize(tasks,hardware,width=a.width);audit=verify(tasks,hardware,plan)
        row={'scenario':label,'status':'planned','total_graph_nodes':len(m['tasks']),
            'streaming_kernels':len(tasks),'address_views':len(m['tasks'])-len(tasks),
            'private_S_bytes':{s:v['words']*16 for s,v in hardware['sites'].items()},
            'zero_data_prelinks':not any(v.get('fixed') for v in hardware['nets'].values()),
            'baseline_bound':base['makespan'],'search_bound':plan['makespan'],
            'all_spill_bound':all_spill['makespan'],'all_spill_words':all_spill['external_words'],
            'all_spill_audit':all_spill_audit,
            'baseline_wire_cost':base['wire_cost'],'search_wire_cost':plan['wire_cost'],
            'external_transfer_words':plan['external_words'],'required_external_bytes':ir['required_external_bytes'],
            'external_capacity_qualified':ir['capacity_qualified'],'compile_seconds':time.monotonic()-began,
            'audit':audit,'baseline_audit':base_audit,'address_check':ir['address_check'],
            'primitive_address_check':ir.get('primitive_address_check'),'search_statistics':plan['search_statistics'],
            'native_cost_check':ir.get('native_cost_check'),
            'read_cache_scope':ir.get('read_cache_scope'),
            'preparation_reuse_scope':ir.get('preparation_reuse_scope'),
            'read_cache_hits':plan.get('read_cache_hits',0),'read_cache_calls':plan.get('read_cache_calls',0),
            'timing_scope':ir['timing_scope'],'optimization_scope':ir['optimization_scope']}
        write(a.output/(label+'-plan.json'),plan);write(a.output/(label+'-baseline.json'),base)
        write(a.output/(label+'-all-spill.json'),all_spill)
        results.append(row);print(json.dumps(row),flush=True)
        if label=='nine-groups-count-experiment':
            constrained=optimize(tasks,hardware,width=a.width,wire_budget=base['wire_cost'])
            constrained_audit=verify(tasks,hardware,constrained,wire_budget=base['wire_cost'])
            write(a.output/'nine-groups-budget-plan.json',constrained)
            row['equal_wire_budget']={'budget':base['wire_cost'],'bound':constrained['makespan'],
                'wire_cost':constrained['wire_cost'],'audit':constrained_audit}
    write(a.output/'summary.json',{'status':'complete_graph_planning_passed','results':results,
        'op_counts':dict(Counter(t['op'] for t in m['tasks'])),'numeric_checks':primitive_numeric['samples'],
        'primitive_program_sha256':primitive_numeric.get('program_sha256'),
        'evidence_boundary':'whole numerical reference and complete conservative loop plans; no binary/system RTL/physical claim',
        'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.model,a.hardware,a.numeric)}})
    from full_report import main as report_main
    import sys
    sys.argv=['full_report',str(a.output)];report_main()
    if a.read_cache:
        from reuse_report import generate
        generate(a.output)


if __name__=='__main__':main()
