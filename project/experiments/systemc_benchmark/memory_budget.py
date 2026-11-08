"""Conditional dense B1 decode bandwidth floor, not SystemC/performance score.

All GEMV weights are streamed once, all granted on-chip capacity may retain
weights, and all attention/nonlinear/intermediate traffic is free. Hypothetical
packed formats do not establish quality, implemented packing or decompression.
"""
import argparse
import hashlib
import json
from pathlib import Path
from linear_capacity import model_work


def budget(config, *, granted_weight_cache_bytes=1 << 20, target_tps=(8.74, 10., 37.87, 92.7)):
    weights = sum(row['macs'] for row in model_work(config))
    rows = []
    for label, bits in (('old_scalar_128bit_records', 128), ('hypothetical_packed_S16', 16),
                        ('hypothetical_quality_preserving_S8', 8), ('hypothetical_quality_preserving_4bit', 4)):
        stored = (weights * bits + 7) // 8
        streamed = max(0, stored - granted_weight_cache_bytes)
        rows.append({'format': label, 'dense_linear_weight_storage_bytes': stored,
            'optimistic_weight_stream_bytes_per_token': streamed,
            'required_sustained_GBps': [{'target_tps': t, 'GBps': streamed * t / 1e9}
                                       for t in target_tps],
            'quality_or_implemented_packing_claimed': False})
    return {'dense_linear_parameters_including_tied_head': weights,
        'granted_permanent_weight_cache_bytes': granted_weight_cache_bytes,
        'rows': rows,
        'scope': 'conditional best-case weight-traffic floor, not SystemC decode or full-chip energy',
        'assumptions': ['dense direct GEMV, B1, no weight compression or recomputation',
                        'total reusable on-chip weight storage <= the stated granted cache (conditional, not inventoried here)',
                        'all granted cache may permanently hold weights',
                        'all other traffic and protocol inefficiency free'],
        'not_claimed': ['quality of lower precision', 'packing/decompression implemented',
                        'external bandwidth or memory hardware qualified'],
        'actual_tokens_per_second': None, 'actual_j_per_token': None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('config', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--granted-cache-bytes', type=int, default=1 << 20)
    a = p.parse_args()
    if a.granted_cache_bytes < 0:
        raise ValueError('nonnegative cache capacity required')
    result = budget(json.loads(a.config.read_text(encoding='utf-8')),
                    granted_weight_cache_bytes=a.granted_cache_bytes)
    result['files_sha256'] = {str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in (a.config, Path(__file__), Path(__file__).with_name('linear_capacity.py'))}
    a.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{'format': r['format'], 'ten_tps_GBps': r['required_sustained_GBps'][1]['GBps']}
                      for r in result['rows']]))


if __name__ == '__main__':
    main()
