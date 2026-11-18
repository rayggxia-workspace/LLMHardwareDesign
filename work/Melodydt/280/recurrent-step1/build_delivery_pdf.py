"""Build the first recurrent-state calibration delivery from measured receipts."""
from pathlib import Path
import json
from hashlib import sha256
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader, PdfWriter

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'output/pdf/seven-model-sync/2026-11-18-r4'
OUT.mkdir(exist_ok=True,parents=True)
for n,f in [('text','Deng.ttf'),('bold','Dengb.ttf')]:
    pdfmetrics.registerFont(TTFont(n,str(Path('C:/Windows/Fonts')/f)))
result=json.loads((HERE/'candidate-rollup.json').read_bytes())
audit=json.loads((HERE/'rollup-check.json').read_bytes())
pdf=OUT/'recurrent-state-first-round.pdf'
c=Canvas(str(pdf),pagesize=A4,invariant=1)
c.setTitle('GDN 与 Mamba 第一轮状态更新标定')
page_id=0
expected=[]
def text(x,y,s,size=11,bold=False,right=False):
    c.setFillColor(HexColor('#193744'))
    c.setFont('bold' if bold else 'text',size)
    (c.drawRightString if right else c.drawString)(x,y,s)
def page(title,subtitle):
    global page_id
    page_id+=1
    text(36,793,'LLMHardwareDesign  /  状态更新能耗标定',12,True)
    text(558,793,'2026-11-18  ·  第一轮',10,right=True)
    text(36,747,title,23,True)
    text(36,714,subtitle,10.5)
    text(36,32,'200 MHz · 512-bit 系统 SRAM · 综合网表活动 · 无布线寄生',9)
    text(558,32,str(page_id),10,right=True)
def table(y,head,rows,widths):
    for i,row in enumerate([head]+rows):
        c.setFillColor(HexColor('#DCEBE7' if i==0 else '#F3F7F6'))
        c.rect(36,y-24,523,29,fill=1,stroke=0)
        x=36
        for j,(s,w) in enumerate(zip(row,widths)):
            font='bold' if i==0 else 'text'
            size=10
            assert pdfmetrics.stringWidth(s,font,size)<w-8,s
            text(x+5 if j==0 else x+w-5,y-13,s,size,i==0,j!=0)
            x+=w
            if i: expected.append(s)
        y-=29
    return y-24
def notes(y,title,lines):
    text(36,y,title,13,True)
    for line in lines:
        y-=21
        assert pdfmetrics.stringWidth(line,'text',10.5)<523,line
        text(36,y,line,10.5)
    return y-34
def span(xs,decimals):
    return '-'.join(f'{x:.{decimals}f}' for x in sorted(xs))
page('真实捕获与连续状态验证','差异以 Q16 最低位计，1 LSB = 1/65536。RTL 同时对自己的定点参考逐字核验。')
text(36,692,'本次同步：前五页为候选标定；合订版附录保留七模型 v3，默认数值未改。',10)
rows=[]
for tag,label in [('qwen35','Qwen3.5 原格式'),('falcon','Falcon S16/Q11'),('falcon-wide','Falcon S32/Q24'),
                  ('qwen35-stress32','Qwen3.5 32 步'),('falcon-wide-stress32','Falcon 宽系数 32 步')]:
    d=json.loads((HERE/(tag+'-receipt.json')).read_bytes())
    rows.append([label]+[str(max(x[k]['max_lsb'] for x in d['vs_frozen_tlm_q16'])) for k in ['output','state']])
y=table(672,['候选与工况','输出最大差 / LSB','状态最大差 / LSB'],rows,[241,141,141])
y=notes(y,'测试内容',[
    '每模型六个真实捕获的 16 通道块，覆盖短 Prefill、首步与第二步 Decode。',
    '每块拆为两批八路，通过 LOAD、EXEC、READ_OUT、COMMIT、READ_STATE 接口。',
    '两步 Decode 保留已提交的 RTL 状态，验证真实后继输入的参考状态衔接。'])
y=notes(y,'连续压力测试范围',[
    '32 步交替使用两份捕获的系数与输入。浮点参考与候选分别反馈 Q16 状态。',
    '完整模型的后继输入、独立层样本和最终 token 精度仍待验证。'])
notes(y,'Falcon 的剩余精度来源',[
    '宽系数解决样本系数范围与部分量化误差。单次诊断中，改用精确注入后状态最大差由',
    '12 降至 4 LSB；将状态更新合并为一次舍入后降至 1 LSB。后者输出仍相差最多 30 LSB。',
    '诊断替换尚缺对应 RTL，默认候选功耗继续绑定本轮实际通过的电路版本。'])
c.showPage()

page('200 MHz 门级活动标定','每个 16 通道服务由两批八路归并，计完整装载、执行、输出和状态读回。')
rows=[]
for m in result['models']:
    for phase,label in [('prefill','短 P2'),('decode','Decode')]:
        w=m['windows'][phase]
        rows.append([m['name']+' '+label,span(w['increment_nj_per_16channel_block'],2),
                     span(w['shared_r_idle_w'],4),str(w['calls']),f"{w['one_r_active_time_s']/w['window_s']:.1%}"])
