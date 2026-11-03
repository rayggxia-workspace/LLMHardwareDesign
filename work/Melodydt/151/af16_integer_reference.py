"""Independent AF16 composition of previously frozen integer references.

No RTL output is used. Dependencies are explicit formal repository files;
this module adds no host-program or runtime quantization stage.
"""
import importlib.util
from pathlib import Path


REFERENCE_DEPENDENCIES = ['work/Melodydt/151/a16_integer_reference.py',
                          'work/Melodydt/151/f16_integer_reference.py']


def load_reference(root, filename):
    path = Path(root)/'work/Melodydt/151'/filename
    spec = importlib.util.spec_from_file_location('af16_dependency_'+filename[:-3], str(path))
    module = importlib.util.module_from_spec(spec)
    # Compile/exec in memory: never create __pycache__ in the read-only source tree.
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def compose(root, a_input, f_gamma, gate_weights, up_weights, down_weights):
    a = load_reference(root, 'a16_integer_reference.py')
    f = load_reference(root, 'f16_integer_reference.py')
    ar = a.a16(a_input['X'], a_input['gamma'], a_input['Wq'], a_input['Wk'],
               a_input['Wv'], a_input['Wo'], a_input['coeff'])
    fr = [f.f16(row, f_gamma, gate_weights, up_weights, down_weights) for row in ar['final']]
    parameters = []
    for weights in [gate_weights, up_weights, down_weights]:
        word = f.pack([v for col in weights for v in col], 8)
        parameters.extend((word >> (128*i)) & ((1 << 128)-1) for i in range(4))
    parameters.append(f.pack(f_gamma, 16))
    histories = []
    for result in fr:
        history = {448+i: [w] for i, w in enumerate(result['ingress_words'][:16])}
        history[475] = [result['ingress_words'][16]]
        for addr in [466,467,474,448,464,465,468,469,470,471,472,473]:
            word = result['normalized_input_word'] if addr == 448 else result['S_words'][addr]
            history.setdefault(addr, []).append(word)
        assert sum(map(len, history.values())) == 29
        histories.append(history)
    assert len(ar['ingress_words']) == 27 and len(parameters) == 13
    return {'A': ar, 'F': fr, 'F_S_write_history': histories,
            'ingress_words': ar['ingress_words'] + parameters,
            'parameter_words': parameters,
            'A_hidden_words': [f.pack(row,16) for row in ar['final']],
            'final': [r['final'] for r in fr],
            'final_words': [f.pack(r['final'],16) for r in fr],
            'done_saturated': ar['done_saturated'] or any(r['done_saturated'] for r in fr)}
