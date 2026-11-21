"""Source-bound necessary capacity conditions, never a system throughput model.

The bound covers registered dense M/GEMM execution. It grants free S8 operands,
perfect issue, perfect sharding, zero communication and no vector/attention
work. It does not apply to unregistered sparse/low-rank/fast linear algorithms.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError('positive integer required: ' + name)
    return value


def dense_work(config):
    if config.get('model_type') not in ('qwen2', 'qwen3', 'llama') or config.get('hidden_act') != 'silu':
        raise ValueError('unregistered dense gated decoder configuration')
    if any(config.get(name, 1) != 1 for name in ('num_experts', 'num_local_experts', 'num_experts_per_tok')):
        raise ValueError('MoE configuration is not a dense decoder')
    values = {key: positive(config[key], key) for key in (
        'hidden_size', 'num_attention_heads', 'num_key_value_heads',
        'num_hidden_layers', 'intermediate_size', 'vocab_size')}
    h, heads, kv_heads = values['hidden_size'], values['num_attention_heads'], values['num_key_value_heads']
    if 'head_dim' in config:
        dim = positive(config['head_dim'], 'head_dim')
    else:
        if h % heads:
            raise ValueError('hidden size does not determine integral head dimension')
        dim = h // heads
    if heads % kv_heads:
        raise ValueError('unregistered nonintegral grouped-query heads')
    q, kv = heads * dim, kv_heads * dim
    f, layers = values['intermediate_size'], values['num_hidden_layers']
    per_layer = {'q_projection': h*q, 'k_projection': h*kv, 'v_projection': h*kv,
                 'o_projection': q*h, 'gate_projection': h*f, 'up_projection': h*f, 'down_projection': f*h}
    head = h * values['vocab_size']
    return {'per_layer': per_layer, 'layers': layers, 'lm_head': head,
            'products_per_token': layers*sum(per_layer.values())+head,
            'effective_query_dimension': q, 'effective_kv_dimension': kv,
            'scope': 'one B1 decode token, dense projections and full vocabulary head only; attention/vector work excluded'}


def m_contract(source, expected_sha256):
    if hashlib.sha256(source).hexdigest() != expected_sha256:
        raise ValueError('M RTL source hash changed')
    text = source.decode('utf-8')
    product = re.search(r'reg\s+signed\s*\[15:0\]\s+product\[0:(\d+)\]', text)
    issue = re.search(r'if\(state==ISSUE\)begin\s*for\(i=0;i<(\d+);i=i\+1\)product\[i\]<=lhs\[i\]\*rhs\[i\];', text)
    operands = re.search(r'reg\s+signed\s*\[7:0\]\s+lhs\[0:(\d+)\],rhs\[0:(\d+)\]', text)
    if not product or not issue or not operands:
        raise ValueError('unrecognized M source capacity contract')
    lanes = int(product[1])+1
    if [int(operands[1])+1, int(operands[2])+1, int(issue[1])] != [lanes]*3:
        raise ValueError('M lane/issue contract differs')
    if 'product_valid<=state==ISSUE' not in text or 'issue_row<=issue_row+1' not in text:
        raise ValueError('M ISSUE or row-loop contract changed')
    return {'rtl_sha256': expected_sha256, 'narrow_product_bits': 8,
            'optimistic_products_per_cycle': lanes,
            'method': 'pinned native M product array and ISSUE-loop contract; not a generic RTL formal proof',
            'row_handling': 'rows reuse the same product array sequentially',
            'excluded': 'scale lanes are part of the registered M reduction; no separate general GEMM service admitted'}


def audit(root, inventory, workloads):
    hz = positive(inventory['frequency_hz'], 'frequency_hz')
    engines = inventory['engines']
    if not engines or len({e['id'] for e in engines}) != len(engines):
        raise ValueError('unique supplied M instances required')
    evidence = root / inventory['inventory_evidence_path']
    evidence_raw = evidence.read_bytes()
    if hashlib.sha256(evidence_raw).hexdigest() != inventory['inventory_evidence_sha256']:
        raise ValueError('frozen hardware inventory evidence changed')
    recorded = json.loads(evidence_raw)['results']
    if not recorded:
        raise ValueError('frozen inventory contains no qualified result')
    for result in recorded:
        actual = result['diagnostic']['resource_pool_bounds']['native.M']['resources']
        if set(actual) != {e['id'] for e in engines}:
            raise ValueError('supplied engines differ from frozen inventory')
    contracts = {}
    total = 0
    for engine in engines:
        relative = PurePosixPath(engine['rtl_path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('RTL path outside repository')
        path = (root / str(relative)).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('RTL source leaves repository')
        contract = m_contract(path.read_bytes(), engine['rtl_sha256'])
        if positive(engine['products_per_cycle'], 'products_per_cycle') != contract['optimistic_products_per_cycle']:
            raise ValueError('declared products do not match native source')
        contracts[engine['id']] = contract
        total += contract['optimistic_products_per_cycle']
    capacity = total * hz
    rows = []
    for workload in workloads:
        config_path = root / workload['config_path']
        raw = config_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != workload['config_sha256']:
            raise ValueError('official configuration changed')
        work = dense_work(json.loads(raw))
        bound = Fraction(capacity, work['products_per_token'])
        result = {'name': workload['name'], 'configuration': workload,
                  'work': work, 'optimistic_dense_compute_token_s_upper_bound': float(bound),
                  'exact_bound_numerator': bound.numerator, 'exact_bound_denominator': bound.denominator}
        target = workload.get('reference_token_s_decimal')
        if target is not None:
            target = Fraction(target)
            if target <= 0:
                raise ValueError('positive reference throughput required')
            if len({e['products_per_cycle'] for e in engines}) != 1:
                raise ValueError('equivalent-M count requires homogeneous M capacity')
            required = target * work['products_per_token']
            one = hz * engines[0]['products_per_cycle']
            ratio = required/one
            result.update(reference_token_s=float(target),
                          dense_capacity_necessary_condition_met=bound >= target,
                          minimum_equivalent_M_count=(ratio.numerator+ratio.denominator-1)//ratio.denominator,
                          ideal_4bit_weight_bandwidth_bytes_per_s=float(required/2))
        rows.append(result)
    return {'kind': 'necessary_dense_M_capacity_conditions_not_system_simulation',
            'frequency_hz': hz, 'engine_count': len(engines), 'contracts': contracts,
            'optimistic_S8_products_per_second': capacity, 'workloads': rows,
            'assumptions': ['registered dense M/GEMM only; no unproven sparsity/low-rank/fast transforms',
                'free legal S8 operands even though current Qwen integer execution uses wider formats',
                'one product per physical lane every cycle, perfect sharding and no pipeline gaps',
                'zero control/communication/attention/vector/quantization costs; no physical-frequency claim'],
            'not_proven': ['full-model decode values, SystemC token/s, memory bandwidth, energy or physical closure',
                'quality-qualified low-bit execution; an equivalent-M lower bound is not a selected hardware design']}


def crosscheck_graph(proof, expected_work):
    positive(proof['tokens'], 'tokens')
    rows = proof['static_weight_dot_shapes']
    if len({r['id'] for r in rows}) != len(rows) or len(rows) != proof['static_weight_dot_count']:
        raise ValueError('graph Dot coverage differs')
    products = 0
    for row in rows:
        if len(row['shape']) != 3 or row['shape'][:2] != [1, proof['tokens']]:
            raise ValueError('crosscheck requires explicit B1 token axes')
        products += positive(row['shape'][2], 'output columns') * positive(row['K'], 'reduction K') * proof['tokens']
    if products != expected_work['products_per_token'] * proof['tokens']:
        raise ValueError('official shape formula differs from exported graph')
    return {'passed': True, 'static_weight_dot_count': len(rows), 'source_ir_sha256': proof['source_ir_sha256'],
            'products_per_token': products // proof['tokens'],
            'scope': 'frozen exported B1/S2 dense projection shapes; not decode execution qualification'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inventory', type=Path)
    parser.add_argument('workloads', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--graph-evidence', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    result = audit(root, json.loads(args.inventory.read_text()), json.loads(args.workloads.read_text()))
    if args.graph_evidence:
        proof = json.loads(args.graph_evidence.read_text())
        matches = [r for r in result['workloads'] if r['name'] == proof['model']]
        if len(matches) != 1:
            raise ValueError('unknown graph crosscheck model')
        result['graph_crosscheck'] = crosscheck_graph(proof, matches[0]['work'])
        result['graph_evidence_sha256'] = hashlib.sha256(args.graph_evidence.read_bytes()).hexdigest()
    result['input_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.inventory, args.workloads)}
    result['audit_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + '\n', newline='\n')
    print(json.dumps({'kind': result['kind'], 'bounds': [(r['name'],r['optimistic_dense_compute_token_s_upper_bound']) for r in result['workloads']]}))


if __name__ == '__main__':
    main()