y=table(672,['模型与窗口','增量 nJ/服务','静默 W/R','调用数','R 忙占比'],rows,[178,114,91,70,70])
y=notes(y,'功耗计算',[
    '对每个捕获块配对等长活跃与静默窗口，使用映射后门级活动计算差额。',
    '每 16 通道服务：Qwen3.5 为 10.80 µs，Falcon 为 24.56 µs，包含测试读回。',
    '每窗总能量 = 服务调用数 × 单服务增量 + 一个共享 R 的整窗静默能量。',
    '电压与温度沿用 Nangate45 typical。每批所有输出与状态均通过门级数值对照。',
    '完整波形原生含单元引脚名，逐项对连接图核验；逐窗标注数与全部已连接引脚数相等。',
    '零延迟门级活动未计门延迟导致的毛刺；本轮没有 SDF 或物理时序签核。'])
y=notes(y,'样本与实例假设',[
    '每个窗口的服务端点来自两个捕获块，保留两批八路能量之和。部署场景采用一个共享 R。',
    '已检查累计活跃时间落在冻结窗口预算内；实际并行实例、接口连接与调度仍需集成验证。',
    'R 内部双状态 bank 映射为标准单元触发器；系统数据 SRAM 仍为 512-bit。',
    '尚未冻结七模型共用的芯片配置；统一部署时须同时核对其他模型的 R 驻留成本。',
    '已捕获的 Prefill 状态全零，仅支持冷状态外推；Decode 样本具有真实历史状态。'])
notes(y,'能量归属',[
    'Falcon 的 delta×value 注入由驱动生成，其生成能量继续保留 E32 标量代理。',
    '外部格式转换和集成互连仍缺标定。芯片其他算术、SRAM 与 DDR 沿用 v3 已覆盖分项。'])
c.showPage()

page('候选实现的片上能耗','替换状态更新代理并计入一个共享 R 的驻留。此页只含片上已覆盖小计。')
rows=[]
for m in result['models']:
    for phase,label in [('prefill','短 P2'),('decode','Decode')]:
        w=m['windows'][phase]
        rows.append([m['name']+' '+label,span(w['baseline']['on_chip']['mean_w'],3),
                     span(w['candidate']['on_chip']['mean_w'],3),
                     span(w['candidate']['on_chip']['mj_per_token'],1)])
y=table(672,['模型与窗口','原 v3 / W','候选情景 / W','候选 mJ/token'],rows,[190,101,106,126])
y=notes(y,'对比基线与单位',[
    '对比基线为 2026-11-18 R3 的 200 MHz 算术补项 v3；只替换两个模型的状态更新分项。',
    '未将主会话后续 v4/v5 混入本次对照。其余五模型、原速度、DDR 分项保持基线值。',
    '每个短 Prefill 窗口计两个输入 token；Decode 为原第二步代表窗口。',
    'Prefill 候选列为冷状态样本外推，尚缺非零状态阶段，不能作为完整 Prefill 功耗界。'])
notes(y,'尚未覆盖与验收',[
    '保留 v3 的读 DMA 实测、控制外壳、全局时钟及实际门控、集成互连等缺项。',
    'DDR PHY 与板级 I/O 未覆盖；本次没有布局布线寄生或新增物理时序签核。',
    '单 R 的总活跃时间可容纳只是一项必要条件，不能证明整模型实际调度已实现。'])
c.showPage()

page('候选实现的片上＋DDR 能耗','同一候选片上小计加原 DDR 芯片估算，保留原 DDR 的活动和时间口径。')
rows=[]
for m in result['models']:
    for phase,label in [('prefill','短 P2'),('decode','Decode')]:
        w=m['windows'][phase]
        rows.append([m['name']+' '+label,span(w['baseline']['on_chip_plus_ddr']['mean_w'],3),
                     span(w['candidate']['on_chip_plus_ddr']['mean_w'],3),
                     span(w['candidate']['on_chip_plus_ddr']['mj_per_token'],1)])
y=table(672,['模型与窗口','原 v3 / W','候选情景 / W','候选 mJ/token'],rows,[190,101,106,126])
y=notes(y,'本轮完善了什么',[
    'GDN 与 Mamba 状态更新已有具体候选电路、真实样本数值回放和门级活动能耗依据。',
    '模型积分显式计入 R 内部状态存储和控制驻留，并保留 Falcon 注入生成的代理成本。'])
for item in audit['checks']:
    if item['phase']=='decode':
        text(36,y+12,f"{item['model']} Decode 区间宽度：{item['old_width_w']:.4f} → {item['candidate_width_w']:.4f} W，缩小 {item['width_reduction']:.1%}。",10.5)
        y-=21
y-=8
y=notes(y,'候选情景的边界',[
    '候选采用定点逐阶段舍入，冻结 TLM 使用浮点状态计算。已有差异仍待模型级精度验收。',
    '采样端点描述当前输入的活动差异，不能作为全部模型输入的概率置信区间或保证误差界。',
    'Prefill 为全零初态样本外推，后续非零状态活动尚未采样；Decode 带真实历史状态。',
    '正式七模型默认结果需在精度、部署与调度合同确认后更新。'])
