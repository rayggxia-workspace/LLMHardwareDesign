"""Derive matched-prefix tensor comparisons from the preserved run directory."""
import argparse
import gzip
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('run', type=Path)
p.add_argument('out', type=Path)
args = p.parse_args()
events = [json.loads(line) for line in gzip.decompress(
    (args.run / 'primary-events.jsonl.gz').read_bytes()).splitlines()]
comparisons = []
for stage in ('attention.probabilities', 'swiglu_product_before_down_proj', 'q_projection_pre_norm_rope'):
    row = {'stage': stage}
    for schedule in ('single_prefill', 'chunked_prefill'):
        selected = [e for e in events if e['layer'] == 0 and e['stage'] == stage
                    and e['schedule'] == schedule and e['end'] <= 32]
        row[schedule] = {'calls': len(selected),
                         'max_single_tensor_bytes': max(e['logical_bytes'] for e in selected),
                         'cumulative_tensor_bytes': sum(e['logical_bytes'] for e in selected)}
    comparisons.append(row)
numeric = [json.loads((args.run / name).read_text()) for name in
           ('primary-numeric.json', 'length_confirmation-numeric.json')]
positive = [r for n in numeric for rows in n['positive_paths'].values() for r in rows]
trace = json.loads((args.run / 'primary-trace.json').read_text())
manifest = json.loads((args.run / 'manifest.json').read_text())
output = {
    'source_commit': manifest['source_commit'], 'positive_calls': len(positive),
    'negative_controls': [{k: control[k] for k in ('name', 'passed', 'detected')}
                          for n in numeric for control in n['negative_controls']],
    'top1_agree': sum(r['comparison']['logits']['top1_agrees'] for r in positive),
    'max_logit_abs': max(r['comparison']['logits']['max_abs'] for r in positive),
    'max_logit_relative_l2': max(r['comparison']['logits']['relative_l2'] for r in positive),
    'max_kv_abs': max(f['max_abs'] for r in positive for f in r['comparison']['cache']['fields']),
    'trace_calls': len(trace['calls']), 'trace_events': len(events),
    'selected_boundary_comparisons': sum(len(c['boundary_comparisons']) for c in trace['calls']),
    'comparisons': comparisons,
    'scope': 'Observed tensor logical bytes for matched 32-token prefix, layer0 representative; '
             'not total live peak or physical traffic.'}
args.out.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'positive_calls': len(positive), 'trace_events': len(events)}))
