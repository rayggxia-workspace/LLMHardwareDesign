"""Split expert weights into two S16 terms, with an allocated-node-only export.

High terms are the existing N8 export. Low terms are quantized from original
checkpoint minus decoded high weights. No activation calibration or token labels.
Both terms are accumulated inside M before its single final narrowing.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import numpy as np
import torch
from model_support import source_tensors
from export_checkpoint import sha


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('checkpoint', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    torch.set_num_threads(1)
    report = json.loads((a.checkpoint/'export_receipt.json').read_text())
    if report['config']['model_type'] != 'granitemoe':
        raise ValueError('this schema targets packed Granite expert matrices')
    for row in report['source_files']:
        p = Path(row['path'])
        if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise ValueError('original checkpoint changed')
    if sha(a.checkpoint/'weights.bin') != report['weights_sha256']:
        raise ValueError('high weight export changed')
    index = {}
    for line in (a.checkpoint/'weights.index').read_text().splitlines():
        name, *row = line.split()
        index[name] = list(map(int, row))
    scales = {}
    for line in (a.checkpoint/'weights.scales').read_text().splitlines():
        name, count, *es = line.split()
        if len(es) != int(count):
            raise ValueError('invalid high scales')
        scales[name] = np.array(list(map(int, es)), dtype=np.int32)
    a.output.mkdir(exist_ok=False)
    shutil.copyfile(a.checkpoint/'weights.bin', a.output/'weights.bin')
    raw = np.memmap(a.checkpoint/'weights.bin', dtype='<i2', mode='r')
    offset = (a.output/'weights.bin').stat().st_size
    new_index, new_scales, stats = [], [], []
    with (a.output/'weights.bin').open('ab') as output:
        for _, name, value in source_tensors(report['model_path'], 'granitemoe'):
            if not name.endswith(('.input_linear.weight', '.output_linear.weight')):
                continue
            rows, cols, _, off = index[name]
            if rows % 8 or name not in scales:
                raise ValueError('expert must have aligned N8 high scales')
            high_e = torch.from_numpy(scales[name])
            high = torch.from_numpy(raw[off//2:off//2+rows*cols].astype('float32').reshape(-1, 8, cols))
            high = torch.ldexp(high, high_e[:, None, None])
            original = value.reshape(-1, 8, cols)
            residual = original-high
            peak = residual.abs().flatten(1).amax(1)
            low_e = torch.where(peak > 0, torch.ceil(torch.log2(peak/32767)), high_e-15).int()
            low_e = torch.maximum(low_e, high_e-20)
            if bool((low_e > high_e).any()):
                raise ValueError('residual exponent is coarser than high term')
            q = torch.round(torch.ldexp(residual, -low_e[:, None, None]))
            if bool(((q < -32768) | (q > 32767)).any()):
                raise ValueError('residual clips')
            error = torch.ldexp(q, low_e[:, None, None])-residual
            data = q.to(torch.int16).numpy().astype('<i2', copy=False).tobytes()
            output.write(data)
            new_index.append((name+'.low', rows, cols, int(low_e[0]), offset))
            es = low_e.tolist()
            new_scales.append(name+'.low '+str(len(es))+' '+' '.join(map(str, es)))
            stats.append(dict(name=name, bytes=len(data), clipped=0,
                              max_absolute_reconstruction_error=float(error.abs().max()),
                              relative_l2_reconstruction_error=float(error.double().norm()/original.double().norm()),
                              changed_values=int((error != 0).sum()),
                              max_exponent_difference=int((high_e-low_e).max())))
            offset += len(data)
    if not new_index:
        raise ValueError('no expert weights found')
    (a.output/'weights.index').write_text((a.checkpoint/'weights.index').read_text().rstrip()+'\n'+
                                        '\n'.join(' '.join(map(str, r)) for r in new_index)+'\n')
    (a.output/'weights.scales').write_text((a.checkpoint/'weights.scales').read_text().rstrip()+'\n'+
                                         '\n'.join(new_scales)+'\n')
    (a.output/'metadata.txt').write_text((a.checkpoint/'metadata.txt').read_text().rstrip()+'\nweight_residual_terms 2\n')
    for name in ('prompt.txt', 'reference_hidden.bin', 'reference_logits.bin'):
        (a.output/name).symlink_to((a.checkpoint/name).resolve())
    report.update(previous_export=str(a.checkpoint.resolve()),
                  previous_receipt_sha256=sha(a.checkpoint/'export_receipt.json'),
                  weights_sha256=sha(a.output/'weights.bin'),
                  weight_scales_sha256=sha(a.output/'weights.scales'),
                  exporter_sha256=sha(Path(__file__)), expert_residuals=stats,
                  weight_scale_policy='N8 primary weights plus expert residual S16 terms; M accumulation before RNE; no calibration',
                  reference_reused_from=str(a.checkpoint.resolve()))
    (a.output/'export_receipt.json').write_text(json.dumps(report, indent=2)+'\n')
    print('EXPERT_RESIDUAL_EXPORT', offset, 'bytes', len(stats), 'matrices', flush=True)


if __name__ == '__main__':
    main()