notes(y,'后续工作',[
    '增加独立层与真实更长序列，验证精度累积；实现并校准 Falcon 注入及格式转换。',
    '确认共享 R 的实际加载路径、实例数、门控和跨块传输，然后重新绑定模型窗口。'])
c.showPage()
page('版本、作业与复现','同一结果包保存真实捕获、固定 RTL、命令向量、配对功耗回执及独立积分检查。')
rows=[]
for m,key in [('Qwen3.5-4B','qwen35'),('Falcon-H1-3B','falcon-wide')]:
    collected=json.loads((HERE/'results'/key/'collection.json').read_bytes())
    cal=json.loads((HERE/(key+'-calibration.json')).read_bytes())
    rows.append([m,collected['jobs']['job'],collected['jobs']['power_job'],f"{cal['source']['cell_count']:,}"])
y=table(672,['模型','综合作业','门级功耗作业','映射单元数'],rows,[185,96,116,126])
y=notes(y,'来源和版本',[
    '关联 Issue #280 / PR #281。固定基础 R 来源 commit：',
    'f034be2b7c87137b92f7bfce274a5485647e512d。Falcon 候选变更和完整 SHA 在结果包内。',
    '比较基线：2026-11-18 R3 / 200 MHz 算术补项 v3。后续 v4/v5 未混入本轮对照。'])
y=notes(y,'服务器与工具',[
    '服务器 yuzelu@10.129.166.172；成果位于本人 issue-280 的 recurrent-round1-20261118 目录。',
    'Yosys 0.68+post、Verilator 5.042、Clang 14、Python 3.10.12、Nangate45 typical。',
    'OpenROAD 版本字符串返回 unknown，以实际可执行文件和容器 SHA 固定版本。'])
text(36,y+10,'功耗兼容视图仅移除 160 处 signed 声明；位宽、单元、连接和赋值保持一致。',9.5)
y-=15
text(36,y+10,'120422 逐位连接图审计通过：原始网表与兼容视图的所有单元、端口和网络完全对应。',9.5)
y-=15
y=notes(y,'数据核验和复算',[
    'work/Melodydt/280/recurrent-step1/ 内的 DELIVERY.md 给出作业、路径与全部接续步骤。',
    'candidate-rollup.json 保存双口径积分；calibration.json 保存门级分窗功耗和工具散列。',
    'rollup_candidate.py 复算，verify_candidate.py 独立核验；原始大网表与 VCD 保留在服务器。',
    '结果包内附文件 SHA 清单，解压到空目录后即可执行模型积分复算。'])
notes(y,'交付状态',[
    '这是候选硬件的第一轮实验交付，完整模型数值精度、实际集成部署和物理时序尚未验收。',
    '用户已明确授权本轮公开上传；提交和 PR 回执见 publication.json，审查与合并另计。',
    '项目保持 in_progress；独立审查待安排，线上提交与本地技术交付分别记录。'])
c.linkURL('https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280',(36,536,280,553),relative=0)
c.save()
extracted='\n'.join(p.extract_text() for p in PdfReader(pdf).pages)
assert all(v in extracted for v in expected)
(OUT/'receipt.json').write_text(json.dumps(dict(pdf_sha256=sha256(pdf.read_bytes()).hexdigest(),
    model_data_sha256=sha256((HERE/'candidate-rollup.json').read_bytes()).hexdigest(),pages=5),indent=2)+'\n')
previous=ROOT/'output/pdf/seven-model-sync/2026-11-18-r3'
prior_receipt=json.loads((previous/'sync-receipt.json').read_bytes())
assert sha256((previous/'200mhz-power.pdf').read_bytes()).hexdigest()==prior_receipt['output_sha256']['200mhz-power.pdf']
assert sha256((HERE/'baseline-200mhz-v3.json').read_bytes()).hexdigest()==prior_receipt['output_sha256']['200mhz-power-v3.json']
combined=OUT/'200mhz-power.pdf'
writer=PdfWriter()
writer.append(pdf,outline_item='R4: recurrent-state candidate calibration')
writer.append(previous/'200mhz-power.pdf',outline_item='Frozen R3: seven-model 200 MHz arithmetic v3 baseline')
writer.add_metadata({'/Title':'200 MHz seven-model power: frozen v3 plus recurrent-state candidate calibration'})
with combined.open('wb') as f:writer.write(f)
assert len(PdfReader(combined).pages)==9
(OUT/'combined-receipt.json').write_text(json.dumps(dict(pages=9,
    combined_pdf_sha256=sha256(combined.read_bytes()).hexdigest(),
    candidate_pdf_sha256=sha256(pdf.read_bytes()).hexdigest(),
    frozen_v3_pdf_sha256=prior_receipt['output_sha256']['200mhz-power.pdf'],
    default_seven_model_numbers_changed=False),indent=2)+'\n')
print(pdf)
print(combined)
