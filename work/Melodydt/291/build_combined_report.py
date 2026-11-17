"""Combine frozen speed and covered-energy results; do not rerun simulations."""
import csv
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from html import escape
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OUT = REPO/'output/pdf/seven-model-speed-and-energy-evaluation.pdf'
ORDER = ['qwen3', 'llama', 'phi', 'gemma', 'granite', 'qwen35', 'falcon']
ENERGY_COMMIT = '78812ea98ddc5714ea3e71d789b9800a4641bb7e'
SPEED_COMMIT = '0550231032102ffde7d6cf24ea659f3fd9a9dbbe'
ENERGY_DATA_COMMIT = '3ce71cc712439da45580e7c89f8533e6a5ff0d25'
SCOPE_NAMES = {'on_chip': '片上已覆盖', 'on_chip_plus_ddr': '片上已覆盖＋DDR'}
WINDOW_NAMES = {'prefill': '短 Prefill', 'decode': '第2步 Decode'}
PAPER = ('我们在统一的三路P并行FFN与512-bit SRAM配置下，对覆盖稠密Transformer、混合专家及注意力与递推混合架构的七个大模型进行了全层系统级仿真。'
         '两输入token的短Prefill吞吐为4.01-23.45 token/s，从真实512位置历史开始的两步Decode代表窗口吞吐为2.03-7.15 token/s。'
         '结合电路级分项标定与DDR器件模型，在当前已覆盖的片上模块加DDR器件口径下，短Prefill和Decode能耗分别估计为0.163-1.033 J/输入token和0.491-1.864 J/输出token；'
         'DDR器件约占已覆盖能耗的67.7%-73.0%，表明存储访问是后续性能与能耗优化的重要关注点。'
         '这些结果验证了该映射与调度流程在系统仿真层面对不同模型架构的适用性，并量化了当前实现的执行效率与已覆盖能耗。')
PAPER_EN = ('We evaluate seven LLMs spanning dense Transformers, mixture-of-experts models, and hybrid attention-recurrent architectures through full-layer system-level simulation under a common three-P parallel-FFN configuration with 512-bit SRAM interfaces. '
            'The two-input-token prefill tests achieve 4.01-23.45 input tokens/s, while the representative interval in two-step decoding from 512 positions of real history achieves 2.03-7.15 output tokens/s. '
            'Combining circuit-level component calibration with a DDR device model, estimated energy for the currently covered on-chip components plus DDR devices ranges from 0.163 to 1.033 J/input token for short prefill and from 0.491 to 1.864 J/output token for decoding. '
            'DDR devices account for approximately 67.7%-73.0% of this covered energy, identifying memory access as an important target for further performance and energy optimization. '
            'These results demonstrate the applicability of the mapping and scheduling flow across model architectures at the system-simulation level and quantify the execution efficiency and covered energy of the current implementation.')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)


