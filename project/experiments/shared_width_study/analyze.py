"""Read-only receipt verification and comparison; performs no simulation."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--receipts', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    root, out = args.receipts.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = json.loads((root / 'results/result.json').read_bytes())
    collection = json.loads((root / 'collection.json').read_bytes())
    assert collection['whole_run_passed'] is True and collection['terminal_state'] == 'COMPLETED'
    assert collection['exit_code'] == '0:0' and result['passed'] is True
    assert result['baseline_phase_passed'] is True and len(result['cases']) == 24
    assert str(collection['job']) == str(result['slurm']['job_id'])
    assert result['source_commit'] == collection['source_commit']
    selected = 0
    for name, digest in result['output_sha256'].items():
        path = root / 'results' / name
        if path.is_file():
            assert sha(path) == digest, 'returned output SHA differs: ' + name
            selected += 1
    all_hash = {}
    for line in (root / 'output-files.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        all_hash[name] = digest
    for path in (root / 'results').rglob('*'):
        if path.is_file():
            name = path.relative_to(root).as_posix()
            assert all_hash[name] == sha(path), 'collection SHA differs: ' + name
    main_cases = [c for c in result['cases'] if c['shared_pool_KiB'] == 32]
    controls = [c for c in result['cases'] if c['run30_control_required']]
    assert len(main_cases) == 20 and len(controls) == 8
    assert all(c['run30_complete_RESULT_exact'] for c in controls)

    def find(width, groups, mapping, dual):
        found = [c for c in main_cases if c['configuration'] == dict(width=width, groups=groups, mapping=mapping)
                 and c['dual_ports'] == dual]
        assert len(found) == 1
        return found[0]

    rows = []
    for config in result['configuration_plan']:
        for dual in (False, True):
            current = find(config['width'], config['groups'], config['mapping'], dual)
            base = find(32, 1, 'single', dual)
            narrow = find(16, 1, 'single', dual)
            rate = current['result']['tokens_per_second']
            meta = current['result']['shared_pool_study']
            rows.append(dict(**config, dual_ports=dual, tokens_per_second=rate,
                             gain_vs_single32=rate / base['result']['tokens_per_second'] - 1,
                             gain_vs_single16=rate / narrow['result']['tokens_per_second'] - 1,
                             passed_five=rate >= 5,
                             dot_ticks=current['result']['spans_ticks']['Dot'],
                             total_ticks=current['result']['ticks'],
                             shared_read_bytes=meta['read_bus_bytes'],
                             aggregate_port_wait=meta['port_wait_subcycles'],
                             workers=meta['P'],
                             group_service=meta.get('group_service_subcycles'),
                             group_read_beats=meta.get('group_read_beats')))
    output = dict(scope=result['scope'], source_commit=result['source_commit'],
                  result_sha256=sha(root / 'results/result.json'), collection=collection,
                  verified_returned_outputs=selected, exact_run30_controls=len(controls),
                  numeric_checks=result['numeric_checks'], cases=rows,
                  production_RTL_modified=False, native_full_model_tokens_per_second=None,
                  physical_clock_qualified=False,
                  pool_capacity_KiB=32, pool_4KiB_macros=8,
                  added_pool_SRAM_macros_for_two_groups=0,
                  new_control_datapath_area='not synthesized')
    (out / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf8')
    lines = ['# 共享32KiB继续扩宽：prefill具体评估', '',
             'Issue247 / PR243；负责人Melodydt。以下来自服务器实际执行的原条件SystemC评价体系，生产RTL未扩宽。', '',
             '固定prefill2/W8、300MHz、2P/1U、17.1GB/s、S32/K256/S96、原R1/R2/R4、每P四个64B FIFO槽和读延迟2拍。',
             '本地shared/idealdual是原模型两层，不能作为新原生RTL本地1R1W或整模型速度的资格。', '',
             '| 每P入口 B/拍 | 读取服务 | shared token/s | 相对原32B | idealdual token/s | 相对原32B |',
             '| ---: | --- | ---: | ---: | ---: | ---: |']
    for config in result['configuration_plan']:
        pair = [r for r in rows if all(r[k] == v for k, v in config.items())]
        assert len(pair) == 2 and pair[0]['dual_ports'] is False
        service = '全局64B' if config['groups'] == 1 else ('双64B组，' + ('连续16KiB分组' if config['mapping'] == 'contiguous' else '64B行交错'))
        lines.append('| {} | {} | {:.6f} | {:+.3%} | {:.6f} | {:+.3%} |'.format(config['width'], service,
            pair[0]['tokens_per_second'], pair[0]['gain_vs_single32'], pair[1]['tokens_per_second'], pair[1]['gain_vs_single32']))
    lines += ['', '## 验证与可追溯性', '',
              f"Slurm job{collection['job']} / {collection['node']} / {collection['elapsed']} / COMPLETED 0:0。",
              f"实际源码commit `{result['source_commit']}`；结果SHA-256 `{output['result_sha256']}`。",
              '24场景完成；8个16/32B控制的完整RESULT精确等run30。DDR传输、矩阵命令/工作量和向量工作均不变。',
              '逐配置数值与生命周期负例、独立地址/带宽/FIFO/组冲突审计见analysis.json；定向测试覆盖真实128B双行消费。', '',
              '## 面积与证据边界', '',
              '双组方案复用共享池8颗4KiB宏，容量仍32KiB，新增共享SRAM宏为0。双读仲裁、FIFO多项访问、M并行写入和互连增加逻辑，未综合，不能给出可信mm²增量或频率保证。',
              '共享A同址双P读取分别计费，不含广播。双组128B是无冲突峰值，单组冲突需要排队；每P128B不意味着两P合计256B持续供数。',
              '未完成原生S32拆分、K32实际命令、DMA桥/完整模型权重与token生成、STA/P&R或功耗；本结果不构成原生RTL实测token/s。', '']
    (out / 'report.md').write_text('\n'.join(lines), encoding='utf8')
    print(json.dumps(dict(passed=True, cases=len(rows), highest=max(r['tokens_per_second'] for r in rows),
                         analysis_sha256=sha(out / 'analysis.json'))))


if __name__ == '__main__':
    main()
