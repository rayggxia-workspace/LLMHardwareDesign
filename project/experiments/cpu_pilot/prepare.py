"""Make fixed teacher-forced inputs from the existing verified local tokenizer."""
import argparse
import json
from pathlib import Path
from pilot import sha, save

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refusing existing output')
    original = json.loads((ROOT / 'project/experiments/qwen3_trace/experiment.json').read_text(encoding='utf-8'))
    for name, expected in original['model_files'].items():
        f = a.model_dir / name
        assert f.stat().st_size == expected['bytes'] and sha(f) == expected['sha256'], name
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(a.model_dir, local_files_only=True, trust_remote_code=False)
    ids = tokenizer(original['input_text'] * 6, add_special_tokens=False)['input_ids'][:528]
    assert len(ids) == 528
    a.out.mkdir(parents=True)
    save(a.out / 'inputs.json', {'model_revision': original['revision'], 'input_ids': ids,
                                'source_text': original['input_text'], 'repetitions': 6,
                                'scope': 'systems passage repeated, not a language-quality benchmark'})
    print(sha(a.out / 'inputs.json'))


if __name__ == '__main__':
    main()