def collect():
    manifest_path = ROOT/'combined-inputs.json'
    if manifest_path.exists():
        manifest = load(manifest_path)
        for entry in manifest['inputs']:
            assert sha(REPO/entry['path']) == entry['sha256'], entry['path']
    speed_path = ROOT/'seven-model-speed-results.json'
    speed = load(speed_path)['models']
    energy_index_path = REPO/'work/Melodydt/280/energy_report_models.json'
    energy_index = load(energy_index_path)
    assert energy_index['revision'] == '2.1'
    assert energy_index['source_commit'] == ENERGY_DATA_COMMIT
    assert not energy_index['wire_parasitics_loaded']
    inputs = [dict(path=str(x.relative_to(REPO)).replace('\\', '/'), sha256=sha(x), source_commit=c)
              for x, c in [(speed_path, SPEED_COMMIT), (energy_index_path, ENERGY_COMMIT)]]
    data = []
    for model in ORDER:
        s = speed[model]
        item = next(m for m in energy_index['models'] if m['result'] == model+'_tlm_power_v2_no_wire.json')
        path = REPO/'work/Melodydt/280'/item['result']
        assert sha(path) == item['result_sha256'], path
        inputs.append(dict(path=str(path.relative_to(REPO)).replace('\\', '/'), sha256=sha(path), source_commit=ENERGY_DATA_COMMIT))
        energy = load(path)
        windows = {}
        for key in ['prefill', 'decode']:
            w = energy['windows'][key]
            expected_tokens = 2 if key == 'prefill' else 1
            assert w['tokens'] == expected_tokens
            time_s = w['elapsed_ps']/1e12
            throughput = expected_tokens/time_s
            close(throughput, s['short_prefill_input_tok_s' if key == 'prefill' else 'decode_tok_s'])
            close(time_s*1000, s['short_prefill_ms' if key == 'prefill' else 'decode_interval_ms'])
            row = dict(tokens=expected_tokens, duration_s=time_s, tokens_per_second=throughput, scopes={})
            for scope, original in [('on_chip', 'covered_on_chip_subtotal'), ('on_chip_plus_ddr', 'covered_subtotal')]:
                src = w[original]
                ej = [x/1e9 for x in src['energy_nj_per_window']]
                jpt = [x/expected_tokens for x in ej]
                pw = [x/time_s for x in ej]
                tpj = [1/jpt[1], 1/jpt[0]]
                assert 0 < jpt[0] <= jpt[1]
                for i in range(2):
                    close(jpt[i], src['energy_mj_per_token'][i]/1000)
                    close(pw[i], src['average_power_w'][i])
                    close(pw[i], jpt[i]*throughput)
                close(tpj[0], throughput/pw[1])
                close(tpj[1], throughput/pw[0])
                row['scopes'][scope] = dict(average_power_w=pw, energy_j_per_token=jpt,
                                           tokens_per_joule=tpj, energy_j_per_window=ej)
            ddr = [x/1e9 for x in w['components']['ddr_devices']['energy_nj_per_window']]
            chip, total = [row['scopes'][scope]['energy_j_per_window'] for scope in ['on_chip', 'on_chip_plus_ddr']]
            for i in range(2):
                close(chip[i]+ddr[i], total[i])
            row['ddr_share_percent'] = [100*ddr[0]/total[1], 100*ddr[1]/total[0]]
            row['ddr_energy_j_per_window'] = ddr
            windows[key] = row
        pts = [x for curve in s['curves'] for x in curve['samples']]
        mid = max(abs(x['deviation_percent']) for x in pts if 16 <= x['context'] < 512)
        all_err = max(abs(x['deviation_percent']) for x in pts if 2 <= x['context'] <= 512)
        close(mid, s['component_max_deviation_percent'])
        for curve in s['curves']:
            points = {x['context']: x for x in curve['samples']}
            low, high = points[2]['actual_ps'], points[512]['actual_ps']
            for c, x in points.items():
                predicted = low+(c-2)*(high-low)/510
                close(predicted, x['affine_ps'])
                close(100*(x['actual_ps']-predicted)/x['actual_ps'], x['deviation_percent'])
        data.append(dict(model=model, name=s['name'], speed=s, windows=windows,
                         local_intermediate_max_error_percent=mid, local_all_c2_512_max_error_percent=all_err,
                         full_prefill512_prediction_error_percent=None,
                         prefill512_power_evaluated=False,
                         optimization=item['implementation'], energy_exclusions=item['subtotal_exclusions']))
    stamp = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    manifest = dict(inputs=inputs, speed_commit=SPEED_COMMIT, energy_report_commit=ENERGY_COMMIT,
                    energy_data_commit=ENERGY_DATA_COMMIT, input_verification='passed')
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    ranges = {}
    for window in ['prefill', 'decode']:
        for metric in ['average_power_w', 'energy_j_per_token', 'tokens_per_joule']:
            values = [r['windows'][window]['scopes']['on_chip_plus_ddr'][metric] for r in data]
            ranges[window+'_'+metric] = [min(v[0] for v in values), max(v[1] for v in values)]
    values = [r['windows'][w]['ddr_share_percent'] for r in data for w in ['prefill', 'decode']]
    ranges['ddr_share_percent'] = [min(v[0] for v in values), max(v[1] for v in values)]
    output = dict(updated=stamp, models=data, ranges=ranges, sources=manifest,
                  power_scope='covered subtotals only; no wire parasitics; read DMA proxy excluded',
                  paper_chinese=PAPER, paper_english=PAPER_EN)
    (ROOT/'combined-results.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (ROOT/'combined-power-units.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['model', 'window', 'scope', 'duration_s', 'tokens', 'power_W_low', 'power_W_high',
                         'J_per_token_low', 'J_per_token_high', 'token_per_J_low', 'token_per_J_high'])
        for row in data:
            for phase, w in row['windows'].items():
                for scope, v in w['scopes'].items():
                    writer.writerow([row['name'], phase, scope, w['duration_s'], w['tokens']]
                                    +v['average_power_w']+v['energy_j_per_token']+v['tokens_per_joule'])
    return output


