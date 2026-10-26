"""Build a self-contained Chinese HTML report and Python-authored interactive SVGs."""
from pathlib import Path
from html import escape as esc
import base64,json,math
import pandas as pd

ROOT=Path(__file__).resolve().parent

def number(x,d=2):return f'{x:,.{d}f}' if isinstance(x,float) else f'{x:,}' if isinstance(x,int) else str(x)
def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join(f'<th>{esc(str(x))}</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{str(x)}</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def image(name,caption):
    raw=base64.b64encode((ROOT/name).read_bytes()).decode()
    return f'<figure><a href="{name}" target="_blank"><img src="data:image/png;base64,{raw}" alt="{esc(caption)}"></a><figcaption>{caption} · <a href="{name}">PNG</a> / <a href="{name[:-4]}.svg">SVG</a></figcaption></figure>'
def interactive(case):
    from analyze_layout import COLORS,LABELS
    df=pd.read_csv(ROOT/f'{case}_pin_coordinates.csv',keep_default_na=False)
    meta=json.loads((ROOT/f'{case}.meta.json').read_text(encoding='utf-8'));w=meta['die_dbu'][2]/2000
    groups={}
    gg=pd.read_csv(ROOT/f'{case}_groups.csv')
    for _,r in gg.iterrows():groups[r.plan,r.pin]=(r.group,r.semantic)
    sets=[]
    for plan,g in df.groupby('plan'):
        ss=[f'<div class="iview" data-case="{case}" data-plan="{plan}" style="display:{"block" if plan=="A" else "none"}"><svg class="pin-svg" viewBox="-20 -35 665 680" role="img" aria-label="{case} {plan} 可查询引脚">']
        ss.append('<rect x="0" y="0" width="600" height="600" fill="#f4f6f8" stroke="#263d58" stroke-width="1"/>')
        for m in meta['macros']:
            x0,y0,x1,y1=[q/2000 for q in m['bbox_dbu']]
            ss.append(f'<rect x="{600*x0/w:.4f}" y="{600*(w-y1)/w:.4f}" width="{600*(x1-x0)/w:.4f}" height="{600*(y1-y0)/w:.4f}" fill="#d9dee5" stroke="#8391a3" stroke-width=".7"/>')
        for k in range(5):
            p=k*150;v=w*k/4
            ss.append(f'<text x="{p}" y="622" text-anchor="middle" fill="#56677d" font-size="11">{v:.1f}</text><text x="-7" y="{600-p}" text-anchor="end" fill="#56677d" font-size="11">{v:.1f}</text>')
        ss.append('<text x="300" y="645" text-anchor="middle" font-size="13">X (μm)；左侧刻度 Y (μm)</text>')
        for _,r in g.iterrows():
            x=600*r.x_um/w;y=600*(w-r.y_um)/w;gn,sem=groups[plan,r.pin]
            text=f'{r.pin} | {r.layer} | {LABELS[r.interface]} | {r.direction}\nXY = ({r.x_um:.6f}, {r.y_um:.6f}) μm\nnet = {r.net}; bundle = {gn}\n{sem}\n目标层未知、保持原连接意图；标记非实际尺寸'
            attrs=f'class="pin" tabindex="0" data-name="{esc(r.pin,quote=True)}" data-bus="{esc(r.bus,quote=True)}" data-layer="{r.layer}" data-cat="{r.interface}" data-x="{r.x_um:.6f}" data-y="{r.y_um:.6f}" data-group="{esc(gn,quote=True)}" fill="{COLORS[r.interface]}"'
            if r.layer=='metal5':shape=f'<circle {attrs} cx="{x:.5f}" cy="{y:.5f}" r="1.5"><title>{esc(text)}</title></circle>'
            else:shape=f'<rect {attrs} x="{x-1.5:.5f}" y="{y-1.5:.5f}" width="3" height="3"><title>{esc(text)}</title></rect>'
            ss.append(shape)
        ss.append('</svg></div>');sets.append(''.join(ss))
    cats=''.join(f'<option value="{k}">{LABELS[k]}</option>' for k in df.interface.unique())
    return f'''<details><summary>交互查询：悬停查看 pin；按功能、层或名称筛选</summary>
    <div class="viewer" data-case="{case}"><div class="tools">
    <label>方案 <select class="ip"><option>A</option><option>B</option><option>C</option></select></label>
    <select class="il"><option value="">全部信号层</option><option value="metal5">M5</option><option value="metal6">M6</option></select>
    <select class="ic"><option value="">全部功能</option>{cats}</select><input class="iq" placeholder="搜索 pin、总线或绘图束，例如 r_data[10]"></div>
    <div class="callout ipick">选择接点可固定显示该 pin 信息；滚轮缩放，拖动平移。</div>
    <div class="svgbox">{''.join(sets)}</div><p class="muted">交互图仅画边界、宏和接点；灰色底不表示可用金属。图形由 Python 生成，筛选不修改坐标。</p>
    <div class="scroll"><table><thead><tr><th>pin</th><th>功能</th><th>层</th><th>方向</th><th>X μm</th><th>Y μm</th><th>网络</th></tr></thead><tbody class="itable"></tbody></table></div><div class="muted icount"></div>
    </div></details>'''

def build(metrics,patches,endpoints):
    from analyze_layout import LABELS,TITLES,PLAN
    extraction=json.loads((ROOT/'extraction_receipt.json').read_text(encoding='utf-8'))
    validation=json.loads((ROOT/'validation.json').read_text(encoding='utf-8'))
    source=json.loads((ROOT/'source-inventory.json').read_text(encoding='utf-8'))
    html=['''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ACT / GEMM · 接口二维接点候选分析</title>
    <style>:root{--bg:#f2f5f9;--ink:#17283c;--muted:#56677d;--line:#d8e1eb;--blue:#185ca5}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.85 "Microsoft YaHei","Segoe UI",sans-serif}aside{position:fixed;inset:0 auto 0 0;width:220px;padding:30px 22px;background:#13263c;color:#e3edf7;overflow:auto}aside a{display:block;color:#c6d7e9;text-decoration:none;padding:8px 0;font-size:14px}aside strong{font-size:21px}main{margin-left:220px;padding:32px 38px 70px;max-width:1900px}header{padding:18px 0 24px}h1{font-size:36px;line-height:1.4;margin:10px 0}h2{font-size:25px;line-height:1.5;margin:0 0 18px}h3{font-size:19px;margin:22px 0 10px}.eyebrow{color:var(--blue);font-size:13px;letter-spacing:2px}.lead{font-size:18px;color:var(--muted)}section{background:white;border:1px solid var(--line);border-radius:14px;padding:28px;margin-bottom:25px}.callout{border-left:4px solid #3b82bf;background:#eef5fc;padding:13px 18px;border-radius:0 7px 7px 0}.warn{border-left-color:#b98127;background:#fff7e8}.muted,figcaption{font-size:13px;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.metric{padding:14px;background:#f2f6fb;border:1px solid var(--line);border-radius:8px}.metric b{display:block;font-size:23px}img{width:100%;display:block;border:1px solid var(--line);border-radius:7px}figure{margin:20px 0}figcaption{margin-top:7px}.scroll{overflow:auto;max-width:100%;margin:16px 0}table{width:100%;border-collapse:collapse;font-size:13px;line-height:1.65;white-space:nowrap}th{background:#eaf1f8;text-align:left}th,td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:hover{background:#f5f9fd}.wrap{white-space:normal}.wrap td{min-width:120px}a{color:var(--blue)}code{font-family:Consolas,monospace;background:#edf2f7;padding:2px 4px;border-radius:3px;font-size:.9em}pre{background:#14263b;color:#e3edf9;border-radius:8px;padding:18px;overflow:auto;line-height:1.7}details{border:1px solid var(--line);padding:12px 16px;border-radius:8px;margin:16px 0}summary{cursor:pointer;font-weight:600}.tools{display:flex;gap:8px;flex-wrap:wrap;margin:15px 0}select,input,button{padding:7px;border:1px solid #b9ccdf;border-radius:5px;background:white;color:var(--ink)}input{min-width:280px}.svgbox{height:680px;overflow:hidden;background:white;border:1px solid var(--line);touch-action:none}.pin-svg{height:100%;width:100%;cursor:grab}.iview{height:100%}.pin{cursor:crosshair}.pin:hover,.pin:focus{stroke:#101d2d;stroke-width:1.5}.ipick{font-size:13px;white-space:pre-line}.download{display:inline-block;border:1px solid #b9ccdf;padding:4px 9px;border-radius:5px;margin:4px;text-decoration:none;font-size:13px}@media(max-width:1000px){aside{display:none}main{margin:0;padding:20px}h1{font-size:29px}.grid{grid-template-columns:1fr}section{padding:20px}}</style>
    <aside><strong>接口接点<br>从边缘到二维</strong><a href="#scope">01 · 结论与证据</a><a href="#act">02 · ACT 对照</a><a href="#gemm">03 · GEMM 对照</a><a href="#physics">04 · 接入层级与冲突</a><a href="#method">05 · 方法与验证</a><a href="#deliver">06 · 来源与交付</a></aside><main>
    <header><div class="eyebrow">LLMHARDWAREDESIGN · PHYSICAL DESIGN NOTEBOOK</div><h1>ACT / GEMM 的 pin<br>是否值得摆脱四边限制？</h1><p class="lead">真实边界坐标、贴边多排方案、内部二维混合方案。只改变接点 XY；保留信号功能、方向、网络、pin 金属层与连接意图。</p><p class="muted">2026-10-26 · Python 绘图 · 原报告内嵌数据 + 同一来源的 final ODB 只读导出 · 单文件 HTML 可离线查看</p></header>
    <section id="scope"><h2>01 · 先给判断，再看证据</h2>
    <div class="callout"><b>ACT 优先尝试 C 的“数据簇向内、控制口留边”；GEMM 优先选择 C 中有端点依据的活跃读接口簇，并让常量字节和窄控制口留边。B 保留为贴边多排的对照。</b><br>二维接点提供更大的局部接入区域，但不能仅靠改变点位消除通道需求。接点移入内部后，原层引出线、局部通孔与固定底座金属仍要容纳它们。</div>
    <p>ACT 的宏位置明确，宽输出接口与宏外通道、实际逻辑端点有空间关联。GEMM 无块内 SRAM 宏，但有大量逻辑与 filler；它的权重读数据共 2,048 位，其中 1,363 位集中在下边，单排接入值得疏解。外部存储对象的位置和目标层在本报告中并未取得，不能预先认定将这些输入全部深入计算阵列就能缩短块间连接。</p>
    <p><b>层级约束：</b>M1–M10 是设想的固定底座，M11/M12 是补充适配层；本次不把信号统一提升至 M11/M12。原来 M5→M8 的连接仍需 M5→M8。CSV 中未知目标层明确记 UNKNOWN，不把敏感性假设写成真实层级。原数据库的工艺层到 M10，未取得 M11/M12 的真实规则。</p>
    <div class="callout warn"><b>证据级别：</b>B/C 均为 proposed。已检查 pin 清单、边界、宏 bbox、已有 M5/M6 金属矩形、PDN 和假设通孔栈几何；尚未验证完整接入布线和 DRC。没有重硬化、P&R、RC 提取或时序验证，也不报告实际面积或时序收益。</div>
    </section>''']
    for case in ['act','gemm']:
        mm=metrics[case];meta=json.loads((ROOT/f'{case}.meta.json').read_text(encoding='utf-8'))
        data=pd.read_csv(ROOT/f'{case}_pin_coordinates.csv',keep_default_na=False);a=data[data.plan=='A'];known=endpoints[case]
        html.append(f'<section id="{case}"><h2>{"02" if case=="act" else "03"} · {TITLES[case]}</h2>')
        html.append(f'<div class="grid"><div class="metric"><b>{len(a):,}</b>信号 pin，{a.bus.nunique()} 个端口组</div><div class="metric"><b>{len(meta["macros"])} 个存储宏</b>{"合成 SRAM 研究模型，宏区域保守排除" if case=="act" else "tile buffer 为标准单元；外部 SRAM 不在块内"}</div><div class="metric"><b>{known["traced_known"]:,} 位有追踪端点</b>沿 BUF/INV 追踪，最多实际经过 {known["max_buffer_depth"]} 级</div></div>')
        html.append(image(f'{case}_comparison.png',f'{TITLES[case]}：A/B/C 的 block 尺寸、坐标尺度和配色完全一致；虚线框为放大窗口。矩形边界不是新增硬件区域。'))
        if case=='act':
            html.append('''<h3>ACT：哪些区域值得尝试</h3><p><b>B：</b>原边界内侧设置最多四排错位接点，纵深 1.12–4.48 μm，组内名义 pitch 1.12 μm；优先选择原总线束的主分布边。底部 SRAM 从 y=5.775 μm 开始，保留 0.56 μm 的候选宏避让量，所以该窄条可作为几何候选，而非已确认的接入走廊。保持四边拓扑便于比较，但底部一圈仍承受大部分引出压力。</p>
            <p><b>C：</b>优先让 r_data、r_scale、s_data 以及 w_data/we 字节对靠近已追踪端点，选择宏外的 x≈45–125 μm、x≈216–275 μm 纵向通道，以及宏上方区域；精确位置逐束见下表。底部和左部的宏实体均保守避开。中上部逻辑区可放写入接点，但必须与已有 M5/M6 布线及 PG 接入重新协调。r_data 与 r_scale 同属 ACT↔MXU，却未取得它们逐位的硬件 lane 对照，因此不人为按位绑定两条总线。</p>
            <p><b>保留边缘：</b>时钟、小控制/地址接口及缺少端点依据的位保留原坐标。w_data 的四个 8 位 lane 与 we[0:3] 由 RTL 循环确认对应；C 的其余数据束按连续 32 位分段，B 按同总线、同原边上的坐标近邻分段，仅用于摆放，不代表宏 bank。若 MXU 的实际位置更偏向某一侧，应把相关簇偏向该侧再评分；本次没有伪设 MXU 的顶层位置。</p>''')
        else:
            html.append('''<h3>GEMM：活跃接口选择性深入，常量字节留边</h3><p><b>B：</b>在原主边附近放入四排接点，组内名义 pitch 1.12 μm，非字节束按同总线、同原边上的坐标近邻分组，单束最多 32 位；宽权重接口不再强制沿同一条边线逐 bit 展开。gemm_wr_wdata 与 gemm_wr_wstrb 按 64 个 8+1 字节束保留关联；活跃字节尝试聚集，常量字节保持原位，全部位仍保留。该方案用于检验边界接入是否可用浅层重排缓解，不保证缩短引出线。</p>
            <p><b>C：</b>宽读数据、有效指令位及活跃写字节束在块覆盖内按实际追踪端点的中位位置选择接点簇，组内名义 pitch 2.24 μm。不是把无 SRAM 宏误当成无障碍区域：实际已有金属和 PG 的筛查单列在下方。clk/rst、状态、请求/握手等窄接口，以及 321 个无块内 ITerm 的 instr 位保留原坐标；活跃 instr 段可向接收逻辑移动，不据此更改指令语义。</p>
            <p><b>常量位例外：</b>原 RTL 对 gemm_wr_wdata[511:256] 和 gemm_wr_wstrb[63:32] 恒赋零。本次仍保留这 288 个真实 pin 及其原网络；它们的驱动端点原本分散，强制压成 32 个物理字节簇会增加很长的引出。B/C 因此保留原 XY，在字节清单和查询中继续保留数据/strobe 的逻辑关联；此例外有 RTL 和实际端点依据，不适用于活跃字节。</p>
            <p><b>适用条件：</b>若外部读数据本来通过原目标层覆盖这些区域，C 有机会减少从边缘折返的几何距离；若供数对象位于块旁边，内部簇也可能增加横向穿越距离。因此 GEMM 的 C 更适合选少数接收簇试做 ECO，而非直接把 2,048 位权重端口全部深埋。图中的连续位号束不声称是真实 SIMD lane、tile 或外部 SRAM bank。</p>''')
        html.append(image(f'{case}_zoom.png','局部放大叠加原数据库的实际 M5/M6 矩形及 M7 PG；三个局部窗口各自取景，坐标刻度明确。放大标记不代表 pin 或通孔尺寸。'))
        html.append(image(f'{case}_endpoints.png','叉号来自实际数据库的 ITerm，虚线仅是抽样的曼哈顿几何距离示意，不能作为新布线或原真实路径。'))
        html.append(interactive(case))
        html.append('<h3>清单与几何量化</h3>')
        html.append(table(['方案','信号位 / M5 / M6','移动 / 保留','距边界≤10 μm','同层最小 NN：M5 / M6 μm','20×20 μm 窗口采样峰值','候选束包络合计 μm²'],[
            [f'{p} · {PLAN[p]}',f'{m["n"]:,} / {m["layers"]["metal5"]:,} / {m["layers"]["metal6"]:,}',f'{m["moved"]:,} / {m["fixed"]:,}',number(m['within_10um_of_boundary']),f'{m["min_nn_per_layer_um"]["metal5"]:.3f} / {m["min_nn_per_layer_um"]["metal6"]:.3f}',f'{m["max_pin_count_20um_square_sampled"]} 点；{m["density_sampled_max_pins_per_um2"]:.4f} 点/μm²',number(m['sum_nonoverlap_patch_envelopes_um2']) if p!='A' else 'N/A（原始分散分布）'] for p,m in mm.items()]))
        html.append('<p class="muted">NN 为中心欧氏最近邻距离；C 的全局最小值可能由未移动边缘点决定。20 μm 窗以每个接点为四种角点取样，并非连续滑窗的严格最大值。包络为每束接点矩形的几何包络之和，包含原 pin 半宽 0.07 μm；不包含接入线、完整通孔栈、组间避让或预留通道，因此不是所需版图面积，更不是面积节省。</p>')
        access=[]
        for p,pp in patches[case].items():
            areas=[]
            for target in [6,8,10]:
                total=0
                for bundle in pp:
                    # Half of the isolated landing/cut width+basic-spacing envelope.
                    has_m5=any(a.iloc[i].layer=='metal5' for i in bundle['ids'])
                    half=(.15 if has_m5 else .14) if target==6 else (.42 if target==8 else .84)
                    bb=bundle['bbox_um'];delta=half-.07
                    total+=(bb[2]-bb[0]+2*delta)*(bb[3]-bb[1]+2*delta)
                areas.append(number(float(total)))
            access.append([p,*areas])
        html.append(table(['方案','假设到 M6：束包络合计 μm²','假设到 M8：束包络合计 μm²','假设到 M10：束包络合计 μm²'],access))
        html.append('<p class="muted">接入区域敏感性仅对移动束估算：使用该层级单 cut 栈各层 landing/cut“宽度 + 基本 spacing”的最大半径扩展每束包络，M5→M6 为 0.15 μm、原 M6 不升层为 0.14 μm、到 M8 为 0.42 μm、到 M10 为 0.84 μm。合计不是全局并集，可能有 halo 重叠；未计逃逸线、固定布线避让与保留边缘接点。若束内间隔已不足，单纯扩张束外包络不能修复冲突，应重排 pitch；完整所需接入区域仍需试布线。</p>')
        html.append(table(['方案','到最近追踪端点 L1 合计 μm','相对 A 几何变化','XY 移动 L1 合计 μm','pin 层直接重叠：全部 / PG','基本 spacing 筛查风险 pin'],[
            [p,number(m['nearest_traced_L1_sum_um']),f'{(m["nearest_traced_L1_sum_um"]/mm["A"]["nearest_traced_L1_sum_um"]-1)*100:+.1f}%',number(m['xy_movement_L1_sum_um']),f'{m.get("pin_overlap",0)} / {m.get("pin_pg_overlap",0)}',number(m.get('pin_spacing',0))] for p,m in mm.items()]))
        html.append(f'<p class="muted">距离只覆盖 {known["traced_known"]:,} 个有追踪端点的 pin（不含时钟）；一个 pin 多个端点时取最近者，属于局部距离代理，不能替代全扇出树线长。XY 移动量是从旧 pin 到新 pin 的坐标差，不是新增引出线长度。真实总线长、提取 RC、setup/hold 变化均未测量。</p>')
        sums=data.groupby(['interface','plan']).nearest_traced_endpoint_L1_um.apply(lambda v:pd.to_numeric(v,errors='coerce').sum())
        html.append(table(['功能类别','A 最近端点 L1 合计 μm','B 相对 A','C 相对 A'],[[LABELS[k],number(float(sums[k,'A'])),f'{(sums[k,"B"]/sums[k,"A"]-1)*100:+.1f}%' if sums[k,'A'] else 'N/A',f'{(sums[k,"C"]/sums[k,"A"]-1)*100:+.1f}%' if sums[k,'A'] else 'N/A'] for k in a.interface.unique()]))
        html.append('<div class="callout">局部点密度并未随 pitch 增加而必然降低：多排/二维小簇把原一维点线转成了二维点集。表中 20×20 μm 窗口的采样峰值可高于 A，因此仍需对每层的穿越容量、逃逸线和通孔做真实路由检查。局部 L1 的减少也不能直接转化为块间通道或面积减少。</div>')
        rows=[]
        for cat,g in a.groupby('interface',sort=False):
            rows.append([LABELS[cat],len(g),sum(g.layer=='metal5'),sum(g.layer=='metal6'),sum(g.direction=='INPUT'),sum(g.direction=='OUTPUT'),'/'.join(str(sum(g.original_edge==e)) for e in 'WESN')])
        html.append(table(['功能类别（A/B/C 完全一致）','位数','M5','M6','INPUT','OUTPUT','A：W / E / S / N'],rows))
        if case=='act':
            html.append('<details><summary>6 个存储宏的真实位置与方向</summary>')
            html.append(table(['实例','master','方向','bbox μm'],[[f'<code>{esc(m["name"])}</code>',m['master'],m['orientation'],', '.join(f'{v/2000:.3f}' for v in m['bbox_dbu'])] for m in meta['macros']]))
            html.append('</details>')
        html.append('<details><summary>B/C 每个候选束的接入区域、pitch 与位数</summary>')
        html.append(table(['方案','绘图束','位数','位置','中心矩形包络 μm','pitch μm','分组依据'],[
            [p,esc(s['group']),s['pin_count'],s['placement_region'],', '.join(f'{v:.3f}' for v in s['bbox_um']),s['pitch_um'],s['semantic']] for p,gg in patches[case].items() for s in gg]))
        html.append('</details><p>原有 M7 PG 访问矩形独立保留：ACT 为 21 个、GEMM 为 77 个，网络仍为 VDD/VSS；它们不计入信号 pin 位数，也不是完整 PDN。完整 PG 布线另从数据库导出参与筛查。</p></section>')
    html.append('''<section id="physics"><h2>04 · 原层接入、通孔与固定金属压力</h2>
    <p><b>衔接方式：</b>pin 仍放在原 M5/M6，沿原所属网络重新安排局部接入线；块内最终连接到同一组逻辑端点，对外继续连接同一对象和原目标层。原金属上的短接入段和经过层级的通孔位置可能改变。把 pin 改到某处不会自动生成可导通路径，也不能仅改 LEF 后继续使用旧 ODB、RC 或时序模型。</p>
    <p>目前没有取得父层的逐 pin “连接对象 + 目标金属层”映射。因此三种假设只用于分析敏感性：原 pin 层到 M6、M8、M10；不把它们写回 pin 层或网络。越高的目标层会经过更多已有金属与 cut，风险增加；不能拿最高层通孔规则统一否决所有 M5/M6 接点。</p>
    <h3>从本次实际 ODB 技术库读取的规则与 via master</h3>''')
    tech=pd.read_csv(ROOT/'physical/act/tech.tsv.gz',sep='\t')
    html.append(table(['层','默认线宽 / cut 宽 μm','基本 spacing μm','pitch X / Y μm','首选走向'],[[r.layer,f'{r.width/2000:g}',f'{r.spacing/2000:g}',f'{r.pitchx/2000:g} / {r.pitchy/2000:g}',r.direction] for _,r in tech.iterrows() if r.layer in ['metal5','via5','metal6','via6','metal7','via7','metal8','via8','metal9','via9','metal10']]))
    html.append('''<p>单 cut 假设栈使用数据库中的 <code>via5_0</code>、<code>via6_0</code> 等 master，各层 landing 矩形取实际 bbox。via5_0 的 M5/M6 landing 均为 0.14×0.14 μm；via6_0 的 M7 landing 为 0.40×0.40 μm；via7_0 的 M7/M8 landing 均为 0.40×0.40 μm；via8_0 的 M9 landing 与 via9_0 的 M9/M10 landing 为 0.80×0.80 μm。完整矩形列表见 physical/*/vias.tsv.gz。这里没有在图中用放大标记冒充上述尺寸。</p>
    <p>按单 cut、同心无横向错位堆叠、基本 spacing 的轴向保守筛查：M5→M6 的孤立栈中心间隔门槛约 0.30 μm；到 M8 约 0.84 μm；到 M10 约 1.68 μm。它们来自各经过层 landing/cut 的宽度加 spacing 的最大值，不是完整 DRC 的充分必要条件。B 名义 pitch 1.12 μm 支持低层/到 M8 的局部几何研究，却可能不足以逐点堆到 M10；C 的 2.24 μm 较宽松，但宏、PG、其他网络及保留边缘点仍可能造成冲突。端点下接到 M1 等内部线路未模拟新路径。</p>''')
    for case,mm in metrics.items():
        html.append(f'<h3>{TITLES[case]}：假设通孔栈的敏感性</h3>')
        html.append(table(['方案','假设目标','与既有几何冲突 / 基本 spacing 风险的 pin','完整候选清单中的风险 pin 对','涉及移动点的风险 pin 对'],[
            [p,target,number(m.get(key+'_risk_pins',0)),number(m.get(key+'_candidate_pairs',0)),number(m.get(key+'_involving_moved_pairs',0))]
            for p,m in mm.items() for key,target in [('toM6','M6'),('toM8','M8'),('toM10','M10')]]))
    html.append('''<div class="callout warn">这些数字表示需要避让或重排的几何风险，不是 foundry DRC 违例数。A 也按“在 pin 中心新增同心栈”假设筛查；原设计并不一定在那里使用该栈，所以不能把 A 的假设栈风险当成原设计 DRC 失败。原网络自己的已有形状从异网冲突统计中排除，但保留其连通性仍需后续检查。</div>
    <h3>收益与代价分开判断</h3>''')
    html.append(table(['候选','可能缓解的约束','增加或保留的压力'],[
        ['B 贴边多排','将每边的一维接点排布扩展为窄条；允许数据+使能局部成束；可缩短“占用边界投影”的展开长度。','每束新增纵深，外部线可能仍从同一侧进入；底座内部仍要把多排线接回端点。若块间仍只有侧边通道，通道需求未消失。'],
        ['ACT C 混合二维','利用宏外通道和端点邻近区域；可减少部分接口从边缘回折的局部几何距离。','SRAM 周围通道、已有 M5/M6、M7 PG 接入争用；若 MXU 位于反侧，外部距离增加。不能穿过宏 bbox 或假设宏上层无 OBS。'],
        ['GEMM C 选择性内部簇','把宽输入接点分散到接收逻辑附近；允许局部原层接入，避免只在下边解束。','大量固定底座信号、buffer 树和 PG 已占用资源；外部源位置未知，可能把块间通道压力转移到块覆盖内。相邻簇跨越时仍需绕线。']]))
    html.append('''<p>若固定底座已经制造完成，不能任意移动原 M1–M10 的走线或通孔。本次 XY 候选应理解为底座设计冻结之前的接口重构研究；即使冻结后允许补充连接，仍需利用原层真实可达的接入点，不能默认 M11/M12 能“穿过”被占用的下层。报告没有验证任何冻结后改造的实际可制造性。</p></section>
    <section id="method"><h2>05 · 方法、已检查项与限制</h2>
    <p><b>来源一致性：</b>HTML 中信号矩形逐 pin 对照本次同源 ODB 的 BTerm，名称、方向、层和四个矩形坐标全部一致；数量与原报告相符。源 ODB SHA-256 与 HTML 元数据一致，读取前后大小、修改时间与 inode 保持。源数据库由容器只读挂载，所有新脚本、日志、缓存和结果写在独立任务目录。</p>
    <p><b>端点：</b>直接 BTerm net 的 ITerm 逐一导出；沿 BUF_* / INV_* / CLKBUF_* 追踪最多 12 级，停止在非缓冲单元，保留其 ITerm 平均几何坐标和所在层。没有推断逻辑功能重排；无端点位不编造位置。ACT 85 位、GEMM 321 位无直接 ITerm（时钟另不作功能追踪）。C 只移动有已追踪端点的宽总线位和字节束。端点追踪不是全功能锥分析或形式证明。</p>
    <p><b>候选算法：</b>B 除实际字节对外，按同总线、同原边的坐标近邻分束，用原主边和坐标中位位置选择窄条；C 其余宽总线按连续位号分段，再按追踪端点中位位置选择覆盖内二维网格。常量输出字节原位保留。搜索避开宏 bbox + 0.56 μm 人工几何余量、已放束包络 + 0.56 μm，以及保留接点；对 12 个较近合法窗口用异网 pin 层基本间距风险加软代价。两种 0.56 μm 余量是设计假设，不是已验证工艺 halo。候选不是全局最优；矩形窗口和点坐标均保存，可复用脚本调整。</p>
    <p><b>金属筛查：</b>已有信号 wire/path 与通孔的逐层矩形、PG special-wire 矩形及通孔从 ODB 导出；筛查 M5/M6 pin 本体对异网几何直接相交，以及按本层默认 spacing 扩张后的相交。假设栈额外检查其经过的 routing/cut 层。宏区全部保守排除，不尝试从单元图判断其上方可布线。M4 也导出供后续使用；新内部引出线向更低层的完整接入未验证。全体单元/宏的 pin/OBS 形状未作为逐层障碍完整导出，因而该筛查不是数据库全部可布性检查。</p>''')
    html.append(table(['已检查','尚未检查'],[
        ['逐 pin 名称、bus、功能、方向、net、layer、矩形尺寸不变；无遗漏、重复、额外位。','对外连接对象与目标金属的父层映射；宏内部真实晶体管模型。'],
        ['真实边界内含完整 pin 矩形；无重复 XY；宏 bbox 无交叠；PG 访问形状独立保留。','全层 macro OBS 精细开放窗口、track snapping、EOL/PRL/宽线/天线/最小面积规则、cut array 和 enclosure 的全部条件。'],
        ['已布金属与 PG 的逐层异网矩形相交及基础 spacing 风险；按经过层假设栈分析。','新接入线连通、线宽及过孔冗余、原固定线保留率、新拥塞、宏 PG 资格、提取 RC、完整 STA 和 DRC。']]))
    html.append('<h3>自动完整性检查结果</h3>')
    html.append(table(['block','方案','信号位','漏项 / 多项 / 重复名','层 / net / 方向改变','越界矩形 / 宏 bbox 重叠','PG 矩形保留'],[
        [case,p,c['signal_count'],'0 / 0 / 0','0 / 0 / 0','0 / 0',c['pg_shapes_retained']] for case,cc in validation['cases'].items() for p,c in cc.items()]))
    html.append('''<p>检查通过只指清单与几何完整性通过，不能称为物理实现通过。原报告中的快照资格仍适用：ACT/GEMM 仅记录阶段工具预算通过，完整硬宏资格检查未完成。源实验和正在运行任务均未更改；本次只读导出作业 91824、91825 正常完成。</p></section>
    <section id="deliver"><h2>06 · 文件、来源与复用</h2><p>交付包括独立中文 HTML、六组 PNG/SVG（对照、局部、端点）、完整原始/候选逐 pin CSV、PG CSV、分束清单、结构化指标、验证结果及 Python/Tcl/服务器作业脚本。HTML 的主图和交互 pin 数据均内嵌；源文件下载链接指向同目录的交付包。</p>''')
    files=['all_pin_coordinates.csv','act_pin_coordinates.csv','gemm_pin_coordinates.csv','act_pg_coordinates.csv','gemm_pg_coordinates.csv','act_groups.csv','gemm_groups.csv','metrics.json','validation.json','proposed_patches.json','endpoint_coverage.json','tool_receipt.json','rtl_evidence.txt','parse_report.py','analyze_layout.py','build_report.py','export_odb.tcl','export_anchors.tcl','export.sh','anchors.sh','README.txt','manifest.json']
    html.append(''.join(f'<a class="download" href="{f}">{f}</a>' for f in files))
    html.append('<h3>实际输入与版本</h3><div class="scroll"><table class="wrap"><thead><tr><th>来源</th><th>实际位置 / 身份</th></tr></thead><tbody>')
    html.append(f'<tr><td>输入 HTML</td><td>{esc(extraction["source"])}<br>SHA-256 <code>{extraction["sha256"]}</code></td></tr>')
    for case in ['act','gemm']:
        meta=json.loads((ROOT/f'{case}.meta.json').read_text(encoding='utf-8'))
        html.append(f'<tr><td>{TITLES[case]} ODB</td><td>{esc(meta["spec"]["odb"])}<br>SHA-256 <code>{meta["source_odb_sha256"]}</code></td></tr>')
        html.append(f'<tr><td>{TITLES[case]} LEF 索引</td><td>{esc(source[case]["lef"])}<br>原报告记录 SHA-256 <code>{source[case]["sha256"]}</code>；本次坐标直接对照 ODB，而非再解析 LEF。</td></tr>')
    html.append('''<tr><td>工具</td><td>复用服务器 orfs-current-repacked.sif；OpenROAD 自报 unknown，单线程 Tcl 导出。实际 binary SHA-256 记录在 tool_receipt.json；不伪填 release 号。Python / numpy / pandas / scipy / matplotlib 版本见同文件。</td></tr>
    <tr><td>服务器独立任务目录</td><td>/public/home/yuzelu/PingyangHuang/pin-xy-candidates-20261026；仅此新目录写入。源 project-circuit 只读。首次内存请求、首次计算节点 PATH 尝试失败，记录保留；有效导出作业为 91824/91825。</td></tr>
    <tr><td>代码身份</td><td>源仓库本地 main 的 commit 见 tool_receipt.json。正式业务仓库只读，未提交代码、Issue、PR 或更新 Projects。此分析包为用户要求的本地独立交付；不把本地交付描述为在线验收。</td></tr></tbody></table></div>
    <h3>复现</h3><pre>python parse_report.py "输入报告.html" --out .
# physical/ 包含本次只读导出的压缩表；不需要重新访问服务器
python analyze_layout.py
# 输入：source_pin_data.json、*.meta.json、physical/{act,gemm}/*.tsv.gz
# 输出：CSV、PNG、SVG、metrics.json、validation.json、report.html
# 若要重做服务器导出，先读远程规则并换一个全新任务目录。
# export.sh / anchors.sh 中目录和输入路径需要按新任务修改。</pre>
    <p>独立输出目录不进入原 ref-project，也不改现有实验。新增成果的 SHA-256 清单见 manifest.json；当前包可供审阅，正式仓库登记、PR 和 Projects 状态未改变。</p>
    </section><footer class="muted">ACT / GEMM · 接点位置候选研究 · 几何完整性通过；完整物理验证未执行</footer></main>''')
    # Query data and filters: JS only controls existing Python-generated SVG nodes.
    rows={case:pd.read_csv(ROOT/f'{case}_pin_coordinates.csv',keep_default_na=False).to_dict('records') for case in ['act','gemm']}
    html.append('<script type="application/json" id="query-data">'+json.dumps(rows,ensure_ascii=False).replace('</','<\\/')+'</script>')
    html.append('''<script>
    const db=JSON.parse(document.getElementById('query-data').textContent),labels='''+json.dumps(LABELS,ensure_ascii=False)+''';
    const safe=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    document.querySelectorAll('.viewer').forEach(v=>{const c=v.dataset.case,plan=v.querySelector('.ip'),layer=v.querySelector('.il'),cat=v.querySelector('.ic'),q=v.querySelector('.iq');
      function filter(){const pp=plan.value,ll=layer.value,cc=cat.value,qq=q.value.trim().toLowerCase();
        v.querySelectorAll('.iview').forEach(n=>n.style.display=n.dataset.plan===pp?'block':'none');
        const names=new Set();v.querySelectorAll('.iview[data-plan="'+pp+'"] .pin').forEach(n=>{const d=n.dataset,ok=(!ll||d.layer===ll)&&(!cc||d.cat===cc)&&(!qq||[d.name,d.bus,d.group].join(' ').toLowerCase().includes(qq));n.style.opacity=ok?'1':'.035';if(ok)names.add(d.name)});
        const rr=db[c].filter(r=>r.plan===pp&&names.has(r.pin));v.querySelector('.itable').innerHTML=rr.slice(0,100).map(r=>'<tr>'+[r.pin,labels[r.interface],r.layer,r.direction,r.x_um.toFixed(6),r.y_um.toFixed(6),r.net].map(x=>'<td>'+safe(x)+'</td>').join('')+'</tr>').join('');
        v.querySelector('.icount').textContent=`共 ${rr.length} 位；表格最多显示前 100 行，搜索可精确定位。全部位见坐标 CSV。`;
      }[plan,layer,cat,q].forEach(n=>n.addEventListener('input',filter));filter();
      v.querySelectorAll('.pin').forEach(n=>n.addEventListener('click',()=>{v.querySelector('.ipick').textContent=n.querySelector('title').textContent}));
      v.querySelectorAll('svg').forEach(s=>{let start=null;const initial=[-20,-35,665,680];
        s.addEventListener('wheel',e=>{e.preventDefault();const b=s.viewBox.baseVal,p=s.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const m=p.matrixTransform(s.getScreenCTM().inverse()),f=e.deltaY>0?1.15:.87;if(b.width*f<2||b.width*f>2000)return;s.setAttribute('viewBox',[m.x+(b.x-m.x)*f,m.y+(b.y-m.y)*f,b.width*f,b.height*f].join(' '))},{passive:false});
        s.addEventListener('pointerdown',e=>{if(e.target.classList.contains('pin'))return;start=[e.clientX,e.clientY,...s.getAttribute('viewBox').split(' ').map(Number)];s.setPointerCapture(e.pointerId)});
        s.addEventListener('pointermove',e=>{if(!start)return;const b=s.getBoundingClientRect(),scale=Math.max(start[4]/b.width,start[5]/b.height);s.setAttribute('viewBox',[start[2]-(e.clientX-start[0])*scale,start[3]-(e.clientY-start[1])*scale,start[4],start[5]].join(' '))});
        s.addEventListener('pointerup',()=>start=null);s.addEventListener('dblclick',()=>s.setAttribute('viewBox',initial.join(' ')));
      });
    });</script></html>''')
    (ROOT/'report.html').write_text('\n'.join(html),encoding='utf-8')

if __name__=='__main__':build(json.loads((ROOT/'metrics.json').read_text(encoding='utf-8')),json.loads((ROOT/'proposed_patches.json').read_text(encoding='utf-8')),json.loads((ROOT/'endpoint_coverage.json').read_text(encoding='utf-8')))
