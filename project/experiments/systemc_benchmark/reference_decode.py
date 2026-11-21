"""Generate pinned HF cached-decode oracle; host time is NOT device timing.

Checks cached decoding against full-prefix forwards at multiple positions.
Only final-row logits are requested to avoid giant prefill vocabulary tensors.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('checkpoint', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--prompt-tokens', type=int, required=True)
    p.add_argument('--decode-steps', type=int, default=128)
    p.add_argument('--prompt-variant', type=int, default=0)
    p.add_argument('--threads', type=int, default=10)
    a = p.parse_args()
    if min(a.prompt_tokens, a.decode_steps, a.threads) < 1:
        raise ValueError('positive scope required')
    a.output.mkdir(exist_ok=False)
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    tokenizer = AutoTokenizer.from_pretrained(str(a.checkpoint), local_files_only=True)
    prompts = [
        'Explain how a computer stores and retrieves information. Give precise examples. ',
        'A researcher compares several ways of scheduling matrix operations and moving data. ']
    base = tokenizer.encode(prompts[a.prompt_variant % len(prompts)], add_special_tokens=False)
    ids = (base * ((a.prompt_tokens + len(base) - 1) // len(base)))[:a.prompt_tokens]
    model = AutoModelForCausalLM.from_pretrained(
        str(a.checkpoint), local_files_only=True, torch_dtype=torch.float32,
        attn_implementation='eager').eval()
    params = sum(x.numel() for x in model.parameters())
    if not 3_000_000_000 <= params <= 4_100_000_000:
        raise ValueError('not a full 3-4B checkpoint')
    checks, generated, logits_samples = [], [], []
    prefix = torch.tensor([ids], dtype=torch.long)
    start = time.monotonic()
    with torch.inference_mode():
        out = model(input_ids=prefix, use_cache=True, logits_to_keep=1)
        past = out.past_key_values
        for step in range(a.decode_steps):
            last_logits = out.logits[:, -1, :].float()
            if step in sorted(set([0, 1, a.decode_steps // 2, a.decode_steps - 1])):
                independent = model(input_ids=prefix, use_cache=False, logits_to_keep=1).logits[:, -1, :].float()
                delta = (independent - last_logits).abs()
                torch.testing.assert_close(last_logits, independent, atol=5e-4, rtol=5e-4)
                if not torch.equal(last_logits.argmax(-1), independent.argmax(-1)):
                    raise ValueError('cached/full-prefix argmax differs')
                checks.append({'step': step, 'prefix_tokens': int(prefix.shape[1]),
                               'maxabs': float(delta.max())})
                logits_samples.append(last_logits.numpy())
            token = last_logits.argmax(-1).view(1, 1)
            generated.append(int(token.item()))
            prefix = torch.cat((prefix, token), dim=1)
            # N generated tokens include one selected from prefill logits.
            # Execute N cached calls as well, yielding a separate steady-decode
            # oracle with explicit cache lengths P..P+N for performance models.
            out = model(input_ids=token, past_key_values=past, use_cache=True,
                        logits_to_keep=1)
            past = out.past_key_values
    elapsed = time.monotonic() - start
    np.savez(a.output / 'logits.npz', logits=np.concatenate(logits_samples, axis=0))
    files = sorted(a.checkpoint.glob('*.safetensors')) + [a.checkpoint / 'config.json']
    manifest = {f.name: file_sha(f) for f in files}
    ids_raw = json.dumps({'prompt': ids, 'generated': generated}, separators=(',', ':'))
    (a.output / 'tokens.json').write_text(ids_raw + '\n')
    receipt = {'scope': 'HF FP32 numerical oracle; not macro numeric/device timing/energy',
               'model': str(a.checkpoint), 'parameter_count': params,
               'checkpoint_files_sha256': manifest,
               'checkpoint_manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
               'tokens_sha256': file_sha(a.output / 'tokens.json'),
               'batch': 1, 'prompt_tokens': a.prompt_tokens, 'generated_tokens': len(generated),
               'cached_forward_calls': a.decode_steps, 'cached_prefix_lengths': [a.prompt_tokens, a.prompt_tokens + a.decode_steps],
               'cached_vs_full_checks': checks,
               'host_wall_seconds_including_validation': elapsed,
               'host_wall_is_device_timing': False, 'torch': torch.__version__}
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
