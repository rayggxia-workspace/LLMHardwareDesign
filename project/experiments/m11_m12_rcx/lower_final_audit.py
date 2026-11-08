"""Retain all-row point estimates and the largest unresolved cases explicitly."""
import argparse
import csv
import gzip
import hashlib
import heapq
import json
import os
from pathlib import Path
import statistics


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def stats(values):
    if not values:
        return None
    v = sorted(values)
    def q(f):
        x = f * (len(v) - 1)
        i = int(x)
        return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (x - i)
    return dict(count=len(v), minimum=v[0], median=statistics.median(v), p95=q(.95), maximum=v[-1])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--delivery', type=Path, required=True)
    p.add_argument('--native', type=Path, required=True)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    delivery = json.loads((a.delivery / 'delivery.json').read_text())
    summary = json.loads((a.native / 'summary.json').read_text())
    assert delivery['native_parameter_comparison_completed'] and summary['complete_requested_coverage']
    path = a.native / 'comparison.tsv.gz'
    assert sha(path) == summary['comparison_sha256'] == delivery['native_comparison_sha256']
    values, unresolved, top, bins = [], [], [], [0, 0, 0]
    with gzip.open(path, 'rt', newline='') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            x = float(row['field_delta_percent'])
            values.append(x)
            bins[0 if abs(x) <= 1 else 1 if abs(x) <= 5 else 2] += 1
            if row['precision_passed'] not in ['True', 'true', '1']:
                unresolved.append(x)
                heapq.heappush(top, (x, int(row['master']), row))
                if len(top) > 100:
                    heapq.heappop(top)
    assert len(values) == summary['completed_rows'] == 2252983
    assert len(unresolved) == summary['unqualified_rows']
    result = dict(completed_native_electrodes=len(values), precision_passed=summary['precision_passed_rows'],
                  precision_unresolved=len(unresolved), all_population_point_estimates_percent=stats(values),
                  unresolved_point_estimates_percent=stats(unresolved),
                  absolute_point_estimate_bins=dict(up_to_one_percent=bins[0],one_to_five_percent=bins[1],above_five_percent=bins[2]),
                  zero_point_estimate_is_not_proof_of_zero_effect=True,
                  macro_acceptance_threshold=None, direct_macro_reuse_qualified=False,
                  original_delivery=str(a.delivery), original_delivery_sha256=sha(a.delivery / 'delivery.json'),
                  native_summary_sha256=sha(a.native / 'summary.json'),
                  native_comparison_path=str(path), native_comparison_sha256=sha(path),
                  scope='All-row point statistics are descriptive, including unresolved rows. They do not replace individual intervals or qualify macro delay. Qualified-only statistics remain separately labeled in original summary.')
    (out / 'final-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'largest-unresolved-increases.json').write_text(json.dumps([r[2] for r in sorted(top, reverse=True)], indent=2) + '\n')
    text = (
        '# 下层参数对照：完整统计与未解决项\n\n'
        f'原版Qwen3.5共有{len(values):,}条非边界线路完成前后比较；'
        f'{result["precision_passed"]:,}条达到本轮计算精度，{len(unresolved):,}条仍须结合误差范围判断。\n\n'
        '全体线路的点估计统计和精度足够条目的统计分别保存。点估计为零，不表示已经证明影响严格为零。'
        '精度未过但变化较大的线路另列在largest-unresolved-increases.json，未从报告中隐藏。\n\n'
        f'中文报告和上下连接线对照：{a.delivery / "README.md"}\n\n'
        f'完整逐网对照：{path}\n\n'
        '电容变化、宏的速度变化是两回事；这张参数表没有自动授予旧宏模型直接复用资格。\n'
    )
    (out / 'README.md').write_text(text)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
