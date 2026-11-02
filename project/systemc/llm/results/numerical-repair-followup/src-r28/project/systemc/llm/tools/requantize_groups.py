"""S16 weights with one exponent per M N8 output group, no activation calibration.

Re-read original learned matrix parameters. Preserve all other exported parameter
bytes, metadata, input and independent references. No checkpoint/old export edits.
"""
import argparse
import json
import math
from pathlib import Path
import torch
import numpy as np
from model_support import source_tensors
from export_checkpoint import sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkpoint', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    torch.set_num_threads(1)
    report = json.loads((a.checkpoint/'export_receipt.json').read_text())
    original_base = Path(report.get('metadata_repair', {}).get('previous_export', a.checkpoint)).parent
    model_path = Path(report['model_path'])
    if not model_path.is_absolute():
        model_path = (original_base/model_path).resolve()
    report['model_path'] = str(model_path)
    for row in report['source_files']:
        p = Path(row['path'])
        if not p.is_absolute():
            row['path'] = str((original_base/p).resolve())
    fixture = model_path/'fixture-scope.json'
    if fixture.exists():
        report['fixture_provenance'] = json.loads(fixture.read_text())
        report['scope'] = report['fixture_provenance']['scope']
    family = report['config']['model_type']
    old = {}
    for line in (a.checkpoint/'weights.index').read_text().splitlines():
        name, *row = line.split()
        old[name] = list(map(int, row))
    for row in report['source_files']:
        p = Path(row['path'])
        if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise ValueError('source changed: '+str(p))
    a.output.mkdir(exist_ok=False)
    index, scales, stats, seen, offset = [], [], [], set(), 0
    with (a.checkpoint/'weights.bin').open('rb') as previous, (a.output/'weights.bin').open('xb') as output:
        def preserve(name):
            nonlocal offset
            rows, cols, e, off = old[name]
            previous.seek(off)
            raw = previous.read(rows*cols*2)
            if len(raw) != rows*cols*2:
                raise ValueError('truncated previous parameter')
            output.write(raw)
            index.append((name, rows, cols, e, offset))
            offset += len(raw)
            seen.add(name)
        for original, name, value in source_tensors(model_path, family):
            if name.endswith('.A_log'):
                name = name.replace('A_log', 'A_exp')
            if value.ndim < 2 or '.conv1d.weight' in name:
                preserve(name)
                continue
            rows, cols, old_e, _ = old[name]
            if value.numel() != rows*cols:
                raise ValueError('matrix shape changed: '+name)
            matrix = value.reshape(rows, cols)
            groups = (rows+7)//8
            if rows % 8:
                matrix = torch.nn.functional.pad(matrix, (0, 0, 0, groups*8-rows))
            block = matrix.reshape(groups, 8, cols)
            peak = block.abs().flatten(1).amax(1)
            exponents = torch.where(peak > 0, torch.ceil(torch.log2(peak/16383)), torch.full_like(peak, -14))
            quantized = torch.round(block/torch.exp2(exponents)[:, None, None])
            if bool(((quantized > 32767) | (quantized < -32768)).any()):
                raise ValueError('group quantization clips: '+name)
            raw = quantized.reshape(groups*8, cols)[:rows].to(torch.int16).numpy().astype('<i2', copy=False).tobytes()
            output.write(raw)
            index.append((name, rows, cols, old_e, offset))
            e = exponents.to(torch.int32).tolist()
            scales.append(name+' '+str(groups)+' '+' '.join(map(str, e)))
            stats.append({'name': name, 'groups': groups, 'min_exponent': min(e), 'max_exponent': max(e), 'clipped': 0})
            offset += len(raw)
            seen.add(name)
        for name in old:
            if name.startswith('rope.'):
                preserve(name)
    if seen != set(old):
        raise ValueError('unmapped exported parameters: '+str(set(old)-seen))
    (a.output/'weights.index').write_text('\n'.join(' '.join(map(str, row)) for row in index)+'\n')
    (a.output/'weights.scales').write_text('\n'.join(scales)+'\n')
    md=(a.checkpoint/'metadata.txt').read_text().rstrip()+'\nweight_group_rows 8\n'
    (a.output/'metadata.txt').write_text(md)
    for name in ('prompt.txt', 'reference_hidden.bin', 'reference_logits.bin'):
        (a.output/name).symlink_to((a.checkpoint/name).resolve())
    report.update(weight_scale_policy='learned matrices: independent power-of-two exponent per output N8; 14 magnitude bits; no activation calibration',
                  weight_groups=stats, weights_sha256=sha(a.output/'weights.bin'),
                  weight_scales_sha256=sha(a.output/'weights.scales'),
                  previous_export=str(a.checkpoint.resolve()), previous_receipt_sha256=sha(a.checkpoint/'export_receipt.json'),
                  exporter_sha256=sha(Path(__file__)), nonmatrix_parameters='exact previous exported bytes',
                  reference_reused_from=str(a.checkpoint.resolve()))
    (a.output/'export_receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print('GROUP_EXPORT', offset, 'bytes', len(stats), 'learned matrices; zero clips')


if __name__ == '__main__':
    main()
