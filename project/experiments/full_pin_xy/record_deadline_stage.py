"""Add a brief current engineering notice without rewriting historical figures."""
from pathlib import Path
import datetime,json,os,subprocess
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/experiments/issue-126-full-pin'

def run():
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    note=f'''\n\n### R58 实际接线与父层失败收集（{now}）

原目标仍未全部完成。LL SYSTEM 新 c494 版本保留既有10261个真实内部接点，再修正2832个接入点；这些不是从A边界移动的数量。原13507位功能、方向、网络、M5/M6层和0.14μm尺寸保持；2827处旧pin占用以真实WIRE保留，原金属并集未减少。独立native报项0，725253网所检连通、双PG、RC提取、匹配13507位物理/时序模型与原负时序重放已执行。未重新搜索GRT/DRT，不把重用已布线路径写成新全流程完成。setup −3.909000ns、min −0.587515ns（含removal）、1091条slew和7784条cap实际失败保留。最差写许可输出bank_we[67]的BUF_X1实际420.387054fF，原限60.653706fF，负责把写许可送往设计外部存储接口。

共同父层93460闭合失败：六块布局/PG和256条FIXED M10导体已经生成，全局布线完成；详细布线在u_llaccel_aux/bit_1011（M5、dram_rsp_rdata[329]，局部340.015/1062.390μm）无合法接入点。它负责接收外部DRAM返回数据，像房间已经建好、门口仍进不去；当前c494版本此口未移动，不能假设换视图即修好。没有可冻结的完整底座、两功能或公平系统PPA结论。

93539从已闭合PG/固定导体检查点真实接续，升级当前LL视图、保持原父层端点/M10目标与几何，保守合并M1–M3障碍前先核对已有PG；运行结果待终态。剩余87点的修正via6预检93535找到74个附近候选、13个有界未找到；只是准备，真实重接未完成。原错误统一0.14帽假设已纠正：via6的M7帽实际0.4μm，pin仍0.14μm。

原64×64同步读/位掩码RTL实际映射17043单元、37608.676μm²，超过原宏5156.676μm²；这个具体映射不能塞回原框，不是所有SRAM实现不可能，也未虚构GDS替代。当前工程驱动来源`{source}`；源与产物SHA在阶段索引，历史回执不覆盖。39组PNG/SVG保留。

期限仍为北京时间2026-10-30 09:19。Refs #126 / Draft PR #129 / in_progress；登记management-hub PR5 pending；看板unverified、同步pending（缺已配置Projects入口与工具）；审查人/管理员待指定。
'''
    paths=['docs/experiments/issue-126-full-pin.md','progress/huangpingyang04-lgtm/STATUS.md','docs/handoffs/2026-10-29-issue-126-12h-delivery.md','docs/STATUS.md']
    for rel in paths:
        p=ROOT/rel;text=p.read_text(encoding='utf-8');assert '### R58 实际接线与父层失败收集' not in text
        prefix='\n\n' if rel!='docs/experiments/issue-126-full-pin.md' else '\n\n'
        split=text.find('\n');text=text[:split]+note+'\n'+text[split:]
        link=Path(os.path.relpath(OUT/'status.html',p.parent)).as_posix()
        text=text.replace('[唯一当前状态表](issue-126-full-pin/status.html)','[唯一当前状态表]('+link+')')
        p.write_text(text,encoding='utf-8',newline='\n')
    p=OUT/'report.html';text=p.read_text(encoding='utf-8');assert '<main>' in text
    card='''<section id="r58-current-stage" style="padding:18px;background:#fff4da;border-left:5px solid #ae741e"><h2>R58 当前实物与失败：先看本段，再查历史证据</h2><p>LL SYSTEM 已形成 c494 真实接线版本，13507位接口保持，累计13093处接入修正；独立native报项0、所检信号连通及双PG、寄生提取和匹配模型已执行。时序、电气仍失败：setup −3.909000ns，min −0.587515ns（含removal），1091条转换时间、7784条电容违规。不能把坐标或native0当完整资格。</p><p>共同父层93460已闭合：供电和全局布线完成，详细布线在 llaccel SYSTEM 的M5数据入口 bit_1011 / dram_rsp_rdata[329] 找不到合法入口。这个口负责接收外部存储返回的数据；像门的位置确定了，但进门线路尚未修通。当前LL版该pin未移动，正在真实诊断，不是假设换版本即可修复。共同底座未冻结、两套完整功能和公平系统对照仍未完成。</p><p><a href="status.html">唯一当前状态表</a> · <a href="data/deadline_engineering_receipts.json">当前源/实际阶段/SHA</a> · <a href="data/deadline_receipts/llsys-wire-pin-retention-r01/all_13507_actual_pin_correspondence.csv.gz">13507位实际坐标</a>。以下旧“最新”标题均是带版本的历史证据，不能覆盖本状态表；39组原图保留。</p></section>'''
    text=text.replace('<main>','<main>'+card,1);p.write_text(text,encoding='utf-8',newline='\n')
    print('CURRENT_NOTICE_RECORDED',now)
if __name__=='__main__':run()
