"""Accumulate seven-model reports without replacing missing samples by measurements."""
import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORDER = ['qwen3', 'llama', 'phi', 'gemma', 'granite', 'qwen35', 'falcon']
INFO = {
 'qwen3': ('Qwen3-0.6B', '28层稠密；128维KV，三P FFN，ATT1分片复用和双窗口流水。'),
 'llama': ('Llama3.2-1B', '16层稠密；64维紧凑KV、256 B行，三P FFN与V读取复用。'),
 'phi': ('Phi4-mini', '32层稠密；融合QKV/Gate-Up，128维ATT1与partial LongRoPE。'),
 'gemma': ('Gemma3-4B', '34层；256维宽注意力，局部/全局层，Q12残差；512目标未跨1024局部窗口。'),
 'granite': ('Granite3.1-3B-A800M', '32层MoE；64维KV，每token动态选择8/40专家，三P按3/3/2波次执行。'),
 'qwen35': ('Qwen3.5-4B', '8层256维全注意力＋24层固定大小GDN状态，三P FFN。'),
 'falcon': ('Falcon-H1-3B', '32层，每层Mamba2与128维注意力；现有程序先递推再注意力，三P FFN。'),
}
ATT1 = int.from_bytes(b'ATT1', 'little')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def analyze(model):
    pp, dp = [ROOT/'inputs'/('{}-{}.json'.format(model, mode)) for mode in ('prefill', 'decode')]
    sp = ROOT/'results'/model/'samples.json'
    pf, dc, sample = load(pp), load(dp), load(sp)
    assert pf['history'] == 0 and dc['history'] == 512
    assert len(pf['boundary']) == len(dc['boundary']) == len(dc['retirements']) == 2
    assert pf['model'] == dc['model'] == sample['model'] == model
    sampling_baseline = dp
    if dc['plan_sha256'] != sample['frozen_plan_sha256']:
        sampling_baseline = ROOT/'inputs'/('{}-sampling-baseline.json'.format(model))
        relocated = load(sampling_baseline)
        assert relocated['plan_sha256'] == sample['frozen_plan_sha256']
        assert {k:v for k,v in dc.items() if k!='plan_sha256'} == {k:v for k,v in relocated.items() if k!='plan_sha256'}
    assert pf['pr272_profile'] == dc['pr272_profile'] == 'combined'
    p1, p2 = [x['complete_ps'] for x in pf['boundary']]
    d1, d2 = [x['complete_ps'] for x in dc['boundary']]
    r1, r2 = [x['time_ps'] for x in dc['retirements']]
    low, high = p2-p1, d2-r1
    slope = (high-low)/512.0
    # Keep observed first-position time (including boot) exactly once.
    body = p1 + 511*low + (510*511//2)*slope
    tail = r2-d2
    total = body+tail
    curves = []
    for layer in sample['selected_layers']:
        rows = [x for x in sample['attention'] if x['layer'] == layer]
        by = {x['context']: x['elapsed_ps'] for x in rows}
        assert sorted(by) == sorted(sample['contexts'])
        assert all(x['ddr'].get('reads',0)+x['ddr'].get('writes',0) == x['ddr'].get('callbacks',0) for x in rows)
        residuals = []
        for c in sorted(by):
            pred = by[2] + (c-2)*(by[512]-by[2])/510.0
            residuals.append(dict(context=c, actual_ps=by[c], affine_ps=pred,
                                  deviation_percent=100*(by[c]-pred)/by[c]))
        interior = [x for x in residuals if 16 <= x['context'] < 512]
        curves.append(dict(layer=layer, max_abs_deviation_percent=max(abs(x['deviation_percent']) for x in interior),
                           samples=residuals))
    deviation = max(x['max_abs_deviation_percent'] for x in curves)
    warnings = []
    if deviation > 5:
        warnings.append('注意力局部采样与两端直线偏差超过5%，仍按用户要求保留全层端点线性估算；不得将此预测写成完整Prefill实测。')
    else:
        warnings.append('局部注意力采样未超过本报告5%筛查阈值；这不代表整段Prefill预测误差已通过5%验证。')
    if model == 'granite':
        warnings.append('MoE条件估算：仅有冻结的4个位置路由；未新增专家组合/长提示词路由扫描，输入相关DDR与波次等待不确定，继续使用线性估算。')
    if model in ('qwen35', 'falcon'):
        warnings.append('混合模型条件估算：递推服务采用固定大小状态的零态/真实512末态局部探针；没有64/128/256真实递推快照或完整前缀回放。')
    breakdown = {}
    for name, data, group in [('prefill_second',pf,'pos1-layers'), ('decode_second',dc,'pos513-layers')]:
        slots = {}
        for kind, condition in [('attention',lambda s:s in (ATT1,15)),('recurrent',lambda s:s==18),
                                ('moe',lambda s:s==17),('other',lambda s:s not in (ATT1,15,18,17))]:
            rows=[x for x in data['services'] if x['group']==group and condition(x['signature'][1])]
            slots[kind] = dict(calls=sum(x['count'] for x in rows),
                               cumulative_service_ps=sum(x['service_ps'] for x in rows),
                               cumulative_dispatch_ps=sum(x['dispatch_ps'] for x in rows))
        breakdown[name]=slots
    routes = [x for data in (pf,dc) for x in data.get('expert_routes',[])]
    frequency = Counter(i for route in routes for i in route['ids'])
    result = dict(model=model, name=INFO[model][0], architecture=INFO[model][1],
        source_commit='395fe768ceaed45ef2b822d9ce288e1f98f0fe0f', sample_job='38826721',
        short_prefill_input_tok_s=pf['tok_s'], short_prefill_ms=p2/1e9,
        decode_tok_s=dc['tok_s'], decode_interval_ms=(r2-r1)/1e9,
        first_prefill_including_boot_ms=p1/1e9, second_prefill_increment_ms=low/1e9,
        decode_second_body_ms=high/1e9, decode_tail_ms=tail/1e9,
        affine_slope_ps_per_context=slope, estimated_prefill_body_s=body/1e12,
        estimated_prefill_to_logits_s=total/1e12,
        estimated_input_tok_s_body=512e12/body, estimated_input_tok_s_to_logits=512e12/total,
        attention_samples=len(sample['attention']), recurrent_samples=len(sample['recurrent']),
        component_max_deviation_percent=deviation, curves=curves,
        nonlinear_screen_exceeded=deviation>5, warnings=warnings, service_totals=breakdown,
        recurrent=[{k:x[k] for k in ('layer','state','elapsed_ps','recurrent_write_beats')} for x in sample['recurrent']],
        frozen_expert_route_records=len(routes), frozen_expert_frequency=dict(sorted(frequency.items())),
        verified_input_sha256={str(x.relative_to(ROOT)):digest(x) for x in (pp,dp,sp,sampling_baseline)},
        sampling_plan_matches_speed_plan=(sampling_baseline==dp),
        independent_sequence_validation='deferred by user',
        full_model_rtl_qualified=False, full_model_timing_calibrated=False)
    assert abs(2e12/p2-pf['tok_s']) < 1e-10
    assert abs(1e12/(r2-r1)-dc['tok_s']) < 1e-10
    assert body > 0 and total > body
    (ROOT/'results'/model/'estimate.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result


def cell(value):
    return html.escape(str(value))


def table(headers, rows):
    return '<table><thead><tr>'+''.join('<th>'+cell(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join(
        '<tr>'+''.join('<td>'+cell(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def render():
    results={m:load(ROOT/'results'/m/'estimate.json') for m in ORDER if (ROOT/'results'/m/'estimate.json').exists()}
    when=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    summary=[]
    for m in ORDER:
        p,d=[load(ROOT/'inputs'/('{}-{}.json'.format(m,mode))) for mode in ('prefill','decode')]
        r=results.get(m)
        summary.append([INFO[m][0],'{:.6f}'.format(p['tok_s']),'{:.3f}'.format(p['interval_ps']/1e9),
                        '{:.3f}'.format(r['estimated_prefill_body_s']) if r else '待整理',
                        '{:.3f}'.format(r['estimated_prefill_to_logits_s']) if r else '待整理',
                        '{:.3f}'.format(r['estimated_input_tok_s_to_logits']) if r else '待整理',
                        '{:.6f}'.format(d['tok_s']),
                        ('⚠ 条件线性' if m in ('granite','qwen35','falcon') or r['nonlinear_screen_exceeded'] else '线性预测，未独立验证') if r else '待整理'])
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>七模型速度仿真与512-token Prefill估算</title>',
      '<style>body{font:16px/1.65 "Microsoft YaHei","Noto Sans CJK SC",sans-serif;max-width:1240px;margin:36px auto;padding:0 22px;color:#172536}h1,h2{color:#102a43}table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}th,td{padding:9px 10px;border:1px solid #cbd5e1;text-align:left}th{background:#eaf0f6}tbody tr:nth-child(even){background:#f8fafc}.warning{border:2px solid #b45309;background:#fff3cd;padding:14px 18px;margin:18px 0}.danger{border-color:#b91c1c;background:#fff0ee;color:#8b1a1a}.muted{color:#53657a}code,pre{background:#eef2f6;padding:3px 5px}section{break-before:page}a{color:#1763a6}@media print{body{margin:12mm;font-size:11pt}table{font-size:9pt}tr{break-inside:avoid}}</style>',
      '<h1>七模型速度仿真与 512-token Prefill 估算</h1>',
      '<p>Issue #291 / PR #292 · Melodydt · '+when+' · 已完成模型 '+str(len(results))+'/7</p>',
      '<div class="warning danger"><strong>全部512-token结果均为预测，未执行完整512-token Prefill；16/32-token独立序列验证按用户要求暂缓。</strong><br>短Prefill和Decode沿用已验收的全层TLM回执。新增采样是冻结组件的局部计时，使用真实KV前缀和固定合成查询向量，不是中间位置的整模型数值回放。预测误差范围未知。</div>',
      '<h2>逐模型速度</h2>',table(['模型','短P 输入tok/s','短P2 ms','估计P512主体 s','估计P512至logits s','估计输入tok/s（含尾部）','已有Decode tok/s','估计资格'],summary),
      '<h2>统一口径与算法</h2><p>Batch=1，三路P FFN，逻辑SRAM/PM写宽512 bit，核周期3334 ps，双通道DRAMsim3 tCK=630 ps，每通道32 credits，权重窗口4、ATT KV窗口8，PR272 combined。保留模型专项优化与冻结数值配置。</p>',
      '<p>短P2从空状态运行两个输入位置，到第二位置末层完成，吞吐=2/时间。Decode从各自真实512位置历史运行两步，以第二次减第一次退休时间的倒数报告；不是长序列稳态统计。</p>',
      '<pre>P1 = 第1个Prefill位置末层完成时刻（含启动一次）\nL = 第2个Prefill位置增量时间（可见KV=2）\nH = 第2步Decode末层完成 - 第1次退休（可见KV=514，不含本步词表头）\nb = (H-L)/512\nT_body(512) = P1 + Σ[c=2..512] (L + b·(c-2))\nT_logits(512) = T_body(512) + (第2次退休 - 第2步末层完成)</pre>',
      '<p>末层口径与原短Prefill对齐；含尾部口径最后仅加一次最终归一化和完整词表头。选词仍沿用主机逻辑，没有独立硬件采样器或网络/服务队列计时，因此不称已验证的用户请求TTFT。输入DDR与反馈token入口、边界残差读、地址布局/DDR状态差异保留为模型不确定性；无多token并行、批处理或新增权重复用收益。Qwen3采样计划与速度回执计划SHA不同，已核对对应完整result.json除plan_sha256外逐字段一致；分别保留两套散列，不宣称计划文件字节相同。</p>',
      '<h2>中间上下文采样与显著性判据</h2><p>每个模型选择前/中/后代表层，Gemma另取全局注意力层。每层测c=1,2,4,7,8,9,16,32,64,65,128,129,256,257,512。采用冻结实际描述符、KV地址及真实历史数据；修改上下文长度并重新计算描述符CRC。独立运行原ATT服务、原DRAMsim3和512-bit S128端口，记录回包/排空、输出哈希和输入来源。固定Q仅用于计时敏感性，不宣称对应前缀数值输出正确。</p>',
      '<p>局部筛查比较c=2与512两端连线，在16≤c&lt;512的采样点计算|实际-直线|/实际。5%只是预先声明的局部非线性筛查阈值，不是整模型精度保证；超过阈值仍按用户要求保留端点线性估算并加红色注释。短长度还存在分片/拍数取整。局部采样未包括投影和母控竞争，模型主表继续锚定全层回执，不将组件耗时直接累加为全层耗时。</p>',
      '<p>混合模型补首/末递推层各零态与真实512末态探针，激活输入为固定合成值，使用真实参数及状态读写；不将末态截短冒充中间前缀。Granite只分析已有路由，未新增长提示词路由分布实验。</p>']
    for m,r in results.items():
        parts += ['<section><h2>'+cell(r['name'])+'</h2><p>'+cell(r['architecture'])+'</p>',
          '<div class="warning '+('danger' if m in ('granite','qwen35','falcon') or r['nonlinear_screen_exceeded'] else '')+'">'+
          '<br>'.join('<strong>'+cell(x)+'</strong>' for x in r['warnings'])+'</div>',
          table(['短P2 ms','P1含启动 ms','L ms','H ms','最终尾部 ms','P512主体 s','P512至logits s','Decode tok/s'], [[
            '{:.6f}'.format(r[k]) for k in ['short_prefill_ms','first_prefill_including_boot_ms','second_prefill_increment_ms','decode_second_body_ms','decode_tail_ms','estimated_prefill_body_s','estimated_prefill_to_logits_s','decode_tok_s']]]),
          '<p>新增注意力样本 '+str(r['attention_samples'])+'；递推样本 '+str(r['recurrent_samples'])+'。局部采样最大直线偏差 '+format(r['component_max_deviation_percent'],'.3f')+'%，不代表全层预测误差。</p>']
        for curve in r['curves']:
            parts += ['<h3>代表层 '+str(curve['layer'])+'：注意力长度采样</h3>', table(['可见KV位置','局部服务 µs','端点直线 µs','偏差 %'],
                [[x['context'],format(x['actual_ps']/1e6,'.3f'),format(x['affine_ps']/1e6,'.3f'),format(x['deviation_percent'],'.3f')] for x in curve['samples']])]
        if r['recurrent']:
            parts += ['<h3>固定大小递推状态敏感性</h3>',table(['层','状态载荷','局部服务 ms','写回64 B拍'],
                [[x['layer'],x['state'],format(x['elapsed_ps']/1e9,'.6f'),x['recurrent_write_beats']] for x in r['recurrent']])]
        if r['frozen_expert_route_records']:
            parts += ['<p>已有路由记录 '+str(r['frozen_expert_route_records'])+' 条（4个位置×32层），覆盖专家 '+str(len(r['frozen_expert_frequency']))+'/40；跨层合并计数不等于每层路由分布已经充分覆盖。</p>']
        rows=[]
        for phase,classes in r['service_totals'].items():
            for name,x in classes.items():
                rows.append([phase,name,x['calls'],format(x['cumulative_service_ps']/1e9,'.6f'),format(x['cumulative_dispatch_ps']/1e9,'.6f')])
        parts += ['<h3>已有全层服务计时拆分</h3><p>以下是CALL累计忙时/分发时间，用于归因；三P可能并行，不能将这些列直接相加作为总延迟。</p>',table(['阶段','类别','CALL数','累计服务 ms','累计分发 ms'],rows),
          '<p class="muted">输入与样本SHA-256：<br>'+'<br>'.join(cell(k)+'：'+cell(v) for k,v in r['verified_input_sha256'].items())+'</p></section>']
    parts += ['<section><h2>追溯、复算与未完成项</h2><p>源码提交395fe768ceaed45ef2b822d9ce288e1f98f0fe0f，起点89b02b0424e3ab923fca320509a4058692bd5f97；原速度结果d8f775b661c511d6450d5cbe63f4519563114895。采样作业38826721，BSCC-T6，v6_384/m3ca0801，7×1核，UNLIMITED。</p>',
      '<p>服务器目录：~/LLMHardware/zenanyan/issue-291-prefill-01/run-38826721。38826673在容器挂载前失败；38826697在只读窗口缺失零写计数字段时失败。失败回执保留，不计入结果。</p>',
      '<pre>python -B work/Melodydt/291/build_speed_report.py --all\nsacct -j 38826721 -X --format=JobID,State,ExitCode,Elapsed,NodeList,Timelimit</pre>',
      '<p>后续：独立16/32-token验证；必要时补中间位置整层、MoE路由、混合状态与不同布局；完整P512数值及RTL/物理时序校准。此前约36秒的Qwen3粗估现改为首位置原始时间只计一次，数值微调属计时边界修正，非性能优化。</p>',
      '<p><a href="https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/292">PR #292</a> · <a href="https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/291">Issue #291</a>。报告完成与PR审查/合并分开；登记pending，看板缺配置/工具，unverified/pending。</p></section></html>']
    (ROOT/'seven-model-speed-report.html').write_text('\n'.join(parts),encoding='utf-8')
    (ROOT/'seven-model-speed-results.json').write_text(json.dumps(dict(updated=when,models=results),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',choices=ORDER)
    parser.add_argument('--all',action='store_true')
    args=parser.parse_args()
    for model in (ORDER if args.all else [args.model] if args.model else []):
        r=analyze(model)
        render()
        print(json.dumps({k:r[k] for k in ('model','short_prefill_input_tok_s','estimated_prefill_body_s',
              'estimated_prefill_to_logits_s','estimated_input_tok_s_to_logits','decode_tok_s',
              'attention_samples','recurrent_samples','component_max_deviation_percent','nonlinear_screen_exceeded')},ensure_ascii=False))
    if not args.all and not args.model:
        render()
