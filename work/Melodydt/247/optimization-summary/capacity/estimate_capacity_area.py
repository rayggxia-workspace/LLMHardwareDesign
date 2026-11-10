"""Evaluate SRAM replication footprint and conditional tradeoffs from sealed evidence.

No EDA, remote execution, RTL edits or physical-qualification claims. The bank
area is extracted from the committed compact-S report, not from a local LEF.
"""
import argparse
import ast
import hashlib
import json
import platform
import re
from decimal import Decimal
from pathlib import Path

SOURCES = {
    'project/experiments/compact_local_s/README.md': 'ed28dd81a727c6b924196b735dbfddfd41789c74a472a26c77d09a38bda366cf',
    'project/experiments/compact_local_s/physical.py': 'c290ff088014c64260b8185a9a4b6533c0c347d9dfb13c968bd4ab1c26f6506c',
    'project/experiments/compact_local_s/occupancy.py': 'dbe627abdc3705c54a762c123ad37a796554894cfc5cb1ca429a6a8df00335b0',
    'project/rtl/s_sram/block_feed_s16k_sram.sv': 'a1ba89671305fd76f99e1b0c2a6fdadcbc73c783a0383c2b9640b496577317ef',
    'work/Melodydt/247/compare/policy/summary.json': '9548a9c862d32d81812ab5868d435cb8d65018da22cdea942816b44b64dae358',
    'docs/experiments/issue-247-u-fusion.md': '7a8501272ade2328affd47c023848e6d5dbe2f8c6e9f44e2e1ac82cb866c4b5e',
    'docs/experiments/issue-247-p-native-optimizations.md': '88ed0dd1c610a81734b666c614bf140c29635a0fa97fed7a16d75bfb8aeab2e6',
    'docs/experiments/issue-247-capacity-port-compare.md': 'fc5a617e4b46574eb2d49ebda3f2f53b78b961b583654bedda82189b35d39758',
}
LABELS = {('decode512', 'queued_pipe_w8'): 'W8 decode512',
          ('decode512', 'queued_pipe_w16'): 'W16 decode512',
          ('decode2048', 'queued_pipe_w8'): 'W8 decode2048',
          ('prefill2', 'queued_pipe_w8'): 'W8 prefill2'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    contents = {}
    for relative, expected in SOURCES.items():
        raw = (a.repo / relative).read_bytes()
        if digest(raw) != expected:
            raise ValueError('Source drift: ' + relative)
        contents[relative] = raw.decode('utf-8')
    report = contents['project/experiments/compact_local_s/README.md']
    total4 = Decimal(re.search(r'四个 bank 共占 ([\d,.]+) µm²', report).group(1).replace(',', ''))
    assert total4 == Decimal('369848.2001')
    bank_area = total4 / 4
    bank_hashes = None
    for node in ast.parse(contents['project/experiments/compact_local_s/physical.py']).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'BANK_HASHES' for t in node.targets):
            bank_hashes = ast.literal_eval(node.value)
    assert bank_hashes and bank_hashes['v'] == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    perf = json.loads(contents['work/Melodydt/247/compare/policy/summary.json'])
    assert perf['passed'] and perf['source_commit'] == '49b3938ce8b55734520c56a79a7d5d7933af9cdc'
    routes = []
    for route, cap, ctx in [('B16ctx8', 16, 8), ('A48', 48, 1), ('A64', 64, 1)]:
        banks_p = cap // 4
        active_banks = 2 * banks_p + 4
        total_kib = 2 * cap + 16
        routes.append(dict(route=route, P_count=2, U_count=1, P_KiB=cap, U_KiB=16,
            contexts=ctx, banks_per_P=banks_p, banks_U=4, active_banks=active_banks,
            active_S_KiB=total_kib, active_S_bits=total_kib * 1024 * 8,
            added_active_S_KiB_vs_B=total_kib - 48,
            added_banks_vs_B=active_banks - 12,
            active_bank_area_um2=float(bank_area * active_banks),
            active_bank_area_mm2=float(bank_area * active_banks / 1000000),
            bank_area_per_P_mm2=float(bank_area * banks_p / 1000000),
            added_bank_area_mm2_vs_B=float(bank_area * (active_banks - 12) / 1000000),
            bank_area_ratio_vs_B=active_banks / 12,
            bank_area_growth_pct_vs_B=(active_banks / 12 - 1) * 100,
            status='Conditional replication of existing 1RW hard-bank footprint only; not target 1R1W area'))
    measured_rows = []
    for (workload, profile), label in LABELS.items():
        selected = {}
        for route in ['B16ctx8', 'A48', 'A64']:
            matches = [c for c in perf['cases'] if c['workload'] == workload and c['profile'] == profile
                       and c['route'] == route and c['policy_KiB'] == 16 and c['P_port_quarters'] == 4]
            assert len(matches) == 1, (label, route, len(matches))
            selected[route] = matches[0]
        rate_b = selected['B16ctx8']['tokens_s']
        for route, ratio in [('A48', 28/12), ('A64', 36/12)]:
            rate = selected[route]['tokens_s']
            growth = rate / rate_b - 1
            measured_rows.append(dict(workload=label, route=route,
                B_token_s=rate_b, A_token_s=rate, speed_gain_pct=growth * 100,
                active_bank_area_ratio_vs_B=ratio,
                throughput_per_stored_bit_relative_to_B=(rate / rate_b) / ratio,
                f_critical_no_periphery=growth / (ratio - 1),
                interpretation='Sensitivity/proxy only; not measured system token/s/mm2'))
    sensitivity = [dict(baseline_bank_fraction_f=f,
        A48_total_area_ratio_ignoring_extra_periphery=1 + 4/3 * f,
        A64_total_area_ratio_ignoring_extra_periphery=1 + 2 * f)
        for f in [0.10, 0.25, 0.50]]
    marginal = []
    for (workload, profile), label in LABELS.items():
        rows = {r['route']: r for r in measured_rows if r['workload'] == label}
        marginal.append(dict(workload=label,
            A64_over_A48_speed_gain_pct=(rows['A64']['A_token_s'] / rows['A48']['A_token_s'] - 1) * 100,
            added_active_S_KiB=32, added_banks=8,
            added_same_1RW_bank_area_mm2=float(8 * bank_area / 1000000),
            active_bank_area_growth_pct=(36/28 - 1) * 100))
    output = dict(schema_version=1,
        scope='Conditional area budget for large-capacity SRAM direction; no new RTL, EDA or remote jobs',
        source_snapshot_commit='9925300dc32c18b786bff7a3fe14a2c07ce5746f',
        sources=[dict(path=p, sha256=h) for p, h in SOURCES.items()],
        bank_reference=dict(name='s_sram_256x128_freepdk45', bits=256*128, KiB=4,
            port_type='1RW', four_bank_report_area_um2=float(total4),
            per_bank_derived_area_um2=float(bank_area), per_bank_derived_area_mm2=float(bank_area/1000000),
            provenance='Committed Issue200 report says sum of final ODB bank instance rectangles; original ODB and LEF not locally read in this evaluation',
            expected_view_sha256=bank_hashes,
            physical_dimensions_um=None,
            physical_dimensions_status='not present in locally read bank view; no LEF width/height invented',
            bitcell_only_area_um2=None, bitcell_status='unknown; hard-bank footprint includes bank-local periphery'),
        historical_16KiB_wrapper_reference=dict(
            S_P_die_um=[900,540], S_P_die_area_mm2=0.486,
            S_base_die_um=[880,520], S_base_die_area_mm2=0.4576,
            S_P_functional_stdcell_area_um2=29210.258, S_base_functional_stdcell_area_um2=7441.616,
            warning='Historical wrapper rectangles only, not complete P/U or new R4; do not multiply whole wrapper area by 3 or 4'),
        capacity_replication=routes,
        performance_source=dict(path='work/Melodydt/247/compare/policy/summary.json',
            source_commit=perf['source_commit'], result_sha256='4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777',
            clock_hz=300000000, DDR_B_s=17100000000,
            policy_KiB=16, P_port_quarters=4,
            warning='Speed uses ideal 1R1W SystemC while footprint is existing 1RW replication, so no physical area-efficiency qualification'),
        conditional_resource_proxies=measured_rows,
        marginal_64_over_48=marginal,
        total_area_sensitivity=dict(
            definition_f='Baseline three active S bank hard-macro footprint divided by complete baseline area',
            formula_A48='A_A48/A_B = 1 + (4/3)*f + Delta_other/A_B',
            formula_A64='A_A64/A_B = 1 + 2*f + Delta_other/A_B',
            ignored_in_example='Delta_other=0; address decode, crossbar, routing/halo, timing repair, true1R1W premium and context-register differences excluded',
            f_is_measured=False, examples=sensitivity),
        true_1R1W_area=dict(premium_q=None,
            q_definition='area of an equivalent 4KiB 1R1W bank divided by known 4KiB 1RW bank area; no measured q',
            bank_area_B='(8*q + 4) * a', bank_area_A48='(24*q + 4) * a',
            bank_area_A64='(32*q + 4) * a',
            warning='a is same 1RW bank footprint; q is unknown, organization may not be simple replication'),
        extra_storage_budgets=[
            dict(item='Old conditional B16ctx8 extra S96 psums', per_P_bytes=672, two_P_bytes=1344,
                 formula='2 * (8-1) * 8 * 96 / 8', control_area='unknown'),
            dict(item='Production S64 context implementation', new_metadata_bits_per_P=325,
                 two_P_new_metadata_bits=650, existing_result_bits_per_P=4096,
                 new_psum_data_bits=0, warning='Reuses existing result slots; not same arithmetic or budget as S96 model'),
            dict(item='E-to-E forwarding only', data_bytes=256, metadata_bytes=32, total_known_bytes=288,
                 RTL_area_mm2=None, implementation='SystemC candidate, not production'),
            dict(item='D2 full-trace overlap candidate including forwarding',
                 data_bytes=2304, forwarding_metadata_bytes=32, total_known_bytes=2336,
                 data_formula='2*(768 input + 256 output) + 256 forwarding',
                 warning='2304 already includes 256 forwarding; do not add 288 again; extra FIFO/descriptors/control unknown'),
            dict(item='Native S16 isolated overlap FIFO D2', data_tag_bits=272,
                 data_tag_bytes=34, warning='Different RTL-local experiment, not the 2304B full-trace model buffer')],
        unmeasured=['New 48/64KiB wrapper floorplan', 'True1R1W macro area/power',
            'System die area', 'Added address/selection/controller/ports area',
            'Post-route frequency and timing fixes', 'New whole-model physical token/s/mm2'],
        local_calculation=dict(python=platform.python_version(), script_sha256=digest(Path(__file__).read_bytes()),
            new_EDA_runs=0, remote_access=False))
    a.output.mkdir(parents=True, exist_ok=True)
    target = a.output / 'area-summary.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 大容量 SRAM 面积预算与证据边界', '',
        '本次仅读取已有报告与模型结果计算，没有新RTL、EDA或服务器作业。', '',
        '## 现有1RW bank外框复制条件估算', '',
        'Issue200紧凑S报告给出四bank最终ODB实例矩形总面积369848.2001µm²。每个4KiB bank派生为92462.050025µm²。未在本次读取原LEF/ODB，不编造bank宽高。', '',
        '| 配置 | 每P KiB | P bank数/颗 | 2P+U bank总数 | 活跃S KiB | bank面积和mm² | 对B增量mm² | 对B比例 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in routes:
        lines.append(f"| {r['route']} | {r['P_KiB']} | {r['banks_per_P']} | {r['active_banks']} | {r['active_S_KiB']} | {r['active_bank_area_mm2']:.6f} | {r['added_bank_area_mm2_vs_B']:.6f} | {r['bank_area_ratio_vs_B']:.4f}x |")
    lines += ['', '**上述是同已表征1RW宏的纯容量复制估算，不是bitcell面积、真实1R1W、新布局或系统面积。** 不含新译码、MUX、响应队列、留白、走廊、时序修复、1R1W面积溢价。模型需要的独立64B读+64B写能力不会由复制自动获得。', '',
        '历史16KiB S_P外框900×540µm=0.486mm²，S_base外框880×520µm=0.4576mm²，仅作旧wrapper背景；不能将整体wrapper按3/4倍放大，也不是完整P/U面积。', '',
        '## 系统面积条件敏感性', '',
        '设f为基线三颗活跃S的bank面积占完整基线面积比例，保持其他面积不变时，A48/B=1+4f/3，A64/B=1+2f。f尚未测得；新外围及context寄存器差异另计。', '',
        '| 假设f | A48总面积/B | A64总面积/B |', '|---|---:|---:|']
    for r in sensitivity:
        lines.append(f"| {r['baseline_bank_fraction_f']:.0%} | {r['A48_total_area_ratio_ignoring_extra_periphery']:.4f} | {r['A64_total_area_ratio_ignoring_extra_periphery']:.4f} |")
    lines += ['', '若目标P的1R1W每4KiB面积为现有1RW的q倍，则三路线bank面积分别为(8q+4)a、(24q+4)a、(32q+4)a；U仍原1RW。q未知，不用q=1冒充目标宏实际面积。', '',
        '## 速度与资源预算的条件对照', '',
        '| 原模型场景 | 路线 | 对B吞吐增幅 | 每存储bit吞吐/B | 面积效率持平f条件 |', '|---|---|---:|---:|---:|']
    for r in measured_rows:
        lines.append(f"| {r['workload']} | {r['route']} | {r['speed_gain_pct']:+.4f}% | {r['throughput_per_stored_bit_relative_to_B']:.4f} | f={r['f_critical_no_periphery']:.4%} |")
    lines += ['', '每bit吞吐及f临界值只是预算敏感性，不是芯片实测token/s/mm²。f临界值还假设新增外围为0；真实1R1W、控制和寄存器差异会改变结论。', '',
        'A64相对A48增加32KiB总S、8颗bank，复制面积多0.739696mm²（活跃bank面积+28.5714%）。各原场景吞吐增幅：']
    for r in marginal:
        lines.append(f"- {r['workload']}: {r['A64_over_A48_speed_gain_pct']:+.5f}%")
    lines += ['', '## 额外寄存器预算', '',
        '- B路线旧S96条件模型额外部分和为672B/P、两P共1344B，控制另计。',
        '- 当前生产S64实现复用原4096bit/P结果槽，新增约325bit/P控制，两个P为650bit。不能把两种数值合同的资源相抵。',
        '- E→E转发独立为256B数据+32B元数据=288B；没有生产RTL面积。',
        '- D2整图流水模型为2×(768B输入+256B输出)+256B转发=2304B数据，再加32B转发元数据=2336B，其他FIFO/描述符/控制未定量。不能再重复加256B转发。',
        '- 原生S16局部FIFO D2为136bit×2=272bit=34B，与上述整图模型2304B不是同一实例。', '',
        '来源、源码SHA、宏视图预期SHA、精确数值及计算公式见area-summary.json。']
    (a.output/'area-notes.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(area_json_sha256=digest(target.read_bytes()), routes=routes,
                          new_EDA_runs=0),ensure_ascii=False))


if __name__ == '__main__':
    main()
