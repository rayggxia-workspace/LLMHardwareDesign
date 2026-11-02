"""Re-export actual source weights with a safe 15-bit magnitude, no new truth.

References/prompt/metadata are read-only links to an existing export. Static RoPE
tables retain the earlier official construction. Learned tensors are re-read from
the original safetensors; re-scaling the old rounded integers cannot recover bits.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import numpy as np
import torch
from model_support import source_tensors
from export_checkpoint import sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkpoint', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    torch.set_num_threads(1)
    previous = json.loads((a.checkpoint/'export_receipt.json').read_text())
    family = previous['config']['model_type']
    a.output.mkdir(exist_ok=False)
    old_index = {}
    for line in (a.checkpoint/'weights.index').read_text().splitlines():
        name, rows, cols, e, off = line.split()
        old_index[name] = tuple(map(int, (rows, cols, e, off)))
    source = Path(previous['model_path'])
    for row in previous['source_files']:
        p = Path(row['path'])
        if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise ValueError('source checkpoint changed: '+str(p))
    index, tensors, offset = [], [], 0
    with (a.output/'weights.bin').open('xb') as f:
        for original, name, value in source_tensors(source, family):
            if family in ('gemma3_text', 'qwen3_5_text') and name.endswith('norm.weight') and '.linear_attn.norm.' not in name:
                value = value+1
            if name.endswith('.A_log'):
                name, value = name.replace('A_log', 'A_exp'), value.exp()
            if '.conv1d.weight' in name:
                value = value.squeeze(1)
            rows = value.numel()//value.shape[-1] if value.ndim > 1 else 1
            cols = value.shape[-1]
            if (rows, cols) != old_index[name][:2]:
                raise ValueError('shape mismatch: '+name)
            peak = float(value.abs().max())
            e = math.ceil(math.log2(peak/32767)) if peak else -15
            quantized = torch.round(value/math.ldexp(1., e))
            if bool(((quantized > 32767) | (quantized < -32768)).any()):
                raise ValueError('unsafe rounded output: '+name)
            raw = quantized.to(torch.int16).numpy().astype('<i2', copy=False).tobytes()
            index.append((name, rows, cols, e, offset))
            tensors.append({'name': name, 'shape': list(value.shape), 'exponent': e, 'clipped': 0})
            f.write(raw)
            offset += len(raw)
        with (a.checkpoint/'weights.bin').open('rb') as old:
            for name, (rows, cols, e, off) in old_index.items():
                if not name.startswith('rope.'):
                    continue
                old.seek(off)
                raw = old.read(rows*cols*2)
                if len(raw) != rows*cols*2:
                    raise ValueError('truncated static table')
                index.append((name, rows, cols, e, offset))
                f.write(raw)
                offset += len(raw)
    if {row[0] for row in index} != set(old_index):
        raise ValueError('incomplete tensor re-export')
    (a.output/'weights.index').write_text('\n'.join(' '.join(map(str, row)) for row in index)+'\n')
    for name in ('metadata.txt', 'prompt.txt', 'reference_hidden.bin', 'reference_logits.bin'):
        (a.output/name).symlink_to((a.checkpoint/name).resolve())
    report = dict(previous)
    report.update(tensors=tensors, weights_sha256=sha(a.output/'weights.bin'),
                  quantization='S16 per-tensor power-of-two scale, 15 magnitude bits, no clipping',
                  previous_export=str(a.checkpoint.resolve()),
                  previous_receipt_sha256=sha(a.checkpoint/'export_receipt.json'),
                  exporter_sha256=sha(__file__),
                  reference_reused_from=str(a.checkpoint.resolve()),
                  static_rope='retained exact earlier exported official table bytes and exponents')
    (a.output/'export_receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print('REEXPORT', offset, 'bytes; original parameters; independent stored FP32 truth unchanged')


if __name__ == '__main__':
    main()
