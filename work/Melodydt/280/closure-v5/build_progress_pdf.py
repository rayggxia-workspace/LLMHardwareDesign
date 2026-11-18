"""Prepend qualified v5 progress to the preserved, clearly historical v4 report."""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path
import shutil
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
DOCS=ROOT/'docs/experiments'
NAMES={'qwen3':'Qwen3','llama':'Llama','granite':'Granite','phi':'Phi','gemma':'Gemma','qwen35':'Qwen3.5','falcon':'Falcon'}
def load(p):return json.loads(p.read_text())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def bounds(v):return '%.3f–%.3f'%tuple(v)

def main():
    current=DOCS/'seven-model-energy-evaluation.pdf'
    baseline=DOCS/'seven-model-energy-evaluation-v4.pdf'
    if not baseline.exists():
        assert len(PdfReader(current).pages)==25
        shutil.copyfile(current,baseline)
    assert len(PdfReader(baseline).pages)==25
    pdfmetrics.registerFont(TTFont('Deng','C:/Windows/Fonts/Deng.ttf'))
    pdfmetrics.registerFont(TTFont('DengB','C:/Windows/Fonts/Dengb.ttf'))
    style=ParagraphStyle('body',fontName='Deng',fontSize=10,leading=15,spaceAfter=8,wordWrap='CJK')
    title=ParagraphStyle('title',parent=style,fontName='DengB',fontSize=21,leading=28,spaceAfter=16)
    head=ParagraphStyle('head',parent=style,fontName='DengB',fontSize=14,leading=20,spaceAfter=10)
    small=ParagraphStyle('small',parent=style,fontSize=8.5,leading=12)
    def p(text,sty=style):return Paragraph(escape(text).replace('\n','<br/>'),sty)
    def table(rows,widths):
        cells=[[p(str(c),small) for c in row] for row in rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf6')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#61758b')),
            ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#c6d0db'))]))
        return t
    now=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M +08:00')
    story=[p('七模型能耗评估\n v5 校准进度补充',title),p(now,small),
        p('尚未完成用户指定前三项的全量验收',head),
        p('本补充报告列出已通过的新增证据与当前缺项。后附 25 页是原 v4 历史快照，原数字和文字完整保留；历史作业状态及缺项说明不代表当前状态。未通过的模型重测不填入新结果。'),
        p('固定口径：300 MHz，TLM 核心周期 3334 ps，512-bit 数据 SRAM，三 P 并行 FFN，短 prefill、代表性历史起点的两步 decode。M 时序闭合不作前置条件；本次不加载布线寄生。'),
        table([['工作项','本轮证据','尚未验收'],
            ['控制/母控外围','执行中 provider 路由、母控指令、PM 安装和资源区间；去重外围 25,880 单元、10.553–11.762 mW 参考。','每模型完整物理顶层、provider 适配、实际 router 参数、门控与完整 RTL 状态驻留。'],
            ['读 DMA','BSCC 已恢复；四份原综合网表 SHA、链接、结构检查及无寄生配对引脚标定通过。','模型物理拓扑绑定仍是条件；未观测内部活动为传播估计。'],
            ['特殊算子 / E32','四函数 50,693 条定点指令及 Conv4 捕获通道通过；E32 按 18 周期重跑实际调度。','特殊候选全模型接入、FP32 转换/复合运算及 GDN/Mamba 的本分支 300 MHz 校准。']], [80,220,211]),
        p('片上与片上＋DDR始终分开。未知分项不是零；候选定点样本通过不等于整模型 RTL 数值验收。范围是样本/场景端点，不是统计置信区间或保证误差界。',small),PageBreak(),
        p('已通过窗口：新时间与部分能耗账本',head),
        p('下表采用 E32 18 周期后的实际调度与 DDR 结果，加入母控外围参考。固定驻留按新时间积分；M 按新区间并集；计数项先核对 SRAM/PM/服务/DDR 等量再复用。此表尚未加入读 DMA 与新特殊候选。')]
    rows=[['模型 / 窗口','速度 tok/s','片上 mJ/token','片上＋DDR mJ/token']];numeric=[]
    for path in sorted((HERE/'timing-ledger').glob('*.json')):
        if path.stem=='index':continue
        d=load(path)
        for name,w in d['windows'].items():
            label=NAMES[d['model']]+' / '+{'prefill':'短 prefill','first_token':'首步','decode':'第二步'}[name]
            values=['%.3f'%w['tokens_per_second'],bounds(w['estimated_on_chip']['energy_mj_per_token']),bounds(w['estimated_on_chip_plus_ddr']['energy_mj_per_token'])]
            rows.append([label,*values]);numeric+=values
    story+=[table(rows,[142,85,142,142]),Spacer(1,12),
        p('七模型未出现的窗口仍等待成功验收。所有列出的重测保持输出数值文件一致；共享 E32/M 和同一 local target 未出现非法重叠。精确区间是 TLM 执行证据，不是完整 RTL 波形。'),
        p('共同未覆盖：读 DMA 的新积分、完整物理部署/门控/全局时钟互连、精确全模型控制 RTL 状态、特殊候选接口与 FP32 转换，以及 DDR PHY/封装/板级 I/O。布线寄生按本路线主动排除。',small),PageBreak(),
        p('特殊候选：数值与活动标注',head),
        p('现有工具按内部网名导入未覆盖所需引脚。修正流程重读确切结构网表，将观测位转换为实际单元引脚别名，保持事件时间不变；活跃与空闲窗使用同一引脚集合。匹配集合完全标注，仍有未观测内部网络需要传播估计。')]
    special=load(HERE/'special-pin-calibration.json');conv=load(HERE/'conv4-pin-calibration.json')
    rows=[['候选','动态增量 nJ/调用或通道','数值口径']]
    for name,r in special['primitives'].items():
        value='%.6f'%r['incremental_nj_per_call'];numeric.append(value)
        rows.append([name,value,'S40/Q24 插值；EXP [-16,+8]，其余主表 [-16,+16]'])
    for name,r in conv['cases'].items():
        value='%.6f'%r['incremental_nj_per_channel'];numeric.append(value)
        rows.append(['Conv4 '+name,value,'输入 Q16、系数 S32/Q24；样本差 '+str(r['max_abs_q16'])+' Q16 LSB'])
    story += [table(rows,[150,150,211]),Spacer(1,10),
        p('Conv4：44,258 / 247,897 个总连接引脚直接标注；特殊函数：5,724 / 140,975。其余内部活动为传播估计。上述系数不包含完整 provider、FP32 转换、递推历史存储或整模型误差。',small),
        p('原 Conv4 极低的边界系数及未完成 fence 的 DMA 空闲值已撤出新结果口径，保留日志用于诊断。GELU/up 乘法、归一化与递推复合运算仍需要独立接口绑定；侧边 200 MHz R 候选不能直接当作本分支 300 MHz 结果。',small),PageBreak(),
        p('读 DMA 场景与接续入口',head),
        p('四版 shared、shared-noshare、phase、phase-noshare 分别标定；phase 包含 shared，不能叠加总功耗。配对空闲须完成 reset fence、模式切换和 generation 核验，无请求/响应/故障后测量。')]
    cf=HERE/'dma-coefficients.json';coefs=load(cf) if cf.exists() else {}
    rows=[['已验收版本','空闲 W','动态 nJ/64B']]
    for name,c in coefs.items():
        values=[bounds(c['idle_w']),bounds(c['dynamic_nj_per_64b'])]
        rows.append([name,*values]);numeric+=values
    if len(rows)>1:story.append(table(rows,[171,170,170]))
    else:story.append(p('修正引脚后的四版系数尚在验收，不在此填入未通过的数字。'))
    story += [Spacer(1,10),p('已通过窗的 dma-ledger 提供每版单实例的片上与片上＋DDR场景。special-candidate-ledger 另行删除匹配的旧代理，加入候选动态、残余复合运算及每个已用站点一个开钟单元的假设驻留。0.5–2 倍迁移敏感性沿用旧假设，不是实测误差；候选执行周期尚未接入模型，不能据此发布新吞吐率。',small),
        p('后续顺序',head),
        p('1. 选择各模型匹配的 DMA 实例/owner，复用四版已完成系数；当前保留替代场景。\n2. 收齐七模型重测与 21 窗双口径账本。\n3. 补齐特殊候选的复合运算、ABI/provider 和 300 MHz 绑定。\n4. 完成真实物理控制部署与完整 RTL 状态证据。\n5. 更新报告、核验去重和数值，再交付审查。'),
        p('详细作业、源码 commit、SSH 目标、命令、输入输出 SHA 和当前缺项：docs/handoffs/2026-11-18-issue-280-closure-v5.md；实验目录 work/Melodydt/280/closure-v5。所有新 Slurm 任务 12 核、UNLIMITED，未配置聊天自动监测。'),
        p('Issue #280 in_progress；PR #281 草稿未合并，审查人待指定。登记 PR #5 pending；看板 unverified / 同步 pending。',small),
        PageBreak(),p('含读 DMA 的第二步 Decode 场景',head),
        p('下表以 E32 18 周期账本为基础，增加一个读 DMA fabric 的空闲与真实读量增量，保留此前的算术代理。各版互为替代，不相加；未选择唯一实际物理版本，因此不是已验收整芯片总功耗。')]
    rows=[['模型','单实例 DMA 版本','片上 mJ/token','片上＋DDR mJ/token']]
    for path in sorted((HERE/'dma-ledger').glob('*.json')):
        if path.stem=='index':continue
        d=load(path)
        if d['phase']!='decode':continue
        for variant,scenario in d['scenarios'].items():
            w=scenario['windows']['decode']
            values=[bounds(w['estimated_on_chip']['energy_mj_per_token']),bounds(w['estimated_on_chip_plus_ddr']['energy_mj_per_token'])]
            rows.append([NAMES[d['model']],variant,*values]);numeric+=values
    story+=[table(rows,[75,145,145,146]),Spacer(1,10),
        p('覆盖缺项：各模型完整物理部署、真实门控、完整控制 RTL 状态及 FP32/provider 接口；全局时钟、跨块互连、DDR PHY/封装/板级。Granite 路由/专家加权和等仍含复合算术代理；Qwen3/Llama 公共算术使用样本标定与条件驻留。phase 活跃样本仅 owner 0，其他 owner 的动态迁移未直接测量。',small),
        p('特殊候选替换结果单列在 special-candidate-ledger，未与本页混用。以下 25 页为 v4 历史报告，旧速度、作业状态和缺项不代表本轮最新状态。',small)]
    front=HERE/'v5-progress-front.pdf'
    def footer(canvas,doc):
        canvas.setFont('Deng',8);canvas.setFillColor(colors.HexColor('#526274'))
        canvas.drawString(42,26,'#280 / PR #281 · v5 校准进度，尚非完整验收')
        canvas.drawRightString(A4[0]-42,26,str(doc.page))
    SimpleDocTemplate(str(front),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    writer=PdfWriter();writer.append(front);writer.append(baseline)
    with current.open('wb') as f:writer.write(f)
    a,b=PdfReader(baseline),PdfReader(current);count=len(PdfReader(front).pages)
    assert 5<=count<=10,(count,'unexpected front page overflow')
    for i,page in enumerate(a.pages):assert page.extract_text()==b.pages[count+i].extract_text()
    text='\n'.join(x.extract_text() for x in b.pages[:count])
    assert all(v in text for v in numeric)
    receipt=dict(front_pages=count,history_pages=len(a.pages),total_pages=len(b.pages),
        preserved_history_text=True,numeric_strings_checked=len(numeric),
        baseline_sha256=digest(baseline),pdf_sha256=digest(current),visual_check='pending')
    (HERE/'pdf-progress-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
