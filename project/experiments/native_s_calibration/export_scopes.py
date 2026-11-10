"""Export actual frozen whole-graph scopes for MC capacity audit, not programs.

No timing or tensor simulation is performed. Addresses are the historical
trace's virtual IDs, not a falsely qualified packed deployment DDR image.
"""
import argparse
import hashlib
import json
from pathlib import Path

TRACE_SHA = '6ed2129e2f13842dc53b4ba2135ea41886d1c126d842661dc7d5ac38ffb26f1d'


def export(path):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == TRACE_SHA
    lines = iter(raw.decode().splitlines())
    nt, no, tokens = map(int, next(lines).split())
    tensors = []
    base = 4096
    for i in range(nt):
        identity, elements, bits, initial = map(int, next(lines).split())
        assert identity == i
        tensors.append(dict(id=i, elements=elements, bits=bits, initial=bool(initial), virtual_base=base))
        base += ((elements*bits+8191)//8192)*1024+4096
    ops = []
    for index in range(no):
        row = next(lines).split()
        out, kind = int(row[0]), row[1]
        elements, rows, cols, k, batches, shift, layout, ni = map(int, row[2:10])
        inputs = list(map(int, row[10:]))
        assert len(inputs) == ni
        ops.append(dict(index=index, out=out, kind=kind, elements=elements,
                        rows=rows, cols=cols, k=k, batches=batches, shift=shift, layout=layout, inputs=inputs))
    assert not list(lines)
    scopes = []
    ffn = 0
    cursor = 0
    while cursor < len(ops):
        group = ops[cursor:cursor+5]
        if (len(group) == 5 and [o['kind'] for o in group] == ['Dot', 'Dot', 'SiLU', 'Product', 'Dot'] and
                group[0]['k'] == 2048 and group[0]['cols'] == 11008 and group[4]['k'] == 11008 and group[4]['cols'] == 2048):
            gate, up, activation, product, down = group
            assert gate['inputs'][0] == up['inputs'][0] and activation['inputs'][0] == gate['out']
            assert product['inputs'] == [activation['out'], up['out']] and down['inputs'][0] == product['out']
            scopes.append(dict(scope_id=len(scopes), kind='FFN_candidate_composite', original_op_indices=list(range(cursor,cursor+5)),
                               ffn_ordinal=ffn, layer_index_inferred_not_explicit_in_trace=ffn,
                               source=gate['inputs'][0], weights=[gate['inputs'][1],up['inputs'][1],down['inputs'][1]],
                               out=down['out'], hidden=2048, mid=11008, group_k=128,
                               projection_tile_columns=192, projection_tile_count=58,
                               projection_tile_tail=64, G_normalization_groups=86,
                               P_column_rule='(global_col/8)%3', full_tile_columns_each_P=[64,64,64],
                               tail_columns_each_P=[24,24,16], RF_contexts_each_P=16,
                               G_place='P0', G_gate_up_ring_B=2048, Mid_A16_B_each_P=[7424,7424,7168],
                               implemented_single_LC_FFN_outer_scope=False,
                               requires=['three-P joins','scatter gather with true write ACK','G128 CALL/WAIT',
                                         'native quantizer CALL/WAIT','shift/object/kk association',
                                         'Mid three-source copy/A LOAD','full-K Down context lifetime']))
            ffn += 1
            cursor += 5
        else:
            op = ops[cursor]
            item = dict(scope_id=len(scopes), kind=op['kind'], original_op_indices=[cursor], op=op)
            if op['kind'] == 'Dot':
                static = op['layout'] == 0
                item.update(provider='M_W8A16_static' if static else 'dynamic_S32xS32_UNQUALIFIED',
                            weight_tensor=op['inputs'][1], original_activation_bits=tensors[op['inputs'][0]]['bits'],
                            activation_lowering_required=static, P_instances=[0,1,2],
                            group_k=128 if static else None,
                            head_group_k=16 if op['cols'] == 151936 else 128 if static else None,
                            implemented_outer_scope=False)
            elif op['kind'] != 'Constant':
                item['provider_qualification'] = 'requires explicit E/N/copy native service; not a free MC opcode'
            scopes.append(item)
            cursor += 1
    assert ffn == 36
    dots = [s for s in scopes if s['kind'] == 'Dot']
    return dict(schema='issue250-wholegraph-scope-export/1', trace_SHA256=TRACE_SHA,
                trace_scope='Qwen2.5-3B B1/context512 single decode; all36layers/head/KV ops retained',
                tokens=tokens, original_op_count=len(ops), tensor_count=nt, fused_FFNs=ffn,
                remaining_static_projections=sum(s['op']['layout']==0 for s in dots),
                remaining_dynamic_Dots=sum(s['op']['layout']!=0 for s in dots),
                address_qualification='historical virtual addresses only; deployment image/layout still requires binding',
                program_compiled=False, whole_system_qualified=False, scopes=scopes, tensors=tensors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = export(args.input)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k,v in result.items() if k not in ('scopes','tensors')}))
