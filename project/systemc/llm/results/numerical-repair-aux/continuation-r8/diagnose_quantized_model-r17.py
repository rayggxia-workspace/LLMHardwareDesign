"""FP32 arithmetic with exported S16 weights, strictly independent diagnostic.

This separates whole-network weight quantization from activation/arithmetic
adaptation. It does not generate or replace any SystemC prediction.
"""
import argparse
import json
import os
from pathlib import Path
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import numpy as np
import torch
from model_support import load_reference
from validate_inference import metric


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkpoint', type=Path)
    ap.add_argument('run', type=Path)
    a = ap.parse_args()
    export = json.loads((a.checkpoint/'export_receipt.json').read_text())
    receipt = json.loads((a.run/'systemc_receipt.json').read_text())
    family = export['config']['model_type']
    if family not in ('phi3', 'qwen2', 'qwen3', 'gemma3_text'):
        raise ValueError('only dense families in this conditional diagnostic')
    torch.set_num_threads(1)
    model = load_reference(export['model_path'])
    targets = model.state_dict()
    raw = np.memmap(a.checkpoint/'weights.bin', dtype='<i2', mode='r')
    copied = set()
    with torch.no_grad():
        for line in (a.checkpoint/'weights.index').read_text().splitlines():
            name, rows, cols, exp, off = line.split()
            if name.startswith('rope.'):
                continue
            rows, cols, exp, off = map(int, (rows, cols, exp, off))
            value = np.ldexp(raw[off//2:off//2+rows*cols].astype('float32'), exp)
            if family == 'gemma3_text' and name.endswith('norm.weight'):
                value = value-1
            targets[name].copy_(torch.from_numpy(value).reshape(targets[name].shape))
            copied.add(name)
    missing = set(targets)-copied
    if export['config']['tie_word_embeddings'] and 'model.embed_tokens.weight' in copied:
        missing.discard('lm_head.weight')
    if missing:
        raise ValueError('unreplaced weights: '+str(sorted(missing)))
    inputs = receipt['inputs']
    if inputs != export['reference_inputs'][:len(inputs)]:
        raise ValueError('this diagnostic requires matching stored reference prefix')
    c = export['config']
    ref = np.memmap(a.checkpoint/'reference_logits.bin', dtype='<f4', mode='r').reshape(-1, c['vocab_size'])
    cache = None
    result = {'scope': 'independent FP32 arithmetic using exported weights; not SystemC inference',
              'family': family, 'steps': []}
    with torch.inference_mode():
        for step, token in enumerate(inputs):
            y = model(input_ids=torch.tensor([[token]]), past_key_values=cache, use_cache=True)
            cache = y.past_key_values
            logits = y.logits[0, -1].numpy()
            result['steps'].append({'step': step, 'top1_equal': int(logits.argmax()) == int(ref[step].argmax()),
                                    'quantized_fp32_top1': int(logits.argmax()), 'logits': metric(logits, ref[step])})
    with (a.run/'quantized-model-diagnostic.json').open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
