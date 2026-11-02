"""Correct a known old Falcon export in a new directory; never mutate its inputs."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkpoint', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    report = json.loads((a.checkpoint/'export_receipt.json').read_text())
    if report['config']['model_type'] != 'falcon_h1':
        raise ValueError('not Falcon-H1')
    md = dict(line.split() for line in (a.checkpoint/'metadata.txt').read_text().splitlines())
    expected = 1/math.sqrt(int(md['head_dim']))
    if float(md['attention_multiplier']) != 1:
        raise ValueError('not the identified old Falcon metadata')
    a.output.mkdir(exist_ok=False)
    md['attention_multiplier'] = repr(expected)
    (a.output/'metadata.txt').write_text('\n'.join(k+' '+v for k, v in md.items())+'\n')
    for name in ('weights.bin', 'weights.index', 'prompt.txt', 'reference_hidden.bin', 'reference_logits.bin'):
        (a.output/name).symlink_to((a.checkpoint/name).resolve())
    report['metadata_repair'] = {'previous_export': str(a.checkpoint.resolve()),
                                 'previous_receipt_sha256': sha(a.checkpoint/'export_receipt.json'),
                                 'old_attention_multiplier': 1, 'attention_multiplier': expected,
                                 'key_multiplier': report['config']['key_multiplier'],
                                 'reason': 'official FalconH1Attention applies key multiplier AND head_dim**-0.5',
                                 'repair_tool_sha256': sha(Path(__file__))}
    (a.output/'export_receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(report['metadata_repair'], indent=2))


if __name__ == '__main__':
    main()
