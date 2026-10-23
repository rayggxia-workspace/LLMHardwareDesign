"""Fresh calibration and untouched short heldout; existing local checkpoint only."""
import argparse
import inspect
import json
import os
from pathlib import Path
import numpy as np
from common import ROOT, config, digest, save, npz, provenance, manifest


def main():
    p = argparse.ArgumentParser(); p.add_argument('--weights', required=True, type=Path)
    p.add_argument('--parent', required=True, type=Path); p.add_argument('--output', required=True, type=Path)
    p.add_argument('--development', action='store_true'); a = p.parse_args()
    if a.output.exists(): raise ValueError('refuse overwrite')
    prod = provenance(a.development); cfg = config()
    if digest(a.parent) != cfg['parent_capture_sha256']: raise ValueError('parent SHA')
    expected = json.loads((ROOT/cfg['model_contract']).read_text())
    receipts = {}
    for name, want in expected['model_files'].items():
        f = a.weights/name; receipts[name] = {'bytes': f.stat().st_size, 'sha256': digest(f)}
        if receipts[name] != want: raise ValueError('model differs '+name)
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch, transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers.models.llama import modeling_llama
    if torch.__version__ != expected['torch_version'] or transformers.__version__ != expected['transformers_version']: raise ValueError('versions')
    impl = inspect.getfile(modeling_llama)
    if digest(impl) != '31bf660a663259134324bc65da4e155951dc89c5ca46471d2325a9938e859e26': raise ValueError('implementation SHA')
    torch.set_num_threads(4); torch.set_num_interop_threads(1); torch.manual_seed(20261023)
    torch.use_deterministic_algorithms(True)
    model = AutoModelForCausalLM.from_pretrained(a.weights, local_files_only=True, trust_remote_code=False,
        use_safetensors=True, dtype=torch.float32, attn_implementation='eager').eval()
    tok = AutoTokenizer.from_pretrained(a.weights, local_files_only=True, trust_remote_code=False)
    frames = []
    def hook(module, args, y): frames.append((args[0][0].detach().numpy().copy(), y[0, :, :16].detach().numpy().copy()))
    layer = model.model.layers[0].mlp.down_proj; handle = layer.register_forward_hook(hook)
    old = np.load(a.parent, allow_pickle=False); arrays = {}
    for name in ['calibration', 'systems', 'arithmetic']:
        for field in ['A', 'Y']: arrays[name+'.'+field] = old[name+'.down_proj.'+field]
    arrays['W'] = old['weight.down_proj']
    if not np.array_equal(layer.weight[:16].detach().numpy(), arrays['W']): raise ValueError('parent weight mismatch')
    inputs = {}; cached_checks = {}
    try:
        with torch.inference_mode():
            for name, text in {**cfg['new_calibration_texts'], 'heldout': cfg['new_heldout_text']}.items():
                n = 40 if name == 'heldout' else 32
                ids = tok(text, add_special_tokens=False, return_tensors='pt')['input_ids'][:, :n].contiguous()
                if ids.shape != (1, n): raise ValueError('text too short')
                frames.clear(); model(input_ids=ids, use_cache=True, logits_to_keep=1)
                if len(frames) != 1: raise ValueError('hook count')
                arrays[name+'.A'], arrays[name+'.Y'] = frames[0]
                inputs[name] = {'text': text, 'tokens': ids.tolist(), 'token_bytes_sha256': __import__('hashlib').sha256(ids.numpy().tobytes()).hexdigest()}
                if name != 'heldout': continue
                frames.clear(); result = model(input_ids=ids[:, :32], use_cache=True, logits_to_keep=1)
                cache = result.past_key_values
                for t in range(32, 40):
                    result = model(input_ids=ids[:, t:t+1], past_key_values=cache, use_cache=True,
                        cache_position=torch.tensor([t]), attention_mask=torch.ones((1, t+1), dtype=torch.long),
                        position_ids=torch.tensor([[t]]), logits_to_keep=1)
                    cache = result.past_key_values
                for ix, field in enumerate(['A', 'Y']):
                    value = np.concatenate([f[ix] for f in frames], axis=0)
                    arrays['heldout.cached_'+field] = value
                    same = bool(np.allclose(value, arrays['heldout.'+field], atol=1e-4, rtol=1e-4))
                    cached_checks[field] = {'passed': same, 'max_abs': float(np.max(abs(value-arrays['heldout.'+field])))}
                    if not same: raise AssertionError('heldout full/cached')
    finally: handle.remove()
    a.output.mkdir(parents=True)
    npz(a.output/'capture.npz', arrays); save(a.output/'inputs.json', inputs)
    manifest(a.output, prod, status='PASS', model_files=receipts, implementation_sha256=digest(impl),
        versions={'torch': torch.__version__, 'transformers': transformers.__version__, 'numpy': np.__version__},
        parent_capture_sha256=digest(a.parent), cached_checks=cached_checks,
        selection='layer0/full K8192/first16 outputs; no full-model quality test; heldout not used for calibration')
    print(json.dumps({'status': 'PASS', 'new_passages': 4, 'heldout_cached': cached_checks}))


if __name__ == '__main__': main()
