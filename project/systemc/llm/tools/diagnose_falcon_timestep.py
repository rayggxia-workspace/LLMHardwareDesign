"""Independent first-layer time-step oracle conditional on actual normalized input."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from validate_inference import metric, tensors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkpoint', type=Path)
    ap.add_argument('run', type=Path)
    a = ap.parse_args()
    export = json.loads((a.checkpoint/'export_receipt.json').read_text())
    c = export['config']
    assert c['model_type'] == 'falcon_h1'
    torch.set_num_threads(1)
    index = {}
    for line in (a.checkpoint/'weights.index').read_text().splitlines():
        name, *row = line.split()
        index[name] = list(map(int, row))
    data = np.memmap(a.checkpoint/'weights.bin', dtype='<i2', mode='r')

    def weight(name):
        rows, cols, e, off = index[name]
        return torch.from_numpy(np.ldexp(data[off//2:off//2+rows*cols].astype('float64').reshape(rows, cols), e))

    # inputnorm trace is the attention input. Undo its known static multiplier
    # then apply SSM input multiplier; no model reference supplies this activation.
    x = torch.from_numpy(tensors(a.run/'stage-inputnorm.bin')[0])
    x = x / c['attention_in_multiplier'] * c['ssm_in_multiplier']
    p = weight('model.layers.0.mamba.in_proj.weight') @ x
    dt = p[-c['mamba_n_heads']:] * c['ssm_multipliers'][4]
    dt = dt + weight('model.layers.0.mamba.dt_bias').flatten()
    expected = torch.nn.functional.softplus(dt).numpy()
    actual = tensors(a.run/'stage-ssm-dt.bin')[0]
    report = {'scope': 'conditional FP64 oracle, quantized weights, first SSM layer/position only',
              'metrics': metric(actual, expected),
              'max_relative_error': float(np.max(np.abs(actual-expected)/(np.abs(expected)+1e-30))),
              'actual': actual.tolist(), 'conditional_reference': expected.tolist(),
              'input_to_softplus': dt.tolist()}
    with (a.run/'timestep-diagnostic.json').open('x') as f:
        json.dump(report, f, indent=2)
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, list)}, indent=2))


if __name__ == '__main__':
    main()
