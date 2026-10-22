"""Create the Chinese research report from qualified, frozen observations only."""
import hashlib
from html import escape
import json
from pathlib import Path
import subprocess

from quality import evaluate, require_toolchain

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RESULTS = HERE / 'results'
OUT = REPO / 'docs/experiments/issue-15-opentpu-results.html'


def table(headers, rows):
    head = ''.join('<th>' + escape(str(x)) + '</th>' for x in headers)
    body = ''.join('<tr>' + ''.join('<td>' + escape(str(x)) + '</td>' for x in row) + '</tr>' for row in rows)
    return '<div class="scroll"><table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table></div>'


def main():
    data = json.loads((RESULTS / 'comparison.json').read_text())
    frozen = (RESULTS / 'comparison-inputs.json').read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == data['input_snapshot_sha256']
    snapshot = json.loads(frozen)
    records = snapshot['attempts']
    selection = data['selection']
    for name in selection.values():
        assert evaluate(records[name])['passed'], 'Report requires qualified source: ' + name
        require_toolchain(records[name])
    images = ['issue-15-ppa', 'issue-15-floorplans', 'issue-15-routing-layers']
    for name in images:
        assert (OUT.parent / 'assets' / (name + '.png')).is_file(), 'Run plot.py first'

    costs = data['costs']
    delta = data['split_change_vs_merged_percent']
    rows = []
    for label, key, digits in [
        ('块内叶单元面积 / µm²', 'private_leaf_area_um2', 1),
        ('父层标准单元面积 / µm²', 'parent_stdcell_area_um2', 1),
        ('合计叶单元面积 / µm²', 'implemented_leaf_area_um2', 1),
        ('硬宏占地 / µm²', 'hard_macro_footprint_um2', 1),
        ('共同 die / µm²', 'common_die_area_um2', 0),
        ('块内信号线 / µm', 'private_signal_wire_um', 0),
        ('父层信号线 / µm', 'parent_signal_wire_um', 0),
        ('总信号线 / µm', 'total_signal_wire_um', 0),
        ('块内信号通孔', 'private_signal_vias', 0),
        ('父层信号通孔', 'parent_signal_vias', 0),
        ('总信号通孔', 'total_signal_vias', 0),
        ('完整提取 setup WNS / ns', 'complete_setup_ws_ns', 6),
        ('完整提取 hold WNS / ns', 'complete_hold_ws_ns', 6)]:
        rows.append([label] + [f'{costs[k][key]:,.{digits}f}' for k in ['split', 'merged']])
    totals = table(['指标', '拆分 ACT + MXU', '合并 ACT/MXU'], rows)
    blocks = []
    for kind, label in [('act', 'ACT'), ('mxu', 'MXU'), ('merged', '合并')]:
        q = evaluate(records[selection[kind]])
        blocks.append([label, f"{q['area_um2']:,.1f}", f"{q['setup_ns']:+.6f}",
                       f"{q['hold_ns']:+.6f}", f"{q['worst_cap_margin_fF']:+.6f}",
                       f"{q['signal_wire_um']:,}", f"{q['signal_vias']:,}"])
    block_table = table(['块', '叶面积 µm²', 'setup ns', 'hold ns', 'cap 余量 fF', '信号线 µm', '通孔'], blocks)
    layers = []
    for i in range(2, 11):
        layer = 'metal' + str(i)
        layers.append(['M' + str(i)] + [f"{costs[k][scope].get(layer, 0):,.0f}"
                      for scope in ['total_signal_wire_by_layer_um', 'parent_signal_wire_by_layer_um']
                      for k in ['split', 'merged']])
    layer_table = table(['层', '拆分总线长 µm', '合并总线长 µm', '拆分父层 µm', '合并父层 µm'], layers)
    classes = sorted(set().union(*(costs[k]['physical_cell_classification'] for k in costs)))
    supports = []
    for cls in classes:
        values = []
        for kind in ['split', 'merged']:
            item = costs[kind]['physical_cell_classification'].get(cls)
            values.append(f"{item['count']:,} / {item['area']:,.2f}" if item is not None else '原生未单列')
        supports.append([cls] + values)
    support_table = table(['原生类别', '拆分：数量 / 面积 µm²', '合并：数量 / 面积 µm²'], supports)
    evidence = []
    roles = dict(selection)
    roles.update({key: data[key] for key in ['functional_proof', 'parent_functional_proof',
                                            'stitch_proof', 'inventory_proof', 'annotation_proof']})
    for role, name in roles.items():
        record = records[name]
        evidence.append([role, name, record['scheduler'].split('|')[0],
                         record['spec']['runner_commit'], record['output_manifest_sha256']])
    evidence_table = table(['角色', '封存尝试', 'Slurm', '实际 runner commit', '输出清单 SHA256'], evidence)
    quality = []
    for kind, name in selection.items():
        record = records[name]
        q = evaluate(record)
        full = record.get('full-hierarchy-quality.json', {})
        quality.append([kind, '通过：全部严格门槛', f"{q['worst_cap_margin_fF']:+.6f}",
                        '通过' if full.get('passed') else '块内独立 STA',
                        '通过' if record.get('final-pg/strict-pg.json', {}).get('passed') else '块内实现'])
    quality_table = table(['实现', 'DRC / 天线 / setup / hold / 电气', '最差 cap 余量 fF', '完整层次 STA', '最终父层 PG'], quality)
    tools = table(['实际镜像 / ELF', 'SHA256'], sorted(data['toolchain_sha256'].items()))
    summary = (f"在本次固定版图和统一预算下，拆分相对合并的合计叶单元面积变化为 "
               f"{delta['implemented_leaf_area_um2']:+.2f}%，总信号线长变化为 "
               f"{delta['total_signal_wire_um']:+.2f}%，总信号通孔变化为 "
               f"{delta['total_signal_vias']:+.2f}%。两组实际完整路径均满足 2.5ns 时钟和 0.5ns IO 预算。")
    body = f'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>openTPU ACT/MXU 同资源物理对照</title>
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f7;color:#172b3a;font:16px/1.7 "Microsoft YaHei",system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;background:white;padding:44px 48px}}h1{{font-size:30px;line-height:1.35}}h2{{font-size:23px;margin-top:38px;border-bottom:1px solid #d9e2e8;padding-bottom:8px}}
p{{max-width:100ch}}a{{color:#175e99}}.eyebrow{{color:#526b7e;font-size:14px}}.lead{{padding:18px 22px;background:#eaf3fa;border-left:4px solid #3478b9}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin:12px 0}}th,td{{padding:9px 12px;border-bottom:1px solid #e1e7eb;text-align:left;vertical-align:top}}th{{background:#edf2f6;white-space:nowrap}}
td:not(:first-child){{font-variant-numeric:tabular-nums}}.scroll{{overflow:auto}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto}}figcaption,.note{{color:#526574;font-size:14px}}code{{overflow-wrap:anywhere}}details{{margin:16px 0}}summary{{cursor:pointer;font-weight:600}}footer{{margin-top:40px;border-top:1px solid #d9e2e8;padding-top:16px;font-size:13px;color:#526574}}
@media(max-width:700px){{main{{padding:24px 18px}}h1{{font-size:25px}}}}@media print{{body{{background:white}}main{{padding:0}}details{{display:block}}figure,table{{break-inside:avoid}}}}
</style><main>
<p class="eyebrow">Issue #15 · Nangate45 typical · H1 工程实验 · 冻结提取结果</p>
<h1>openTPU ACT/MXU 同功能、同资源的拆分与合并物理对照</h1>
<p class="lead">{escape(summary)}</p>
<p>本轮完成三种块内实现及两种父层布线，持续修复真实提取后的电气、setup、hold 和几何违例。只从全部通过资格门槛的终态生成本页；失败过程和调整依据见<a href="issue-15-opentpu-comparison.md">实验记录</a>。</p>
<h2>对照条件</h2>
<p>同一 openTPU 源 f237dab2f196855a59a083b1454786df8f01291f，small 参数 D32、MCOLS2、ROWS2、ACT_BLOCKS32、LANES4、DEPTH64、IMPL2、CL16、E0、SID0。合并直接连接并展开同一对已映射网表，关闭额外逻辑优化。初始 169109 个映射单元、37023 个 DFF、12 个 synthetic SRAM；非支持逻辑、状态及 SRAM 库存与功能锥证书通过。</p>
<p>40 个外部端口、1662bit，2.5ns 时钟、0.5ns 输入输出预算、BUF_X4/Z 输入驱动、5fF 输出负载、50ps 时钟转换。拆分暴露 684bit 地址数据与 1bit computing 反馈，无新增流水、缓存或串行化。两组父层同为 1670×1670µm，实际外部引脚逐 bit 几何一致；ACT 位于 (80,80)、MXU 位于 (486.205,80)，合并位于 (80,80)，方向 R0。</p>
<p>块内保留 M1–M9，详细 LEF 无 M10；父层信号可用 M2–M10，PG 使用 M1/M4/M7/M10，保留详细宏障碍并核对最终 VDD/VSS 连通。物理缓冲、驱动升级、时钟树等允许变化，全部计入面积与布线成本。</p>
<h2>完整系统结果</h2>{totals}
<p class="note">叶单元面积含同一批 SRAM 和非填充支持单元。硬宏占地、父层 die 单独列示，不再叠加到宏内叶面积。信号线与通孔排除 special PG。WNS 来自真实父层与子块网表、分层 SPEF 的完整路径分析，不能相加各块 WNS。</p>
<figure><img src="assets/issue-15-ppa.png" alt="拆分与合并的面积、信号线、通孔和完整时序对比"><figcaption>块内与父层成本分开计量；完整 setup 与 hold 均为实际提取结果。</figcaption></figure>
<figure><img src="assets/issue-15-floorplans.png" alt="相同父层边界中的实际最终宏盒形"><figcaption>从最终数据库 PG 几何审计读取宏盒形；外框和 1662bit 外部引脚相同。</figcaption></figure>
<h2>块内结果与接口代价</h2>{block_table}
<p>块内单独的面积或线长不能代表整机成本：拆分后还需为跨块接口、外部 IO 与时钟完成父层布线及驱动修复。冻结 ACT 输出的内部既有负载会占用电容预算，例如 r_data[471] 内部负载 26.4487fF、驱动上限 60.654fF，留给外部线与接收端约 34.2053fF。父层长线可能使冻结块内部驱动真实过载；本轮通过边界缓冲隔离并重新完整提取验收。</p>
<details><summary>物理支持单元分类与面积</summary>{support_table}<p class="note">使用原生工具分类。buffer 类可能包含 CTS 等缓冲；缺少独立 clock_buffer 类不代表没有时钟树。所有非填充支持单元均计入总面积，不能将这些类别再与总面积相加。</p></details>
<h2>金属层使用与预制底座含义</h2>
<figure><img src="assets/issue-15-routing-layers.png" alt="块内加父层以及父层单独的逐层信号线长"><figcaption>原生详细布线逐层表；四舍五入到整数 µm，总长与 JSON 指标交叉核对。</figcaption></figure>
<p>本次父层 M10 以下的信号线占比：拆分 {costs['split']['parent_signal_wire_below_m10_percent']:.2f}%，合并 {costs['merged']['parent_signal_wire_below_m10_percent']:.2f}%。这是本次允许全父层路由的实际资源使用，不能据此证明其他受限定制层方案可行或不可行。</p>
<p>面向少量掩模定制，下一步须在底座冻结前同时定义边界驱动能力、块内既有负载、允许的外部电容和转换时间、预制缓冲及轨道资源，并在指定定制层集合内重新实现。当前 H1 仍依赖新增有源单元，尚未实现 H2 的冻结资源和少量定制层约束。</p>
<details><summary>逐层线长明细</summary>{layer_table}</details>
<h2>验收与证据</h2>{quality_table}
<p>全部选定来源同时通过 DRC、天线、setup/hold 及 TNS、电容/转换/fanout 计数和有符号余量门槛。父层另通过最终原生 PG、实际引脚一致性、完整真实分层 STA。三块及两父层功能证书、精确非支持资源库存、双子块边界 RC 自检、实际原生标注覆盖审计齐备；双子块自检另以漏父层 RC 负例确认检查敏感性。</p>
<details><summary>选定作业、实际 runner 与封存清单</summary>{evidence_table}</details>
<details><summary>实际计算节点镜像与工具身份</summary>{tools}<p class="note">工具 ELF 以 SHA256 确定；OpenROAD 版本字符串为 unknown，不将官方 master 当作本机精确源码。Yosys 报告 0.68+post，git 版本未知；STA 为嵌入式。所有新 Slurm 作业实际 UNLIMITED，不设完成期限或耗时取消策略。</p></details>
<p>证明和 STA 实际读取的网表、SPEF、SDC 摘要与对应源封存输出绑定；首次终态清单摘要保持不变，共享输入摘要一致。原始物理数据库与日志保存在获授权集群 <code>/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/</code>，仓库保留轻量回执、脚本和索引。</p>
<h2>适用范围</h2>
<p>这是一个 small 参数、单 typical 角点、固定宏位置、外部引脚和随机种子的工程对照，未做多布局、多种子或多工艺角点搜索，差值不能推广为普遍最优结论。synthetic SRAM 没有真实 GDS；上游 RTL 通用形式等价、生产签核与制造版 GDS 未完成。层次 STA 工具仍提示实验功能；共同 SDC 对 clk 的 input delay 被原生忽略，数据预算与时钟约束一致，未为消除提示修改某组约束。</p>
<footer>冻结观测：{escape(snapshot['observed_utc'])}<br>输入快照 SHA256：<code>{data['input_snapshot_sha256']}</code><br>
<a href="https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15">Issue #15</a> · <a href="https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17">PR #17</a> · <a href="issue-15-opentpu-comparison.md">实验过程与失败证据</a></footer>
</main></html>'''
    OUT.write_text(body, encoding='utf-8')
    files = [OUT, RESULTS / 'comparison.json', RESULTS / 'comparison-inputs.json']
    files += [OUT.parent / 'assets' / (name + '.' + suffix) for name in images for suffix in ['png', 'svg']]
    receipt = dict(runner_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                   input_snapshot_sha256=data['input_snapshot_sha256'],
                   files={str(path.relative_to(REPO)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in files})
    (RESULTS / 'report-manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(OUT)


if __name__ == '__main__':
    main()
