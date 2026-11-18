"""Render measured/assumed arithmetic energy separately with per-model exclusions."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
from xml.sax.saxutils import escape

HERE=Path(__file__).resolve().parent
MODELS=('qwen3','llama','granite','phi','gemma','qwen35','falcon')
NAMES=dict(qwen3='Qwen3-0.6B',llama='Llama-3.2-1B',granite='Granite',phi='Phi-4-mini',gemma='Gemma-3-4B',qwen35='Qwen3.5-4B',falcon='Falcon-H1-3B')
WINDOWS=dict(prefill='短 Prefill',first_token='首 Decode',decode='第 2 步 Decode')
LABELS=dict(rms_n='RMS N 核心',rms_scan='RMS 范围扫描',rms_apply_chunked='RMS 分块缩放（含 E32）',
 measured_softmax='Softmax 标定迁移',measured_rope='RoPE 标定迁移（含 E32）',
 arithmetic_idle_sensitivity='算术驻留敏感性',chunk_staging_sensitivity='分块搬运敏感性',
 proxy_scale='缩放代理',proxy_scaled_silu='SiLU 前缩放代理',proxy_silu='SiLU 已计入旧项（不重复）',
 proxy_expert_sum='专家加权和代理',proxy_router='专家路由代理',proxy_gelu='GELU 代理',proxy_sigmoid='Sigmoid 代理',
 proxy_conv4='四 tap 卷积代理',proxy_gdn_state='GDN 状态代理',proxy_mamba_state='Mamba 状态代理',
 proxy_recurrent_factors='循环因子/EXP/Softplus 代理',proxy_recurrent_norm_gate='循环归一化/门控代理')
def fmt(v):return '%.3f - %.3f'%(v[0],v[1])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('output/pdf/seven-model-energy-arithmetic-v3.pdf'));args=ap.parse_args()
    pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/Deng.ttf'));pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/Dengb.ttf'))
    rl_config.invariant=1
    style=ParagraphStyle('body',fontName='CN',fontSize=9.4,leading=13.5,spaceAfter=6,wordWrap='CJK')
    title=ParagraphStyle('title',parent=style,fontName='CNB',fontSize=22,leading=28,spaceAfter=14)
    heading=ParagraphStyle('head',parent=style,fontName='CNB',fontSize=13,leading=18,spaceAfter=9)
    tiny=ParagraphStyle('small',parent=style,fontSize=8,leading=10.7)
    story=[];records={m:json.loads((HERE/(m+'_tlm_power_v3_arithmetic.json')).read_bytes()) for m in MODELS}
    def p(text,kind=style):story.append(Paragraph(escape(text),kind))
    def table(rows,widths):
        cells=[[Paragraph(escape(str(v)),tiny) for v in row] for row in rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DAE9ED')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#BCCDD2')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,10)])
    p('七模型能耗评估',title);p('v3：算术分项标定 + 运算级近似',heading)
    p('2026-11-18 | Issue #280 / PR #281 | Melodydt')
    p('本版按用户确认的“完成能耗估算”口径补入算术项。已有 RTL 活动标定和特殊算子的运算级近似分开列示；不把近似项宣称为 RTL 数值验收。片上与片上 + DDR 分别报告。')
    p('固定条件：512-bit 系统 SRAM、三路 FFN、代表性 KV 历史、两步 Decode 与短 Prefill、名义 300 MHz。沿用冻结 TLM 时间及 DDR 结果；不加载布局布线寄生，不宣称时序闭合。')
    p('阅读顺序',heading)
    p('先看代表 Decode 窗口总表，再看方法及敏感性假设，最后看各模型三窗结果和新增分项。每个模型均列出未覆盖的物理项目和尚未 RTL 验证的代理项。')
    p('重要边界：表中范围是样本端点与人为设定的敏感性场景，既不是统计置信区间，也不是已证明的最坏误差界。“算术项已给出估计”不等于“完整芯片功耗已实测”。')
    story.append(PageBreak());p('代表性 Decode：两类能耗',title)
    rows=[['模型','原片上小计','新片上估算','新片上 + DDR']]
    for m,d in records.items():
        w=d['windows']['decode'];rows.append([NAMES[m],fmt(w['previous_on_chip']['energy_mj_per_token']),fmt(w['estimated_on_chip']['energy_mj_per_token']),fmt(w['estimated_on_chip_plus_ddr']['energy_mj_per_token'])])
    table(rows,[105,125,125,152]);p('单位：mJ / 输出 token。原片上小计为 v2 无布线寄生覆盖；新值增加算术动态项和显式敏感性项。模型规模、服务结构和估计覆盖不同，不能仅按表中值进行硬件效率排名。')
    p('短 Prefill 按输入 token 归一化；Decode 按输出 token 归一化。平均功率按对应冻结窗口能量 / 时间计算，尚未修正 RTL 与 TLM 调度差异。')
    story.append(PageBreak());p('评估方法与范围',title)
    p('1. 已有分项保留',heading);p('沿用 v2 的普通/FFN M、512-bit SRAM、PM、局控、母控、G32、U、写 DMA 等已覆盖项及 DDR 器件能耗。原 G32 SiLU 和 SRAM 事务不重复相加。读 DMA 仍沿用原单独敏感性口径，不混进默认小计。')
    p('2. 公共算术采用真实输入标定',heading);p('使用 Nangate45 typical 综合网表及 RTL 边界 VCD，计算等长窗口的 (Pactive - Pidle) × 时间。RMS 使用 N + scan + chunked apply；apply 和 RoPE 已包含其 E32，禁止再次加独立 E32。大向量保持完整 RMS 因子，仅将缩放拆为不超过 512 个字的合法命令。')
    p('3. 特殊算子为成本代理',heading);p('逐窗口/site/形状统计冻结 TLM 的真实调用数。将 GELU、路由、卷积、GDN/Mamba、EXP/Softplus/门控展开为标量乘、加/比较及非线性服务次数。参考成本来自实测 E32 S32 乘法和 U ADD2；浮点/不同实现的迁移系数人为设为 0.5 - 2 倍。')
    p('每个 EXP/tanh/softplus 组成服务假设 4 - 12 级乘加，倒数/平方根服务假设 4 - 16 级；Softplus 按 EXP 与 LOG 两个服务计。Router 比较/选择以 ADD2 代理。上述是假设成本，不是已经实现的函数算法或误差保证。')
    p('4. 共享资源与新增驻留',heading);p('空闲驻留低场景采用理想门控，高场景采用共同底座的 4 E32 + 4 RMS N + 4 scan + 4 apply 包装 + 1 RoPE 包装 + 1 softmax 模块开钟，分别只计一次。该实例配置是假设，尚非物理部署冻结。大向量 staging 从零额外复制至每字两次 128-bit 读加两次写作敏感性分析。')
    p('5. 数值与时序限制',heading);p('Falcon 卷积系数及 Mamba key/query 超出现有 R 的 S16 Q14 范围；GELU 与循环浮点服务也未完成匹配 RTL。这里仅估其能耗，不修改冻结模型数值。E32 连续无阻塞为 18 周期/包，TLM 叶节点为 9 周期；未将资源周期差直接加到整模型延迟。')
    for m,d in records.items():
        story.append(PageBreak());p(NAMES[m],title);p('三窗结果：包括代理项的条件估算',heading)
        rows=[['窗口','片上 mJ/token','片上 + DDR mJ/token','片上 + DDR 平均 W']]
        for name,w in d['windows'].items():rows.append([WINDOWS[name],fmt(w['estimated_on_chip']['energy_mj_per_token']),fmt(w['estimated_on_chip_plus_ddr']['energy_mj_per_token']),fmt(w['estimated_on_chip_plus_ddr']['average_power_w'])])
        table(rows,[90,135,145,137])
        p('第 2 步 Decode：新增算术分项',heading);w=d['windows']['decode'];rows=[['新增项','mJ / 输出 token','依据']]
        for k,v in w['arithmetic_components'].items():
            if v['energy_mj_per_token'][1]==0:continue
            basis='假设场景' if 'sensitivity' in k else '运算级代理' if k.startswith('proxy_') else '真实输入标定迁移'
            rows.append([LABELS[k],fmt(v['energy_mj_per_token']),basis])
        rows.append(['新增小计',fmt(w['arithmetic_increment']['energy_mj_per_token']),'非统计置信区间']);table(rows,[220,165,122])
        if w.get('read_dma_sensitivity'):
            s=w['read_dma_sensitivity']['same_write_cost']
            p('读 DMA 若取与写 DMA 相同的每拍动态成本：片上 '+fmt(s['estimated_on_chip']['energy_mj_per_token'])+'，片上 + DDR '+fmt(s['estimated_on_chip_plus_ddr']['energy_mj_per_token'])+' mJ/token。该项为独立代理场景，未混入上方默认小计；另保留 0.5/2 倍场景于 JSON。',tiny)
        p('覆盖小计下仍未覆盖：未匹配的控制外壳/分发与实际部署门控，全局时钟/跨块互连，读 DMA 静默/漏电，DDR PHY、封装与板级 I/O。布线寄生按本轮选择主动排除，缺项不代表零能耗。',tiny)
        proxies=[LABELS[k] for k,v in w['arithmetic_components'].items() if k.startswith('proxy_') and v['energy_mj_per_token'][1]>0]
        p('本模型尚未完成匹配 RTL 数值/功耗验收的新增项：'+('、'.join(proxies) if proxies else '无特殊函数代理；公共算术仍限于采样及条件迁移')+'。',tiny)
    story.append(PageBreak());p('复算、验证与后续',title)
    p('复算入口：work/Melodydt/280/seven_model_arithmetic_estimate.py；输入包括各模型冻结 v2 结果、已核验算子调用计数、真实输入标定回执。每个 v3 JSON 记录全部输入 SHA、每窗分项和运算计数。')
    p('验证必须检查：所有调用签名已处理；分块连续且覆盖完整原向量；没有重复 E32/G32/SRAM 项；分项之和等于新增小计；片上 + DDR 与两者之和一致；冻结时间、token 数和 DDR 完全不变；所有范围非负且有序。')
    p('后续提高准确性：用匹配的浮点/定点特殊算子综合网表及真实活动替代代理；实测共同底座的实例门控与访存；校准 9/18 周期差及并行重叠；取得读 DMA 综合后替代其近似；最后才讨论物理时序签核及布线后结果。')
    p('GitHub：rayggxia-workspace/LLMHardwareDesign，Issue #280，草稿 PR #281。报告是研究估算，审查/合并和完整物理验收另行记录。')
    for m in MODELS:p(NAMES[m]+' v3 JSON SHA-256: '+sha256((HERE/(m+'_tlm_power_v3_arithmetic.json')).read_bytes()).hexdigest(),tiny)
    def page(c,doc):
        c.setFont('CN',8);c.setFillColor(colors.HexColor('#526875'));c.drawString(44,25,'LLMHardwareDesign | v3 算术估算 | 2026-11-18');c.drawRightString(A4[0]-44,25,str(doc.page))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(args.output),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=45,bottomMargin=44,
        title='七模型能耗评估 v3：算术标定与运算级近似',author='Melodydt').build(story,onFirstPage=page,onLaterPages=page)
    print('ARITHMETIC_REPORT_WRITTEN',args.output)

if __name__=='__main__':main()
