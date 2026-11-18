"""Render the 200 MHz estimates and their measured evidence boundary."""
from pathlib import Path
import json,sys
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
pdfmetrics.registerFont(TTFont('Deng','C:/Windows/Fonts/Deng.ttf'))
pdfmetrics.registerFont(TTFont('DengBold','C:/Windows/Fonts/Dengb.ttf'))
pdfmetrics.registerFontFamily('Deng',normal='Deng',bold='DengBold')
styles={k:ParagraphStyle(k,fontName='DengBold' if k in ('title','head','warn') else 'Deng',fontSize=s,leading=l,spaceAfter=7,wordWrap='CJK',textColor=colors.HexColor('#172b40')) for k,s,l in [('title',22,30),('head',16,23),('body',10,15),('small',8,11),('cell',8.5,12),('warn',10,15)]}
def main():
    d=json.loads((ROOT/'results-200mhz.json').read_text(encoding='utf8'))
    rows=d['models'];story=[];width=A4[0]-32*mm
    def p(t,style='body'):story.append(Paragraph(escape(t).replace('\n','<br/>'),styles[style]))
    def page(t):
        if story:story.append(PageBreak())
        p(t,'head')
    def table(headers,data,weights=None):
        weights=weights or [1]*len(headers)
        cells=[[Paragraph(escape(str(c)).replace('\n','<br/>'),styles['cell']) for c in row] for row in [headers]+data]
        t=Table(cells,colWidths=[width*w/sum(weights) for w in weights],repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eff5')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#ccd5dd')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([t,Spacer(1,9)])
    p('七模型 200 MHz\n速度与功耗评估','title')
    p('固定 DDR 时钟的代表层抽查与分项能耗积分','head')
    p('2026-11-18  Asia/Shanghai  |  Melodydt  |  Issue 293 / PR 294','small')
    p('本报告沿用 300 MHz 论文数据的冻结配置，核心周期改为 5000 ps，DDR 周期保持 630 ps。成对运行代表完整层、入口和输出头，按原全层阶段时间重建速度；复用原网表与功耗标定，分离动态与漏电后重新积分。')
    p('结果是有代表层测量支撑的系统级估算。未执行七模型完整 200 MHz 回放，也未执行完整 512-token Prefill。功耗仅包含原报告已覆盖的电路和 DDR 器件，不能称为完整芯片功耗或物理签核。','warn')
    if len(rows)==7:
        speed=[r['speed']['decode_tok_s'] for r in rows]
        factors=[r['speed']['decode_tok_s']/r['baseline_300']['speed']['decode_tok_s'] for r in rows]
        p('七模型 Decode 估计吞吐为 {:.3f}-{:.3f} token/s，相当于原 300 MHz 的 {:.1f}%-{:.1f}%。固定 DDR 时钟使性能下降小于简单按 2/3 缩放的情景。'.format(min(speed),max(speed),100*min(factors),100*max(factors)))
    else:p('当前已完成 {}/7 模型，暂缺 {}。本文件为构建过程检查稿。'.format(len(rows),','.join(d['missing_models'])),'warn')
    p('平均功率下降不意味着每 token 能耗下降。固定电压与温度时，访问事件能量近似不变；运行时间增加使漏电、持续开钟和 DDR 后台能量重新累积。报告同时给出 W、J/token 与 token/J。')
    table(['项目','固定或改变的条件'],[['核心与核心耦合资源','3334 ps → 5000 ps；SRAM端口、PM、母控/局控、M流水和DMA发起节奏随核心变化'],['DDR','双通道 DRAMsim3，630 ps，不随核心降频；使用新发起时刻重新执行事务'],['计算部署','三路P并行FFN、512-bit SRAM、原PR272组合优化、真实512位置历史'],['标定基础','Nangate45 typical 标准单元；FreePDK45 SRAM宏 TT 1.1 V 25°C。原网表/标定复用，无新增综合或布线'],['仿真服务器','BSCC-T6；已核验节点为双路 Xeon Platinum 9242 @ 2.30 GHz，96物理核；单探针1核，Slurm不限时']], [1,3.4])
    page('速度结果与局部核验')
    table(['模型','短P2\ntoken/s','估计P512\ntoken/s','Decode\ntoken/s','局部偏差*\n%'],[[r['name']]+['{:.3f}'.format(r['speed'][k]) for k in ('short_prefill_input_tok_s','estimated_input_tok_s_to_logits','decode_tok_s')]+['{:.3f}'.format(r['speed']['representative_300_vs_original_max_percent'])] for r in rows],[2.3,1,1,1,1])
    p('* 局部偏差 = 300 MHz 抽查层时间相对原全层回放中对应层时间的最大绝对百分比。它检查截取代表层时 DDR/调度上下文变化的影响，不是完整 200 MHz 模型或 P512 预测的误差上界。','small')
    table(['模型','P2 对300MHz变化','P512 对300MHz变化','Decode 对300MHz变化'],[[r['name']]+['{:+.2f}%'.format(100*(r['speed'][k]/r['baseline_300']['speed'][k]-1)) for k in ('short_prefill_input_tok_s','estimated_input_tok_s_to_logits','decode_tok_s')] for r in rows],[2.1,1,1,1])
    p('短 Prefill 从空状态执行两个输入位置，计至第二位置末层完成；Decode 从真实 512 位置历史起跑，使用第二次与第一次 token 退休之间的窗口。P512 估计包含最后一次完整输出头，维持逐 token 原调度，不假设批处理或额外权重复用。')
    p('完整 200 MHz 与 P512 的实测误差百分比目前未知。下页所列既有注意力非线性筛查数值，也不能替代整序列误差。','warn')
    page('512-token Prefill 的条件估计')
    p('对每个抽样阶段测得 r = T200 / T300；各层按相同页结构类别中距离最近的代表层比率缩放原层时间。入口、启动、残差读和输出头分别使用成对抽查比率。三路P的重叠与同步已包含在完整层计时中，不相加三路累计忙时。')
    p('设 P1 为首个 Prefill 位置完成时间，L 为第二位置增量，H 为第二步 Decode 主体时间（可见KV=514，不含本步输出头），均先重建至200 MHz。\n斜率 b = (H - L) / 512\nT512 = P1 + 511 L + (510 × 511 / 2) b + 最后一次输出头时间\n吞吐 = 512 / T512。')
    table(['模型','估计P512总时长 s','既有ATT局部直线偏差 %','特别限制'],[[r['name'],'{:.4f}'.format(r['speed']['estimated_prefill_to_logits_s']),'{:.3f}'.format(r['speed']['inherited_attention_nonlinearity_percent']),'MoE路由条件估计' if r['model']=='granite' else '混合状态条件估计' if r['model'] in ('qwen35','falcon') else '未完整序列验证'] for r in rows],[2.1,1.2,1.3,1.8])
    p('醒目标注：对非线性、MoE路由或递推状态可能改变的模型，仍按用户要求保留线性估计。原300 MHz注意力采样的偏差百分比只作为风险筛查，200 MHz长序列误差没有被实测。不得将这些数字写成“误差小于X%”。','warn')
    p('代表层恢复原冻结残差，连续执行两个位置，并比较层输出及 Decode logits。跳过的层没有被执行；未重建中间长度的全模型数值轨迹。该方法用于频率敏感性估算，其覆盖范围与完整端到端仿真不同。')
    for phase,title in [('prefill','短 Prefill 的功率与能耗'),('decode','Decode 的功率与能耗')]:
        page(title)
        p('Prefill 能耗对应两输入 token 的短窗口，不对应速度表中的512-token估计窗口。' if phase=='prefill' else 'Decode 能耗对应第二次与第一次退休之间的一个输出 token。','warn' if phase=='prefill' else 'body')
        dat=[]
        for r in rows:
            for scope,label in [('on_chip','片上已覆盖'),('on_chip_plus_ddr','片上＋DDR')]:
                e=r['windows'][phase]['scopes'][scope]
                dat.append([r['name'],label]+['{:.4f}-{:.4f}'.format(*e[k]) for k in ('average_power_w','energy_j_per_token','tokens_per_joule')])
        table(['模型','口径','平均功率 W','能耗 J/token','能效 token/J'],dat,[2.1,1.25,1.45,1.45,1.45])
        p('范围为原标定样本端点重新积分后的区间，不是误差置信区间，也不涵盖未标定硬件。论文合并表采用低能耗端点；token/J低端对应高能耗端点。','small')
        p('三项单位按同一窗口换算：W = 窗口能量 / 时间；J/token = 窗口能量 / token数；token/J = token数 / 窗口能量。')
    page('标定复用与能量重新积分')
    p('复用原综合网表、单元库及分模块活动标定，未运行新的逻辑综合或布局布线。原标定从 RTL/门级或边界活动取得开关率，并通过映射电路与工艺库估算单元内部、切换及漏电功率。本轮代表层是 TLM 活动抽查，不是新增200 MHz门级功耗实测。')
    table(['分项','200 MHz处理'],[['开钟驻留','P200 = (P300 - Pleak) × 2/3 + Pleak，再乘重建后的整窗时间；保持原实例数。'],['M忙时增量','用抽查层的M忙时变化及2/3动态功率系数修正原增量；保留旧M标定迁移限制。'],['SRAM/PM/算术/写回事件增量','核对成对样本事务与SRAM计数一致，固定电压下复用每事件能量；计数按原全层窗口。'],['DDR器件','根据成对抽查的原层时长权重，分别计算访问命令能量、后台加刷新能量的变化系数，作用于原全窗DDR分项。DDR命令合并/行状态允许随发起节奏变化。'],['缺失模块','不填零、不混入读DMA写价代理；维持冻结300MHz报告的覆盖范围。']], [1.1,3.8])
    p('片上小计含3个M、4个S_P、局控PM与取指参考、母控PM、九目标母控核心、G32、写侧/U/PM桥等既有分项。具体部署和门控仍属参考假设，未逐模型完成物理实例验收。')
    p('缺项包括读DMA实测、未标定特殊算术、控制外壳与其余控制活动、全局时钟和未覆盖互连、DDR PHY及板级能耗。无布线寄生；原综合网表已有缓冲与管脚电容保留。旧M在300MHz未闭合时序，降频不等于200MHz已通过STA。','warn')
    p('模型能耗差异主要受执行时长、访问量和已覆盖模块活动影响。共享网表与标定可跨模型复用，但不同算子、部署或门控变化仍需补充标定，不能据此宣称七个完整芯片设计已签核。')
    page('逐模型优化与验收证据')
    old=json.loads((ROOT.parent/'291/seven-model-speed-results.json').read_text(encoding='utf8'))['models']
    table(['模型','沿用的模型特征与优化','代表层'],[[r['name'],old[r['model']]['architecture'],', '.join(map(str,r['selected_layers']))] for r in rows],[1.7,3.4,1])
    p('本轮只改变核心时钟，未新增算子或调度优化。共同配置沿用三路P FFN、512-bit SRAM和PR272组合优化；模型专用的KV、上下文缓存、低位残差、MoE和混合递推服务按各自冻结代码保持。')
    p('已通过的数值层检查数：{}（包含两频率、两阶段、两个位置）。每项样本还核对输出头logits、DMA排空、SRAM计数和逻辑读写完成数。完整长Prefill验证继续暂缓。'.format(sum(r['numerical_layer_checks'] for r in rows)))
    p('实际源版本与工件入口')
    p('冻结300 MHz论文数据：PR292 / 5464d2794833f5e83afda875e0c264b7a43f3ea3。当前任务：PR294，独立目录 work/Melodydt/293。源码、输入与输出散列见 manifest.json、accepted-manifest.json 和各 samples.json。','small')
    p('远程：~/LLMHardware/zenanyan/issue-293-200mhz-01。首批38832271中的Llama/Phi/Granite单项成功，作业整体因其他模型失败；Qwen3使用38832316；Gemma/Qwen3.5/Falcon使用后续已通过补跑。失败作业及日志保留，不作为测量结果。','small')
    p('早期作业的驱动文件在进程加载后曾更新，因此结尾采集的驱动文件SHA可能对应新版；实际加载版本以作业开始时保存的source-commit和提交源码为准。后续作业改为每次保存独立脚本副本。库和模型源文件保持只读。','small')
    p('后续若要提高可信度：完整200MHz P2/两步Decode回放；16/32-token及完整P512独立验证；补齐读DMA与特殊算术等缺项；按实际部署/门控重算；200MHz完整STA与物理功耗校准。当前报告完成与PR审查/合并、项目登记、看板同步分别记录。','small')
    out=REPO/'output/pdf/seven-model-200mhz-evaluation.pdf';out.parent.mkdir(exist_ok=True,parents=True)
    def footer(c,doc):
        c.setFont('Deng',8);c.setFillColor(colors.HexColor('#607080'));c.drawString(16*mm,12*mm,'200 MHz 系统级估算 | Issue 293');c.drawRightString(A4[0]-16*mm,12*mm,str(doc.page))
    SimpleDocTemplate(str(out),pagesize=A4,leftMargin=16*mm,rightMargin=16*mm,topMargin=16*mm,bottomMargin=20*mm,title='七模型200MHz速度与功耗评估').build(story,onFirstPage=footer,onLaterPages=footer)
    print(out)
if __name__=='__main__':main()
