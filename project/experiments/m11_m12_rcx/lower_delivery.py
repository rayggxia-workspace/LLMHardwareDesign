"""Assemble the completed lower-C comparison and a plain Chinese report."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil

BASE = Path('/public/home/yuzelu/PingyangHuang')
OLD_MATRIX = BASE / 'issue-222-validated-mPI4CdbA/job-100247/result'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--interfaces', type=Path, required=True)
    p.add_argument('--surface', type=Path, required=True)
    p.add_argument('--controls', type=Path, required=True)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    sources = {}
    def read(path):
        sources[str(path)] = dict(bytes=path.stat().st_size, sha256=sha(path))
        return json.loads(path.read_text())
    native = read(a.native / 'summary.json')
    interfaces = read(a.interfaces / 'summary.json')
    surface = read(a.surface / 'summary.json')
    control = read(a.controls / 'comparison.json')
    assert native['complete_requested_coverage'] and native['completed_rows'] == 2252983
    assert interfaces['complete_interface_coverage'] and interfaces['completed_interfaces'] == 2491
    assert interfaces['source_restricted_origin'] and surface['source_net_restricted_origin']
    assert control['all_twelve_controls_passed']
    assert sha(a.native / 'comparison.tsv.gz') == native['comparison_sha256']
    assert sha(a.interfaces / 'interface-comparison.tsv') == interfaces['comparison_sha256']
    checks = read(a.surface / 'checks.json')
    assert sha(a.surface / 'checks.json') == surface['checks_sha256']
    wanted = {r['master'] for r in checks}
    old_meta = read(OLD_MATRIX / 'solve.json')
    assert sha(OLD_MATRIX / 'rows.jsonl') == old_meta['rows_sha256']
    reference = {}
    with (OLD_MATRIX / 'rows.jsonl').open('rb') as f:
        for raw in f:
            i = int(raw.split(b',', 1)[0].split(b':')[-1])
            if i in wanted:
                r = json.loads(raw)
                reference[i] = r['total_ff'], r['sigma_ff']
    assert set(reference) == wanted
    # The fine reports retain whole-field sigma in their raw rows.
    fine_sigmas = {}
    for receipt in surface['source_receipts']:
        folder = Path(receipt).parent
        meta = json.loads(Path(receipt).read_text())
        path = folder / 'rows.jsonl'
        assert sha(path) == meta['rows_sha256']
        for line in path.open():
            row = json.loads(line)
            fine_sigmas[(row['master'], meta['offset'])] = row['sigma_ff']
    resolved_whole = []
    for check in checks:
        sigma = fine_sigmas[(check['master'], check['offset'])] + reference[check['master']][1]
        if abs(check['whole_total_minus_main_ff']) > 5 * sigma:
            resolved_whole.append(dict(master=check['master'], offset=check['offset'],
                                       difference_ff=check['whole_total_minus_main_ff'], five_se_ff=5 * sigma))
    example = next(r for r in control['samples'] if r['alias'] == 'done_data[86]')
    qualified = native['precision_passed_rows']
    uncertain = native['unqualified_rows']
    metrics = native['qualified_delta_percent']
    text = (
        '# 原 Qwen3.5：加入上层后，下层参数变化\n\n'
        '沿用已连好的 #206 版图，没有重新布线。原软件结果、原金属几何和有效的旧计算保留；只补缺项及精度不足项。\n\n'
        f'宏里其他线路共 {native["completed_rows"]:,} 条，已完成前后比较。其中 {qualified:,} 条达到本轮计算精度，'
        f'{uncertain:,} 条仍须结合给出的误差范围判断。另有 2,491 条上下连接线，已补齐下层贡献并修正上下层分摊。\n\n'
        f'在精度足够的 {qualified:,} 条中，电容变化中位数为 {metrics["median"]:.6g}%，'
        f'95 分位为 {metrics["p95"]:.6g}%，最大为 {metrics["maximum"]:.6g}%。'
        '这是逐条线路的电容变化，不能当作整个宏的速度误差。\n\n'
        f'一个已经独立核验的例子是 F0 的 done_data[86]：电容从 {example["global_before_ff"]:.6g} '
        f'变成 {example["global_after_ff"]:.6g} fF，约增加 {example["global_delta_percent"]:.3f}%。'
        f'另一种计算范围得到约 {example["local_delta_percent"]:.3f}%，两者一致。\n\n'
        '本轮 1% 指计算精度目标，并不是用户选定的“宏模型允许误差”。'
        '旧电阻段保持原值。原软件参数另外列出，前后变化采用相同电场设置计算，避免把算法不同造成的差别算作上层影响。\n\n'
        '结果表给出原参考、加入上层前后电容、变化量、数值不确定范围和原线路名称。'
        '这次交付是逐网金属参数比较；没有把它说成新的分布式寄生文件或已经通过速度检查的新宏模型。\n\n'
        '此前报告的上/下层来源百分比已撤回，原因是来源标签有误；旧完整总矩阵仍有效。'
        '本轮已修正来源识别，并保留完整复现、控制、逐行总矩阵一致和选定线路精度检查。\n\n'
        f'选定线路中，来源投影对计算面位置仍有 {surface["resolved_native_projection_sensitivity_cases"]} '
        f'处超过五倍标准误差的变化；整网总量相应检查有 {len(resolved_whole)} 处。'
        '这些敏感性和仍不够准的条目均保留在报告中，原宏模型不因此获得直接复用资格。\n\n'
        f'完整逐网表：{a.native / "comparison.tsv.gz"}\n\n'
        f'上下连接线对照：{a.interfaces / "interface-comparison.tsv"}\n\n'
        '固定版本：#206 179ca76ff35673dcb47986e3d873fc2a87dbabbb；'
        '#216 5f055f6cd1349174ecb71ea55bc48e9acd6a618d。'
        '仅沿用原数据/握手连线范围；没有补父层时钟、复位或控制路由。\n'
    )
    (out / 'README.md').write_text(text)
    for name, source in [('native-summary.json', a.native / 'summary.json'),
                         ('interface-summary.json', a.interfaces / 'summary.json'),
                         ('surface-summary.json', a.surface / 'summary.json'),
                         ('largest-increases.json', a.native / 'largest-increases.json'),
                         ('interface-comparison.tsv', a.interfaces / 'interface-comparison.tsv'),
                         ('surface-checks.json', a.surface / 'checks.json')]:
        shutil.copyfile(source, out / name)
    report = dict(frozen_route_commit='179ca76ff35673dcb47986e3d873fc2a87dbabbb',
                  frozen_baseline_commit='5f055f6cd1349174ecb71ea55bc48e9acd6a618d',
                  completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  native_electrodes=native['completed_rows'], native_precision_passed=qualified,
                  native_precision_unresolved=uncertain, interfaces=2491,
                  native_parameter_comparison_completed=True, direct_macro_reuse_qualified=False,
                  new_distributed_spef_assembled=False, new_macro_timing_model_characterized=False,
                  whole_matrix_surface_sensitivity=resolved_whole,
                  source_projection_surface_sensitivity_cases=surface['resolved_native_projection_sensitivity_cases'],
                  old_source_component_percentages_withdrawn=True, original_geometry_and_dc_r_reused=True,
                  native_comparison_path=str(a.native / 'comparison.tsv.gz'),
                  native_comparison_sha256=native['comparison_sha256'],
                  input_receipts=sources,
                  output_files={p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in out.iterdir()},
                  scope='Uniform-eps quiet-signal metal-only research comparison. Numerical intervals do not include manufacturing/model calibration, device timing, general switching or all-node RC distribution.')
    (out / 'delivery.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['input_receipts', 'output_files']}), flush=True)


if __name__ == '__main__':
    main()
