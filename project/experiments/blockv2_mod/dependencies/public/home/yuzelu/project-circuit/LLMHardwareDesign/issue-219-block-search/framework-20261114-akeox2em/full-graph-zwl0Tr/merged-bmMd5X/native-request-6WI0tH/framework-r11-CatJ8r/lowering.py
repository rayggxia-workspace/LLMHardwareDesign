"""Shape-driven native service lowering, separate from the mapping algorithm."""
from copy import deepcopy
import math

from frontend import lower_elementwise
from solver import Unsupported


def lower_rows(model, hardware):
    """Whole-row N statistics/replay programs with explicit shared operands.

    This does not split a Softmax/RMS reduction into independent reductions.
    Registered row programs own the full context and consume every element.
    Larger-than-S rows need a registered streamed recipe, not silent padding.
    """
    graph = {'tasks': [], 'values': {}, 'outputs': [], 'source': model.get('source')}
    producer = {n: t['id'] for t in model['tasks'] for n in t['outputs']}
    for t in model['tasks']:
        shape = model['values'][t['outputs'][0]]['shape']
        if not shape or any(not isinstance(d, int) or d < 1 for d in shape):
            raise Unsupported('N row requires resolved positive dimensions')
        length, rows = shape[-1], math.prod(shape[:-1])
        candidates = [(sid, s) for sid, s in hardware['services'].items()
            if s.get('qualified') and s.get('row_replay') and s['row_elements'] == length
            and (s['op'], s['numeric'], s.get('domain', ''), s.get('attributes', {})) ==
                (t['op'], t['numeric'], t.get('domain', ''), t.get('attributes', {}))]
        if not candidates:
            raise Unsupported(f"{t['id']}: no registered complete N row program of length {length}")
        signatures = {(tuple(s['input_words']), tuple(s['output_words']), tuple(s['input_layouts'])) for _, s in candidates}
        if len(signatures) != 1:
            raise Unsupported('row packing variants require separate candidates')
        in_words, out_words, layouts = next(iter(signatures))
        if len(t['inputs']) != len(in_words) or len(t['outputs']) != len(out_words):
            raise Unsupported('N row operand count mismatch')
        for row in range(rows):
            tid, ins, outs = f"{t['id']}@row{row}", [], []
            for kind, names, words_list, target in [('in', t['inputs'], in_words, ins), ('out', t['outputs'], out_words, outs)]:
                for i, (name, words) in enumerate(zip(names, words_list)):
                    layout = layouts[i] if kind == 'in' else 'row'
                    shape_i = model['values'][name]['shape']
                    if (layout == 'row' and shape_i != shape) or (layout == 'shared-row' and shape_i != [length]) or (layout == 'scalar-word' and math.prod(shape_i) != 1):
                        raise Unsupported('N operand shape/layout mismatch: ' + name)
                    index = row if layout == 'row' else 0
                    chunk = f'{name}@row{index}'
                    target.append(chunk)
                    v = {'words': words, 'tensor': name, 'row': index, 'layout': layout}
                    if name in producer:
                        v['producer'] = f'{producer[name]}@row{index}'
                    else:
                        v['site'] = hardware['external']
                    if name in model['outputs']:
                        v['output_site'] = hardware['external']
                        if chunk not in graph['outputs']:
                            graph['outputs'].append(chunk)
                    # A consumer may see a producer output as an ordinary row.
                    if chunk in graph['values']:
                        previous = graph['values'][chunk]
                        if any(previous[k] != v[k] for k in ('words', 'tensor', 'row')):
                            raise Unsupported('shared N row packing differs')
                    else:
                        graph['values'][chunk] = v
            graph['tasks'].append({'id': tid, 'op': t['op'], 'numeric': t['numeric'],
                'domain': t.get('domain', ''), 'attributes': deepcopy(t.get('attributes', {})),
                'inputs': ins, 'outputs': outs, 'alternatives': [sid for sid, _ in candidates]})
    return [graph]


def lower_registered(model, hardware):
    if model.get('lowered'):
        return [model]
    # Do not use model names. Reader/packing boundaries come from capabilities.
    row_ops = {(s['op'], s['numeric'], s['row_elements']) for s in hardware['services'].values() if s.get('row_replay')}
    if all(model['values'][t['outputs'][0]].get('shape') and
           (t['op'], t['numeric'], model['values'][t['outputs'][0]]['shape'][-1]) in row_ops
           for t in model['tasks']):
        return lower_rows(model, hardware)
    return lower_elementwise(model, hardware)
