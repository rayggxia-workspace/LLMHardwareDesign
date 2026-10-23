"""Independent saved-summary/manifest checks; does not rerun model inference."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


def main():
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    p.add_argument('--run', default='run01', choices=['run01', 'run02'])
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refusing existing audit')
    run = a.root / a.run
    c = json.loads((run / 'source/experiment.json').read_text())
    b = json.loads((run / 'binding.json').read_text())
    for name, expected in b['source_files'].items():
        assert hashlib.sha256((run / 'source' / name).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((run / 'inputs.json').read_bytes()).hexdigest() == b['input_sha256']
    rows = []
    for dtype in c['dtypes']:
        for threads in c['threads']:
            folder = run / f'{dtype}-{threads}'
            r = json.loads((folder / 'result.json').read_text())
            correctness = json.loads((folder / 'correctness.json').read_text())
            assert all(r[k] == v for k, v in correctness.items())
            assert r['source'] == b and r['dtype'] == dtype and r['threads'] == threads
            assert threads <= len(set(r['affinity'])) and r['packages']['torch'] == c['torch']
            assert r['packages']['transformers'] == c['transformers']
            metrics = [r['cached_logits'], r['chunk_logits']]
            assert len(r['cache_layers']) == 28
            assert r['cached_logits']['elements'] == 8*151936
            assert r['chunk_logits']['elements'] == 136*151936
            for i, layer in enumerate(r['cache_layers']):
                assert layer['layer'] == i and layer['shape'] == [1, 8, 136, 128]
                metrics += [layer[k] for k in ('cached_k', 'cached_v', 'chunk_k', 'chunk_v')]
            for m in metrics:
                assert m['elements'] > 0 and math.isfinite(m['max_abs']) and math.isfinite(m['relative_rmse'])
                assert m['max_abs'] >= 0 and m['relative_rmse'] >= 0 and 0 <= m['argmax_agreement'] <= 1
                expected_gate = m['finite'] and (m['fp32_close'] if dtype == 'float32' else
                                                m['relative_rmse'] <= c['bf16_split_relative_rmse_budget'])
                assert m['pilot_gate'] == expected_gate
            assert r['all_semantic_gates'] == all(m['pilot_gate'] for m in metrics)
            assert len(r['timings']) == 6
            for length in c['prefill_tokens']:
                ts = [t for t in r['timings'] if t['prefix_tokens'] == length]
                assert sorted(t['repeat'] for t in ts) == [0, 1, 2]
                for t in ts:
                    assert t['prefill_seconds'] > 0 and len(t['decode_token_seconds']) == 16
                    assert all(math.isfinite(v) and v > 0 for v in t['decode_token_seconds'])
                    assert math.isclose(t['prefill_tokens_per_second'], length/t['prefill_seconds'], rel_tol=1e-12)
                    assert math.isclose(t['decode_tokens_per_second'], 16/sum(t['decode_token_seconds']), rel_tol=1e-12)
                for k in ('prefill_seconds', 'prefill_tokens_per_second', 'decode_tokens_per_second'):
                    assert r['timing_summary'][str(length)][k] == statistics.median(t[k] for t in ts)
            assert r['peak_rss_kib_process_lifetime'] > 0
            rows.append({'dtype': dtype, 'threads': threads, 'all_semantic_gates': r['all_semantic_gates'],
                'strict_fp32_metric_failures': sum(not m['fp32_close'] for m in metrics),
                'max_relative_rmse': max(m['relative_rmse'] for m in metrics),
                'cached_logits': r['cached_logits'], 'chunk_logits': r['chunk_logits'],
                'peak_rss_kib': r['peak_rss_kib_process_lifetime'], 'timing_summary': r['timing_summary']})
    result = {'status': 'PASS', 'source_commit': b['source_commit'], 'conditions': rows,
              'scope': 'saved scalar metrics/shape/source/timing recomputation only; raw logits not archived, no independent framework kernel'}
    a.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
