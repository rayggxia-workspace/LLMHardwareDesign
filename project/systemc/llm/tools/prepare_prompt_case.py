"""Add an independent short prompt case, preserving the existing weight export."""
import argparse
import json
from pathlib import Path
import os
import time
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from model_support import load_reference
from export_checkpoint import sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkpoint', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--prompt', required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    report = json.loads((a.checkpoint/'export_receipt.json').read_text())
    tokenizer = AutoTokenizer.from_pretrained(report['model_path'], local_files_only=True)
    prompt = tokenizer.encode(a.prompt, add_special_tokens=False)
    if len(prompt) != 1:
        raise ValueError('this bounded case requires one token to reuse three-position RoPE tables')
    a.output.mkdir(exist_ok=False)
    for name in ('metadata.txt', 'weights.bin', 'weights.index'):
        (a.output/name).symlink_to((a.checkpoint/name).resolve())
    if (a.checkpoint/'weights.scales').exists():
        (a.output/'weights.scales').symlink_to((a.checkpoint/'weights.scales').resolve())
    (a.output/'prompt.txt').write_text(str(prompt[0])+'\n')
    if report['config']['model_type'] == 'granitemoe':
        # The installed official loader converts the legacy packed expert names
        # to its current expert modules; the strict new-family loader does not.
        model = AutoModelForCausalLM.from_pretrained(report['model_path'], local_files_only=True,
                                                    dtype=torch.float32, attn_implementation='eager').eval()
    else:
        model = load_reference(report['model_path'])
    started=time.perf_counter()
    cache = None
    inputs, generated = [], []
    with torch.inference_mode(), (a.output/'reference_hidden.bin').open('xb') as hf, (a.output/'reference_logits.bin').open('xb') as lf:
        for step in range(3):
            token = prompt[0] if not step else generated[-1]
            inputs.append(token)
            y = model(input_ids=torch.tensor([[token]]), past_key_values=cache, use_cache=True, output_hidden_states=True)
            cache = y.past_key_values
            pred = int(y.logits[0, -1].argmax())
            generated.append(pred)
            lf.write(y.logits[0, -1].float().numpy().astype('<f4').tobytes())
            for hidden in y.hidden_states:
                hf.write(hidden[0, -1].float().numpy().astype('<f4').tobytes())
    report.pop('reference_reused_from',None)
    report.update(reference_seconds=time.perf_counter()-started,prompt=a.prompt, prompt_ids=prompt, reference_inputs=inputs,
                  reference_next_ids=generated, reference_generated=generated,
                  reference_text=tokenizer.decode(generated),
                  prompt_case_previous_export=str(a.checkpoint.resolve()),
                  prompt_case_previous_receipt_sha256=sha(a.checkpoint/'export_receipt.json'),
                  prompt_case_tool_sha256=sha(Path(__file__)))
    (a.output/'export_receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print('INDEPENDENT_PROMPT', prompt, generated, report['reference_text'])


if __name__ == '__main__':
    main()
