"""Brief current notice while CAD continues; retain every historical result."""
from pathlib import Path
import datetime
ROOT=Path(__file__).resolve().parents[3]
def run():
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    note=f'''\n\n### R59 实际全口引出与公平资源核对（{now}）

原完整目标仍未完成，按目前证据预计12小时内不能全部验收通过；北京时间2026-10-30 09:19硬截止不延长。LL新试验93561已经实际编辑9517个接点并补M5/M6短线或在真实同网金属上重定位，13507位完整清单保留；24个原生单端口/无块内端点/无原布线的声明口保持原XY，没有编造其RTL常量或unused语义。实际编辑及双PG执行完成，独立native DRC/全口AP/RC-STA尚待终态，不替换唯一状态表当前c494合格范围有限的源。完整原生逐pin快照正在无损归档。

全13507首级接入筛查4937点几何清、8570点有风险、6796不在所测第一跳交叉轨道；不是8570个native失败，也不是完整接入栈验证。父层bit_1011的真实M6异网net257248直接挡在M5接点上方；75点实际重接和7438驱动换型试验均在未选中的bit_3598无AP失败，故转为全口工程，未删除失败检查。共同检查点经DEF重新导入后，逐bit图、原供电/端口/实例及256 FIXED保持；未完成详细布线，不能冻结。

VECTOR75个驱动换型的新试验完整布线/RCX/STA及独立native0已执行，但供电实际失败，未晋升。已定位9个单元的合法化朝向在重放时遗漏；第一次局部翻转又把OpenDB包围框偏移一排1.4μm，现按真实合法坐标与朝向一起恢复。布局和VSS通过，余下VDD与clknet_leaf_167_clk/172_clk旧时钟线短接，93571已按真实受影响网络重新接线；继续查双PG/fresh/RC/STA，不用native0代替供电。openTPU SYSTEM1149换型试验在bit_22553无AP失败，保留源与证据。

已核对ACT/MXU/LL的旧Aopt与当前C：原生全cells/连接/位置、PG、die、SDC四组SHA一致，可复用这三块叶结果，不能冒充系统对照。GEMM/VECTOR/openTPU SYSTEM三块已启动使用当前C同单元/同位置/同约束的优化周边真实重布线93572/93573/93574，不混用旧ECO资源。共同底座、两个完整功能、冻结哈希与公平完整系统PPA仍未完成。39组PNG/SVG保留。

Refs #126 / Draft PR #129 / in_progress。登记PR5 pending；看板unverified/同步pending，缺Projects配置/能力，管理员与审查人待指定。唯一当前状态表及阶段SHA索引为恢复入口，持续执行而非暂停。\n'''
    for rel in ['docs/experiments/issue-126-full-pin.md','progress/huangpingyang04-lgtm/STATUS.md','docs/handoffs/2026-10-29-issue-126-12h-delivery.md','docs/STATUS.md']:
        p=ROOT/rel;text=p.read_text(encoding='utf-8');assert '### R59 实际全口引出' not in text;at=text.find('\n');p.write_text(text[:at]+note+text[at:],encoding='utf-8',newline='\n')
    p=ROOT/'docs/experiments/issue-126-full-pin/report.html';text=p.read_text(encoding='utf-8');assert '<main>' in text
    card='''<section id="r59-current-engineering" style="background:#fff4da;padding:18px;border-left:5px solid #ae741e"><h2>R59：真实施工在继续；原完整目标尚未完成</h2><p>LL已实际编辑9517个接点并补线，完整13507位保留，24个原生无块内端点/无原导线的声明口保持原位。实际编辑与双供电检查已执行；独立完整规则检查尚未终态，不能把它写成已经合法。当前正式选用源仍见<a href="status.html">唯一状态表</a>。</p><p>VECTOR新换型试验虽布线/寄生/独立native0完成，供电仍实际失败。已找到9个单元重放遗漏朝向，修正合法坐标与朝向后，布局和VSS通过；旧时钟线仍与VDD相碰，正按具体网络重接。像换了房间朝向，旧管线也必须重新接对，不能只移动图纸。对应对象包括_457487_以及时钟网clknet_leaf_167_clk/172_clk。</p><p>ACT/MXU/LL旧优化周边结果已证原生cells/连接/位置、PG、die、SDC指纹与当前源一致，可复用叶结果。其余三块已开始同当前资源的周边真实重布线。共同底座未冻结、两个完整功能与公平完整系统对照尚未做成。<a href="data/deadline_engineering_receipts.json">分阶段真实回执、原失败与SHA</a>。硬截止仍为北京时间10月30日09:19，目前预计不能在期限内全部验收通过；继续工程并按期如实交付。</p></section>'''
    p.write_text(text.replace('<main>','<main>'+card,1),encoding='utf-8',newline='\n');print('R59_NOTICE_RECORDED',now)
if __name__=='__main__':run()