def render(result):
    pdfmetrics.registerFont(TTFont('Deng', 'C:/Windows/Fonts/Deng.ttf'))
    pdfmetrics.registerFont(TTFont('DengBold', 'C:/Windows/Fonts/Dengb.ttf'))
    pdfmetrics.registerFontFamily('Deng', normal='Deng', bold='DengBold', italic='Deng', boldItalic='DengBold')
    navy = colors.HexColor('#17324D')
    red = colors.HexColor('#9A3412')
    styles = {
        'body': ParagraphStyle('Body', fontName='Deng', fontSize=10, leading=15, textColor=navy, wordWrap='CJK', spaceAfter=7),
        'title': ParagraphStyle('Title', fontName='DengBold', fontSize=23, leading=30, textColor=navy, spaceAfter=12),
        'h1': ParagraphStyle('H1', fontName='DengBold', fontSize=16, leading=22, textColor=navy, spaceAfter=9, spaceBefore=5, keepWithNext=True),
        'h2': ParagraphStyle('H2', fontName='DengBold', fontSize=11.5, leading=17, textColor=navy, spaceAfter=6, spaceBefore=9, keepWithNext=True),
        'small': ParagraphStyle('Small', fontName='Deng', fontSize=8.3, leading=12, textColor=colors.HexColor('#53677A'), wordWrap='CJK', spaceAfter=6),
        'cell': ParagraphStyle('Cell', fontName='Deng', fontSize=9, leading=12.5, wordWrap='CJK', textColor=navy),
        'th': ParagraphStyle('TH', fontName='DengBold', fontSize=9, leading=12.5, wordWrap='CJK', textColor=navy),
        'warning': ParagraphStyle('Warning', fontName='DengBold', fontSize=9.5, leading=14, wordWrap='CJK', textColor=red),
        'english': ParagraphStyle('English', fontName='Deng', fontSize=9.5, leading=14, textColor=navy, spaceAfter=8),
    }
    width = A4[0]-32*mm
    story, checks = [], []

    def p(text, style='body'):
        story.append(Paragraph(escape(text).replace('\n', '<br/>'), styles[style]))

    def heading(text):
        p(text, 'h1')

    def warn(text):
        table = Table([[Paragraph(escape(text).replace('\n', '<br/>'), styles['warning'])]], colWidths=[width])
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF2E8')),
                                  ('BOX', (0, 0), (-1, -1), .9, colors.HexColor('#C25331')),
                                  ('LEFTPADDING', (0, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                                  ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
        story.extend([table, Spacer(1, 9)])
        checks.append(text)

    def table(headers, rows, weights=None):
        weights = weights or [1]*len(headers)
        cells = []
        for ri, row in enumerate([headers]+rows):
            current = []
            for v in row:
                text = str(v)
                checks.append(text)
                formatted = escape(text).replace('\n', '<br/>')
                if text == 'Granite3.1-3B-A800M':
                    formatted = 'Granite3.1-3B-<br/>A800M'
                current.append(Paragraph(formatted, styles['th' if ri == 0 else 'cell']))
            cells.append(current)
        tab = Table(cells, colWidths=[width*x/sum(weights) for x in weights], repeatRows=1, hAlign='LEFT')
        tab.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8EFF5')),
                                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FB')]),
                                ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#C7D5E1')),
                                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                                ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
        story.extend([tab, Spacer(1, 8)])

    def interval(value, digits=4):
        text = ('{0:.'+str(digits)+'f} - {1:.'+str(digits)+'f}').format(*value)
        return text

    def page(title):
        story.append(PageBreak())
        heading(title)

    models = result['models']
    p('七模型速度与功耗评估', 'title')
    p('短 Prefill · 代表性 Decode · 512-token Prefill 条件估计', 'h2')
    p('2026-11-17（Asia/Shanghai）｜Issue #291 / PR #292｜速度快照 #291；功耗快照 #280 v2.1', 'small')
    warn('512-token Prefill 为估算，完整序列预测误差尚未知。功耗为当前已覆盖分项小计，主动排除布线寄生，仍有未标定硬件；不能视为完整芯片功耗或物理签核结果。')
    p('速度汇总', 'h2')
    table(['模型', '短P2\n输入token/s', 'Decode\n输出token/s', '估计P512\n至logits s', '估计P512\n输入token/s'],
          [[r['name'], format(r['speed']['short_prefill_input_tok_s'], '.3f'), format(r['speed']['decode_tok_s'], '.3f'),
            format(r['speed']['estimated_prefill_to_logits_s'], '.3f'), format(r['speed']['estimated_input_tok_s_to_logits'], '.3f')] for r in models],
          [1.5, 1, 1, 1, 1])
    p('短P2：空状态输入两个token，计时到第二位置末层完成。Decode：从真实512位置历史开始运行两步，以两次退休间隔取倒数。P512：当前逐token调度下的512位置主体估计，再加一次最终归一化及词表头。三种窗口不同，不直接互当同口径的速度提升比例。')
    p('共同配置：batch=1，三路P并行FFN，逻辑SRAM数据接口512 bit；3334 ps核周期，双通道DRAMsim3。源短程数值验收与DDR/SRAM事务回执沿用已发布结果。')
    p('报告导航：第2页为误差百分比及估计方法；第3-4页为两种功耗范围的三单位汇总；随后列覆盖范围、逐模型优化、论文用语及来源。', 'small')

    page('512-token Prefill 估计与误差口径')
    p('以下百分比均为局部ATT计时与端点直线的最大绝对相对偏差。它们是现有采样可复算的误差指标，不能转写为完整模型P512预测的误差界。')
    table(['模型', '原中间点\n最大偏差 %', '全部2-512采样\n最大偏差 %', '完整P512\n预测误差 %'],
          [[r['name'], format(r['local_intermediate_max_error_percent'], '.2f'),
            format(r['local_all_c2_512_max_error_percent'], '.2f'), '未知／未验证'] for r in models], [1.6, 1, 1.15, 1.05])
    p('偏差 = 100 × |局部采样时间 - 端点直线时间| / 局部采样时间。端点为c=2与512。原中间点口径使用16≤c<512；完整采样口径纳入2≤c≤512中的所有已测点，补入4、7、8、9等短长度。不是对每个整数长度都执行采样。')
    warn('Phi与Falcon的原中间点偏差超过10%；加入短长度后，两者最大偏差均为14.83%，Llama与Granite为8.64%。按既有授权仍保留线性估计，醒目标注适用性限制；不能据此宣称整段预测具有相同百分比的误差。')
    p('估计公式', 'h2')
    p('L = 第二Prefill位置增量（可见KV=2）；H = 第二Decode末层完成 - 第一次退休（可见KV=514）。\nb = (H-L)/512。\nT主体(512) = P1 + Σ(c=2…512)[L+b(c-2)]。\nT至logits(512) = T主体(512) + 一次最终尾部。')
    p('P1保留第一次启动开销；主机选词、网络和服务队列未独立计时，因此不称已验证TTFT。新增330个ATT局部样本使用冻结KV前缀及合成查询；8个递推样本只比较零态和真实512末态。MoE长提示词路由、中间真实递推状态及整模型竞争仍不充分。16/32-token独立序列验证按用户要求暂缓。', 'small')

    for phase in ['prefill', 'decode']:
        page(WINDOW_NAMES[phase]+' 的功耗与能效')
        p('本页Prefill按2个输入token归一化。' if phase == 'prefill' else '本页Decode为两次退休间的代表窗口，按1个输出token归一化；不代表长序列稳态统计。')
        for scope in ['on_chip_plus_ddr', 'on_chip']:
            p(SCOPE_NAMES[scope]+'小计', 'h2')
            table(['模型', '平均功耗\nW', '每token能耗\nJ/token', '能效\ntoken/J'],
                  [[r['name'], interval(r['windows'][phase]['scopes'][scope]['average_power_w']),
                    interval(r['windows'][phase]['scopes'][scope]['energy_j_per_token'], 6),
                    interval(r['windows'][phase]['scopes'][scope]['tokens_per_joule'])] for r in models],
                  [1.5, 1.1, 1.4, 1.1])
        p('区间来自标定样本端点，不是统计置信区间或总误差界。token/J与J/token互为倒数，区间方向反转。读DMA动态代理不计入基础小计。', 'small')
        p('缺项：读DMA真实动态/静默/漏电，部分控制、特殊算术和全局时钟/互连，以及DDR PHY/板级；布线寄生按当前方案主动排除。', 'small')
        if phase == 'prefill':
            warn('本页是短P2功耗，不是512-token Prefill功耗。完整P512的活动计数与能量尚未评估，不能把短P2的平均W直接套入估计P512时间后称为已验证结果。')

    page('计算方法与当前覆盖范围')
    p('三种单位保持相同窗口', 'h2')
    p('设窗口能量为E（J）、时长为T（s）、token数为N：\n平均功耗P = E/T（W）；每token能耗e = E/N（J/token）；能效η = N/E（token/J）。\n因此P = e × token/s，η = 1/e。范围[e低,e高]对应能效[1/e高,1/e低]。')
    p('能量由电路级分项标定与TLM整窗活动组合：开钟/漏电基线 × 驻留时间，加忙时或事件次数 × 相应活动增量；共享模块只计一次。DDR器件用模型自己的访问流与时窗计算。当前数据禁用布线寄生，但原映射网络仍保留缓冲器、局部时钟单元和引脚电容。')
    table(['已有计入', '仍未覆盖或尚待验证'], [
        ['三M普通投影/FFN活动及开钟驻留；G32、U ADD2已支持项', 'RMS、softmax、RoPE及各模型特殊算术的独立功耗'],
        ['四S_P数据站点、局控PM/描述符取指、四母控PM宏；写DMA/PM桥', '读DMA真实活动/空闲/漏电；母控运行取指/启动、局控外壳/分发、交换机实际流量'],
        ['九目标母控核心六样本迁移参考；双通道DDR器件', '真实实例数/门控、未绑定全局时钟与互连；DDR PHY及板级I/O'],
    ], [1, 1])
    warn('旧M在300 MHz仍有setup/hold违例（WNS -1.121800 / -0.053419 ns）。去掉线网寄生不等于修复时序。当前速度为系统级TLM时间，能量为有覆盖边界的模型估算，均不能称硅后实测或完整物理签核。')
    p('误差与不确定性', 'h2')
    p('速度：完整P512独立误差未知；局部采样偏差只反映被采组件。功耗：标定端点跨度仅反映已纳入工况，不覆盖缺失模块、活动迁移、真实部署、延迟毛刺等误差。因此本报告不把功耗端点写为“±误差百分比”，也不把缺项填成零。')

    for r in models:
        s = r['speed']
        page(r['name'])
        p(s['architecture'])
        table(['速度项目', '时间', '吞吐'], [
            ['短Prefill（2输入token）', format(s['short_prefill_ms'], '.6f')+' ms', format(s['short_prefill_input_tok_s'], '.6f')+' 输入token/s'],
            ['Decode（两次退休间）', format(s['decode_interval_ms'], '.6f')+' ms', format(s['decode_tok_s'], '.6f')+' 输出token/s'],
            ['估计P512主体', format(s['estimated_prefill_body_s'], '.6f')+' s', format(s['estimated_input_tok_s_body'], '.6f')+' 输入token/s'],
            ['估计P512至logits', format(s['estimated_prefill_to_logits_s'], '.6f')+' s', format(s['estimated_input_tok_s_to_logits'], '.6f')+' 输入token/s'],
        ], [1.4, 1, 1.3])
        p('局部偏差：原中间点最大'+format(r['local_intermediate_max_error_percent'], '.3f')+'%；全部2-512采样点最大'+format(r['local_all_c2_512_max_error_percent'], '.3f')+'%。完整P512预测误差：未知。', 'small')
        p('功耗与能效', 'h2')
        rows = []
        for phase in ['prefill', 'decode']:
            for scope in ['on_chip_plus_ddr', 'on_chip']:
                e = r['windows'][phase]['scopes'][scope]
                rows.append([WINDOW_NAMES[phase]+'\n'+SCOPE_NAMES[scope], interval(e['average_power_w']),
                             interval(e['energy_j_per_token'], 6), interval(e['tokens_per_joule'])])
        table(['窗口和范围', 'W', 'J/token', 'token/J'], rows, [1.55, 1.1, 1.4, 1.1])
        p('模型实现与专项优化', 'h2')
        p(r['optimization'])
        limitation = ' '.join(s['warnings'])
        if r['model'] in ['phi', 'falcon', 'granite', 'qwen35']:
            warn(limitation)
        else:
            p(limitation, 'small')
        p('该模型功耗缺项', 'h2')
        p(' '.join(r['energy_exclusions']), 'small')
        p('完整512 Prefill的W、J/token和token/J尚未评估。本页能量区间不是误差界，模型特有算术的缺项会影响跨模型能效比较。', 'small')

    page('论文 验证与主要发现 建议表述')
    p('中文稿', 'h2')
    p(PAPER)
    p('对应英文稿', 'h2')
    p(PAPER_EN, 'english')
    warn('投稿时需在实验方法中明确：速度采用短程全层系统级仿真；能量仅计已覆盖项且不加载布线寄生。不能将“已覆盖模块＋DDR”删改成“完整芯片”。该段不声称相对其他加速器的性能或能效优势。')
    p('512-token结果的使用', 'h2')
    p('建议将512-token条件预测留在实验部分，写为“在当前逐token执行方式下，512-token Prefill至logits时间估计为35.923-137.203 s；尚未通过独立完整序列验证”。局部采样偏差约0.96%-10.72%（中间点）或4.46%-14.83%（全部2-512采样点），均不能替代整段误差。')
    p('本轮新增的是评估汇总与论文措辞，不修改原始论文文件，不新增仿真，不改变模型速度或功耗输入。', 'small')

    page('来源与复算')
    p('速度来源：#291 / PR #292，提交'+SPEED_COMMIT+'；采样源码395fe768ceaed45ef2b822d9ce288e1f98f0fe0f，作业38826721，330 ATT与8递推样本。')
    p('功耗来源：#280 / PR #281，报告v2.1提交'+ENERGY_COMMIT+'；数据提交'+ENERGY_DATA_COMMIT+'。在线索引与本地语义一致，七个模型数据SHA全部匹配索引。')
    p('Qwen3采样计划与原速度计划SHA不同；已保留两套来源并确认result除plan_sha256外逐字段一致。此汇总按窗口时间、token数和速度逐一匹配能耗结果，不把路径迁移冒充字节相同。', 'small')
    rows = []
    for e in result['sources']['inputs']:
        rows.append([Path(e['path']).name, e['sha256']])
    table(['输入文件', 'SHA-256'], rows, [1.25, 2.25])
    p('复算命令：\npython -B work/Melodydt/291/build_combined_report.py\npython -B work/Melodydt/291/verify_combined_report.py')
    p('依赖：Python 3.7+、ReportLab 4.4.9、pypdf、Deng/Dengb中文字体；Poppler用于渲染检查。combined-inputs.json冻结来源；combined-results.json与combined-power-units.csv保留未四舍五入数值。', 'small')
    p('PR #292为草稿未合并；文件交付不等于独立审查或物理验收。登记pending，看板缺配置/工具，unverified及同步pending。', 'small')

    def chrome(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFont('Deng', 8)
        canvas.setFillColor(colors.HexColor('#52687A'))
        canvas.drawString(16*mm, h-10*mm, '七模型速度与功耗评估 | 2026-11-17')
        canvas.drawRightString(w-16*mm, h-10*mm, 'TLM速度 / 有限覆盖能耗')
        canvas.setStrokeColor(colors.HexColor('#D5E0E8'))
        canvas.line(16*mm, 12*mm, w-16*mm, 12*mm)
        canvas.drawString(16*mm, 7.5*mm, 'P512为条件估计；功耗小计不代表完整芯片。')
        canvas.drawRightString(w-16*mm, 7.5*mm, str(doc.page))
        canvas.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
                            topMargin=17*mm, bottomMargin=17*mm,
                            title='七模型速度与功耗评估', author='Melodydt')
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    (ROOT/'combined-pdf-expected-text.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (ROOT/'paper-validation-findings.txt').write_text('验证与主要发现\n\n'+PAPER+'\n\nEnglish\n\n'+PAPER_EN+'\n', encoding='utf-8')
    receipt = dict(pdf=str(OUT.resolve()), pdf_sha256=sha(OUT), reportlab=reportlab.Version,
                   checked_sources=len(result['sources']['inputs']), power_rows=28,
                   prior_speed_results_unchanged=True, independent_sequence_validation='deferred by user')
    (ROOT/'combined-build-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    render(collect())
