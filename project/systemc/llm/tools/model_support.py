"""Text-only checkpoint loading and explicit name mapping; no remote code execution."""
import os
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
from pathlib import Path
import torch
from safetensors import safe_open
from transformers import AutoConfig, AutoModelForCausalLM

def config_for(path):
    cfg = AutoConfig.from_pretrained(path, local_files_only=True)
    return getattr(cfg, 'text_config', cfg)

def canonical(name, family):
    if family == 'gemma3_text':
        return name[len('language_model.'):] if name.startswith('language_model.') else None
    if family == 'qwen3_5_text':
        if name.startswith('model.language_model.'):
            return 'model.' + name[len('model.language_model.'):]
        return name if name == 'lm_head.weight' else None
    return name

def source_tensors(path, family):
    for p in sorted(Path(path).glob('*.safetensors')):
        with safe_open(str(p), framework='pt', device='cpu') as f:
            for name in f.keys():
                mapped = canonical(name, family)
                if mapped is not None:
                    yield name, mapped, f.get_tensor(name).float()

def load_reference(path):
    # On this Lustre installation, mmap page faults took tens of minutes while
    # a sequential read of all four checkpoint sets took13s. Warm the page cache
    # on the actual execution node, with a bounded16MiB buffer and read-only IO.
    for p in sorted(Path(path).glob('*.safetensors')):
        with p.open('rb') as f:
            while f.read(16*1024*1024):
                pass
    c = config_for(path)
    c._attn_implementation = 'eager'
    model = AutoModelForCausalLM.from_config(c).float().eval()
    targets = model.state_dict()
    seen = set()
    with torch.no_grad():
        for original, name, value in source_tensors(path, c.model_type):
            if name not in targets:
                raise ValueError('unmapped text weight: ' + original + ' -> ' + name)
            if targets[name].shape != value.shape:
                raise ValueError('shape mismatch: ' + name)
            targets[name].copy_(value)
            seen.add(name)
    missing = set(targets) - seen
    if c.tie_word_embeddings and 'model.embed_tokens.weight' in seen:
        missing.discard('lm_head.weight')
    if missing:
        raise ValueError('missing true checkpoint weights: ' + str(sorted(missing)))
    model.tie_weights()
    return model
