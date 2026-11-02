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
    ap.add_argument('--restore-group', choices=('none', 'router', 'norm', 'experts','conv','state_parameters','nonmatrix'), default='none')
    ap.add_argument('--out',type=Path,help='New diagnostic file, separate from immutable inference outputs')
    a = ap.parse_args()
    export = json.loads((a.checkpoint/'export_receipt.json').read_text())
    receipt = json.loads((a.run/'systemc_receipt.json').read_text())
    family = export['config']['model_type']
    if family not in ('phi3', 'qwen2', 'qwen3', 'gemma3_text', 'granitemoe','falcon_h1'):
        raise ValueError('unsupported family in this conditional diagnostic')
    torch.set_num_threads(1)
    if family == 'granitemoe':
        from transformers import AutoModelForCausalLM
        model = AutoModelForCausalLM.from_pretrained(export['model_path'], local_files_only=True,
                                                    dtype=torch.float32, attn_implementation='eager').eval()
    else:
        model = load_reference(export['model_path'])
    targets = model.state_dict()
    raw = np.memmap(a.checkpoint/'weights.bin', dtype='<i2', mode='r')
    group_scales = {}
    if (a.checkpoint/'weights.scales').exists():
        for line in (a.checkpoint/'weights.scales').read_text().splitlines():
            name, count, *exponents = line.split()
            if len(exponents) != int(count):
                raise ValueError('invalid group scales')
            group_scales[name] = np.array(list(map(int, exponents)))
    index = {row.split()[0]:list(map(int,row.split()[1:])) for row in (a.checkpoint/'weights.index').read_text().splitlines()}
    parameter_scales={}
    if (a.checkpoint/'parameters.scales').exists():
        for line in (a.checkpoint/'parameters.scales').read_text().splitlines():
            name,elements,group,count,*es=line.split();elements,group,count=map(int,(elements,group,count))
            assert count==len(es)==(elements+group-1)//group
            parameter_scales[name]=np.repeat(np.array(list(map(int,es))),group)[:elements]
    copied = set()
    restored = []
    with torch.no_grad():
        for line in (a.checkpoint/'weights.index').read_text().splitlines():
            name, rows, cols, exp, off = line.split()
            if name.startswith('rope.') or name.endswith('.low'):
                continue
            stored_name = name
            if family == 'granitemoe':
                name = name.replace('.router.layer.weight', '.router.weight')
                name = name.replace('.input_linear.weight', '.experts.gate_up_proj')
                name = name.replace('.output_linear.weight', '.experts.down_proj')
            if family=='falcon_h1' and name.endswith('.A_exp'):
                name=name[:-len('A_exp')]+'A_log'
            restore = ((a.restore_group == 'router' and '.router.weight' in name) or
                       (a.restore_group == 'norm' and name.endswith('norm.weight')) or
                       (a.restore_group == 'experts' and '.experts.' in name)or
                       (a.restore_group=='conv' and '.conv1d.' in name)or
                       (a.restore_group=='state_parameters' and name.endswith(('.A_log','.dt_bias','.D')))or
                       (a.restore_group=='nonmatrix' and (targets[name].ndim<2 or '.conv1d.'in name)))
            if restore:
                if name not in targets:
                    raise ValueError('unknown restored target: '+name)
                copied.add(name)
                restored.append(name)
                continue
            rows, cols, exp, off = map(int, (rows, cols, exp, off))
            values = raw[off//2:off//2+rows*cols].astype('float32').reshape(rows, cols)
            exponents = group_scales[stored_name][np.arange(rows)//8, None] if stored_name in group_scales else exp
            if stored_name in parameter_scales:exponents=parameter_scales[stored_name].reshape(rows,cols)
            value = np.ldexp(values, exponents)
            if stored_name+'.low' in index:
                lr,lc,le,lo = index[stored_name+'.low']
                if (lr,lc) != (rows,cols):raise ValueError('residual shape')
                low = raw[lo//2:lo//2+lr*lc].astype('float32').reshape(lr,lc)
                low_e = group_scales[stored_name+'.low'][np.arange(lr)//8,None]
                value += np.ldexp(low,low_e)
            if family == 'gemma3_text' and name.endswith('norm.weight'):
                value = value-1
            if family=='falcon_h1' and stored_name.endswith('.A_exp'):
                # Only the independent oracle reconstructs the stored parameter.
                # The simulator continues to use offline A_exp and real R commands.
                value=np.log(value)
            targets[name].copy_(torch.from_numpy(value).reshape(targets[name].shape))
            copied.add(name)
    missing = set(targets)-copied
    if export['config']['tie_word_embeddings'] and 'model.embed_tokens.weight' in copied:
        missing.discard('lm_head.weight')
    if missing:
        raise ValueError('unreplaced weights: '+str(sorted(missing)))
    actual_inputs = receipt['inputs']
    matched = 0
    for actual, reference in zip(actual_inputs, export['reference_inputs']):
        if actual != reference:
            break
        matched += 1
    if not matched:
        raise ValueError('no matching stored reference prefix')
    inputs = actual_inputs[:matched]
    c = export['config']
    ref = np.memmap(a.checkpoint/'reference_logits.bin', dtype='<f4', mode='r').reshape(-1, c['vocab_size'])
    ref_hidden = np.memmap(a.checkpoint/'reference_hidden.bin',dtype='<f4',mode='r').reshape(-1,c['num_hidden_layers']+1,c['hidden_size'])
    cache = None
    result = {'scope': 'independent FP32 arithmetic using exported weights; not SystemC inference',
              'family': family, 'systemc_processing_positions': len(actual_inputs),
              'restored_original_parameter_group': a.restore_group,
              'restored_original_parameters': restored,
              'compared_prefix_positions': matched,
              'omitted_positions_reason': 'stored reference prefix differs' if matched < len(actual_inputs) else None,
              'steps': []}
    with torch.inference_mode():
        for step, token in enumerate(inputs):
            y = model(input_ids=torch.tensor([[token]]), past_key_values=cache, use_cache=True, output_hidden_states=True)
            cache = y.past_key_values
            logits = y.logits[0, -1].numpy()
            result['steps'].append({'step': step, 'top1_equal': int(logits.argmax()) == int(ref[step].argmax()),
                                    'quantized_fp32_top1': int(logits.argmax()), 'logits': metric(logits, ref[step]),
                                    'hidden':[metric(h[0,-1].numpy(),ref_hidden[step,i])for i,h in enumerate(y.hidden_states)]})
    with (a.out or a.run/'quantized-model-diagnostic.json').open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
