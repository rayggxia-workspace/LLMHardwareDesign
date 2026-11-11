"""Build the research report from verified run35/run36/run37 results only."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

parser=argparse.ArgumentParser()
parser.add_argument('--runs-root',type=Path,default=Path(__file__).resolve().parent)
parser.add_argument('--repo',type=Path)
ARGS=parser.parse_args()
ROOT=ARGS.runs_root.resolve()
REPO=ARGS.repo.resolve() if ARGS.repo else ROOT.parent/'242/r-load-bounds/repo'
EVIDENCE=REPO/'work/Melodydt/247/optimization-sweep'


def main():
    a=json.loads((EVIDENCE/'analysis.json').read_bytes())
    b=json.loads((EVIDENCE/'run36/analysis.json').read_bytes())
    c=json.loads((EVIDENCE/'run37/analysis.json').read_bytes())
    reports=(a,b,c)
    assert all(r['passed'] for r in reports) and sum(r['scenario_count'] for r in reports)==192
    raw=[json.loads((ROOT/f'run{n}/receipts/results/result.json').read_bytes()) for n in (35,36,37)]
    cases={}
    for report in reports:
        for row in report['comparisons']:
            key=(row['optimization'],row['workload'],row['profile'],row['dual_ports'])
            if key in cases:
                assert cases[key]['tokens_per_second']==row['tokens_per_second']
            else:cases[key]=row
    names=list(dict.fromkeys(c['optimization'] for r in reports for c in r['comparisons']))
    work=(('decode512','queued_pipe_w8'),('decode512','queued_pipe_w16'),('decode2048','queued_pipe_w8'),('prefill2','queued_pipe_w8'))
    def row(name,w='prefill2',p='queued_pipe_w8',dual=True):return cases[name,w,p,dual]
    def rate(name,w='prefill2',p='queued_pipe_w8',dual=True):return row(name,w,p,dual)['tokens_per_second']
    def gain(name,w='prefill2',p='queued_pipe_w8',dual=True):return row(name,w,p,dual)['speed_gain_percent']
    fixed=[r for r in cases.values() if r['intervention_ledger']['DDR_B_s']==17.1e9]
    best_fixed=max(fixed,key=lambda r:r['tokens_per_second'])
    best_all=max(cases.values(),key=lambda r:r['tokens_per_second'])
    baseline=[c for c in raw[0]['cases'] if c['optimization']=='base']
    bottlenecks=[]
    for c in baseline:
        r=c['result'];end=r['detail']['end_subcycles']
        bottlenecks.append(dict(workload=c['workload'],profile=c['profile'],dual_ports=c['dual_ports'],
            measured_condition_seconds=r['seconds'],effective_DDR_GB_s=(r['read_bus_bytes']+r['write_bus_bytes'])/r['seconds']/1e9,
            bus_active_fraction=[ch['bus_work_subcycles']/end for ch in r['detail']['channels']],
            weight_fraction=sum(ch['flows']['weight']['bus_read'] for ch in r['detail']['channels'])/(r['read_bus_bytes']+r['write_bus_bytes']),
            spans_percent={k:v*100/r['ticks'] for k,v in r['spans_ticks'].items()},
            P_stage_percent=[dict(worker=p['worker'],ready=p['consumer_ready_wait_subcycles']*100/p['elapsed_subcycles'],
                input_ACK=p['input_ACK_wait_subcycles']*100/p['elapsed_subcycles'],service=p['service_subcycles']*100/p['elapsed_subcycles'],
                output=p['output_subcycles']*100/p['elapsed_subcycles']) for p in r['detail']['P']]))
    bd=next(x for x in bottlenecks if x['workload']=='decode512' and x['profile']=='queued_pipe_w8' and x['dual_ports'])
    bp=next(x for x in bottlenecks if x['workload']=='prefill2' and x['dual_ports'])
    combined=dict(schema=1,scope='original conditional metric with explicit one-factor/combined interventions',
        scenarios_executed=192,unique_scenarios=len(cases),source_commits=[r['source_commit'] for r in reports],
        verified_received_files=sum(r['verified_received_files'] for r in reports),
        complete_historical_controls=sum(r['complete_historical_controls'] for r in reports),
        negative_result_checks=sum(r['negative_result_checks'] for r in reports),
        highest_fixed_DDR=best_fixed,highest_all=best_all,bottlenecks=bottlenecks,comparisons=list(cases.values()),
        native_full_model_tokens_per_second=None,physical_clock_qualified=False)
    (EVIDENCE/'combined.json').write_text(json.dumps(combined,indent=2)+'\n',encoding='utf8')
    lines=['# 当前共享32KiB方案的后续优化评估','',
        'Issue247 / PR243；负责人Melodydt。2026-11-10，Asia/Shanghai。三批服务器SystemC运行共192场景，生产RTL未修改。','',
        f'**结论：保持共享32KiB和17.1GB/s，向量8路＋S16桥接＋4路NExp的prefill条件结果为{rate("vector8_s16_n4",dual=False):.6f}/{rate("vector8_s16_n4"):.6f} token/s（shared/idealdual）。这是本轮优先建议。** 桥接额外费用从1提高到8拍/8值，idealdual仍为'+f'{rate("vector8_s16_n4_bridge8"):.6f}。固定外存带宽的最高组合为{best_fixed["tokens_per_second"]:.6f} token/s，包含更多M/供数资源，面积代价更大。所有数值均为旧条件模型结果，原生RTL整图速度仍未测得。','',
        '## 1. 评价口径与当前实现边界','',
        '保留原四种工作负载：W8 decode context512、W16 decode context512、W8 decode context2048、W8 prefill2。频率300MHz、2P/1U，默认外存17.1GB/s、共享32KiB、每P四槽、共享A32B/拍、全局池服务64B/拍；保留原S32/K256/S96及R1/R2/R4调度合同。prefill2按两个输入token除以完整trace时间，不能与decode的单token延迟混用。','',
        'shared表示P本地读写共用服务预算；idealdual表示P本地各64B/拍读、写日历独立，U仍共用端口。当前P后端逻辑1R1W已验证，但M写回及普通IO仍128bit，独立wide_write才是512bit；不能把后端峰值当作整条访问路径已经兑现模型合同。','',
        'DDR25.6/34.2GB/s两行显式改变外存条件，其他行仍17.1GB/s。新计算/端口宽度和S16桥接只是待实现服务目标；没有新的RTL校准、完整权重生成验证或300MHz物理验收。现有真实RTL的格式转换、K32命令展开、DMA/LOAD汇合与队列费用仍须进一步校准。','',
        '## 2. 基线瓶颈证据','',
        f'W8 decode512的idealdual基线中，Dot占完整trace时间{bd["spans_percent"]["Dot"]:.2f}%，权重占外存总线字节{bd["weight_fraction"]*100:.2f}%；平均有效外存流量{bd["effective_DDR_GB_s"]:.3f}GB/s。两通道总线忙占比分别{bd["bus_active_fraction"][0]*100:.2f}%/{bd["bus_active_fraction"][1]*100:.2f}%，并非全程100%占满；带宽敏感性仍证明外存服务是decode的重要限制。不能把可重叠的等待计数相加当作总耗时。','',
        f'W8 prefill2的idealdual基线中，Dot占{bp["spans_percent"]["Dot"]:.2f}%，向量阶段占{bp["spans_percent"]["vector"]:.2f}%，NExp占{bp["spans_percent"]["NExp"]:.2f}%。36个NExp操作、792576个值全部是S16输入回退，原S32快路径没有覆盖它们。这说明优化U及格式覆盖比单独继续加MAC更直接。','',
        '## 3. 各方向方案、结果与实施含义','',
        '### 3.1 优先补齐S16 NExp快路径','',
        f'保留4路NExp服务，只增加显式S16到既有低16位数值合同的打包桥接。模型每8值另收1拍，保留全部S读写、vector_region、缓存与DDR费用。prefill达到{rate("s16_n4",dual=False):.6f}/{rate("s16_n4"):.6f} token/s，较同层基线+{gain("s16_n4",dual=False):.2f}%/+{gain("s16_n4"):.2f}%；三个decode不变。','',
        f'继续增加到8路只到{rate("s16_n8"):.6f}（idealdual），较4路桥接方案再提高{(rate("s16_n8")/rate("s16_n4")-1)*100:.2f}%。因此先做格式桥接和资格验证，再决定是否复制NExp单元。桥接的1拍/8值是假设目标，不能称为已测RTL延迟；必须检查符号、缩放、饱和、尾包和背压。','',
        '### 3.2 扩宽U向量流水','',
        f'既有4路向量扩为8/16路，保留每包5拍固定开销及所有存储访问。prefill idealdual分别{rate("vector8"):.6f}/{rate("vector16"):.6f}，增幅{gain("vector8"):.2f}%/{gain("vector16"):.2f}%；W8 decode512的16路为{rate("vector16","decode512"):.6f}（+{gain("vector16","decode512"):.2f}%）。只扩两处向量流水，未把归约、拷贝或整个U费用同比缩小。','',
        f'16路向量与S16桥接4路NExp实际联合仿真得到{rate("vector16_s16_n4",dual=False):.6f}/{rate("vector16_s16_n4"):.6f}，相对基线+{gain("vector16_s16_n4",dual=False):.2f}%/+{gain("vector16_s16_n4"):.2f}%。没有扩共享容量，也没有增加M乘法并行度；作为性能优先的候选保留。','',
        f'进一步测试较小的8路向量＋S16桥接组合，prefill为{rate("vector8_s16_n4",dual=False):.6f}/{rate("vector8_s16_n4"):.6f}（+{gain("vector8_s16_n4",dual=False):.2f}%/+{gain("vector8_s16_n4"):.2f}%）。桥接成本放宽到8拍/8值时仍为{rate("vector8_s16_n4_bridge8",dual=False):.6f}/{rate("vector8_s16_n4_bridge8"):.6f}。因此若以面积与达到条件5 token/s兼顾，先实施8路，再决定是否升到16路；这不是原生RTL吞吐保证。','',
        '### 3.3 M计算与A/B供数必须配套','',
        '单独将M主体的K并行8→16，保留启动、尾部及结果读回费用，本轮四场景两端口层均没有提速。单独将A32→64B、B适配64→128B也收益很小，因为本地S总读服务仍64B、池全局服务仍64B。','',
        f'M16与A/B扩宽联合后，prefill idealdual为{rate("m16_feed2"):.6f}（+{gain("m16_feed2"):.2f}%）。继续把M本地取数扩到128B仅到{rate("m16_feed2_read128"):.6f}，较前者增{(rate("m16_feed2_read128")/rate("m16_feed2")-1)*100:.3f}%。供数、存储、计算的收益不能相乘。','',
        f'加入向量16路和S16桥接4路NExp的完整组合达到{rate("balanced",dual=False):.6f}/{rate("balanced"):.6f}；相对较小的向量＋S16方案，idealdual再增{(rate("balanced")/rate("vector16_s16_n4")-1)*100:.2f}%。需要更大面积及新端口组织，应保留为备选，不能优先假设单独加MAC就有效。','',
        '### 3.4 外存带宽主要帮助decode','',
        f'总带宽17.1→25.6→34.2GB/s，W8 decode512 idealdual从{rate("base","decode512"):.6f}→{rate("ddr25p6","decode512"):.6f}→{rate("ddr34p2","decode512"):.6f}，后者+{gain("ddr34p2","decode512"):.2f}%；W16 decode512达到{rate("ddr34p2","decode512","queued_pipe_w16"):.6f}（+{gain("ddr34p2","decode512","queued_pipe_w16"):.2f}%）。保留原两通道、信用、延迟、行切换及S服务，没有免费消除所有DMA成本。','',
        f'prefill的idealdual仅升至{rate("ddr34p2"):.6f}（+{gain("ddr34p2"):.2f}%），说明其U与计算限制更明显。外存接口、封装和控制器是否能提供该带宽须另行确认；这两行不是17.1GB/s下的优化结果。','',
        '### 3.5 共享池继续扩容','',
        f'共享48/96KiB的prefill idealdual为{rate("pool48"):.6f}/{rate("pool96"):.6f}，较32KiB增加{gain("pool48"):.2f}%/{gain("pool96"):.2f}%。三个decode在48和96之间完全同速，不能期待容量不断翻倍产生同等收益。当前更建议保留32KiB，先实施格式与向量路径优化。','',
        '### 3.6 补齐M写回通路，收益须如实计量','',
        f'旧模型已按64B/拍计M结果写入。把它收紧为实际普通写通路的16B/拍，prefill idealdual变成{rate("write16"):.6f}；从该修正对照补到64B恢复{rate("base"):.6f}，增幅{(rate("base")/rate("write16")-1)*100:.3f}%。W8 decode512对应增幅{(rate("base","decode512")/rate("write16","decode512")-1)*100:.3f}%。这只是带宽敏感性，不含真实命令/ACK/打包成本；不能把已包含在旧基线里的64B收益重复添加。','',
        '### 3.7 NExp单纯加路数的负结果','',
        f'仅将已合格S32路径从4路变8路，W8 decode512 idealdual从{rate("base","decode512"):.6f}到{rate("nexp8","decode512"):.6f}；prefill完全不变，因为没有命中该格式路径。它应排在S16桥接之后，不能用局部两倍吞吐代替整图收益。','',
        '## 4. 面积与实施顺序','',
        '| 方向 | 面积/资源判断 | 建议 |','|---|---|---|',
        '| S16桥接＋原4路NExp | 增加打包、控制和有限缓存；没有要求增加NExp算术路数，具体面积未综合 | 第一优先，先做格式/数值/背压验证 |',
        '| 向量8/16路 | 对所扩向量算术部分约2/4倍路数，不能等同整个U面积倍数 | 第二优先；优先8路＋S16桥接，16路保留余量 |',
        '| NExp8路 | 相对4路约增加一倍该算术通路，整图额外收益有限 | 暂缓 |',
        '| M16＋宽供数＋128B本地读 | MAC主体约2倍K并行度，新增互连/端口/FIFO费用；不是已实现 | 大面积备选，实施前独立备份与综合 |',
        '| DDR25.6/34.2GB/s | 控制器、接口和封装代价未测 | decode目标且外部系统允许时优先 |',
        '| 共享48KiB | 比32KiB增加4颗4KiB宏，宏外框代理+0.369848mm² | 不优先于桥接/向量 |',
        '| 共享96KiB | 比32KiB增加16颗4KiB宏，宏外框代理+1.479393mm² | 保留为容量备选 |','',
        '宏代理使用既有4KiB宏0.092462050025mm²，只计宏外框，不含控制/布线/STA。128B读取若沿用同类宏并采用8lane×双位置，每P需要16宏、物理64KiB，相比当前8宏/P再增加32KiB/P；两P额外宏代理约1.479393mm²，逻辑16KiB可保留但需使用半深度。这只是一个组织选项，其他宏/端口方案需重新评估，不能作为已测面积或最小面积。','',
        '建议顺序：S16 NExp桥接验证 → U向量8路联合实现 → 原生整图/连续负载校准 → 视余量再升16路。若decode为首要目标且可调整系统，则推进外存带宽可行性；M/128B本地读和大容量共享池作为后续备选。当前分支和三个模型commit已保留全部方案；本轮没有实装这些新增候选。','',
        '## 5. 全场景速度表','',
        '单位均为条件token/s。每一行是独立实际SystemC运行或实际联合运行，不是Amdahl外推。write16为修正对照；其余默认比较共享32KiB、17.1GB/s基线，容量和外存变化按名称显式标出。','']
    for dual in (False,True):
        lines+=['### '+('idealdual：独立读写日历' if dual else 'shared：读写共用日历'),'','| 方案 | W8 decode512 | W16 decode512 | W8 decode2048 | W8 prefill2 |','|---|---:|---:|---:|---:|']
        for name in names:
            lines.append('| '+row(name)['label']+' | '+' | '.join(f'{rate(name,w,p,dual):.6f}' for w,p in work)+' |')
        lines.append('')
    lines+=['## 6. 验证、来源及复跑','',
        'run35/job102040（源码e2f91b346f57e872610b0e416290901f5d5e666e）、run36/job102041（源码d9afc95a9b649b096c8a7930d99d56d065d78047）和run37/job102043（源码f1700f031d629e5af33ad8b36ff9523a6393d90b）均在服务器c64/node1/4核Slurm中执行。三个作业均COMPLETED 0:0，合计192例通过；40次历史全RESULT控制一致，960个篡改结果负控拒绝。','',
        '实际生成的共享池A32/A64两设置合计4350个独立数值输出比较、60个生命周期负控和18个事件篡改检查通过；这仅验证共享池的地址/数据/FIFO模型，不是新NExp8/M16/S16桥接RTL数值验收。各例保持外存字节/描述符与M命令/tiles守恒，并核验逐类工作差额、有限队列和token换算。','',
        f'本地逐SHA核验{combined["verified_received_files"]}个回收文件，并重新从逐例日志解析RESULT与主回执比对；完整事件和结果保存在个人服务器run35/run36/run37及本地receipts，仓库仅存轻量分析和索引。收集脚本初次因登录节点Python3.6不支持text参数失败，改用universal_newlines后成功；未重跑或修改已成功仿真。','',
        f'run35 result SHA-256：{a["result_sha256"]}；run36 result SHA-256：{b["result_sha256"]}；run37 result SHA-256：{reports[2]["result_sha256"]}。工具版本及容器/SystemC库SHA见证据目录，所有输入版本沿用冻结manifest。','',
        '[主扫描源码](../../project/experiments/optimization_sweep/README.md)、[补充扫描源码](../../project/experiments/optimization_followup/README.md)、[桥接敏感性源码](../../project/experiments/optimization_bridge_study/README.md)、[完整派生比较与瓶颈](../../work/Melodydt/247/optimization-sweep/combined.json)、[接续记录](../handoffs/2026-11-10-issue-247-optimization-sweep.md)。','',
        '复跑必须在Slurm分配中，按各目录job.sh执行并携带冻结输入manifest。只做本地后处理时使用证据目录analyze.py，明确传入--runs-root与--repo；管理检查python scripts/check_project.py不代替业务仿真。','',
        '交付状态：研究结果待正式审查，PR243未合并，不标done；登记PR5 pending、看板unverified/同步pending，CI既有无steps/runner限制待管理员核实。没有活动仿真或自动监测。此前run24/25原包上传阻塞保留，本轮未重传旧包。','']
    path=REPO/'docs/experiments/issue-247-optimization-sweep.md'
    path.write_text('\n'.join(lines),encoding='utf8',newline='\n')
    if (ROOT/'optimization-analyze.py').exists():shutil.copyfile(ROOT/'optimization-analyze.py',EVIDENCE/'analyze.py')
    if Path(__file__).resolve()!=(EVIDENCE/'build_report.py').resolve():shutil.copyfile(Path(__file__),EVIDENCE/'build_report.py')
    (EVIDENCE/'evidence-index.json').write_text(json.dumps(dict(source_commits=combined['source_commits'],
        report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),runs=[dict(run=r['run'],job=r['job'],
        result_sha256=r['result_sha256'],receipts_sha256=r['receipts_sha256']) for r in reports],
        raw_retention='Authorized personal server run35/run36/run37 and local receipt archives; not a complete raw Git upload'),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(report=str(path),highest_fixed=best_fixed,unique=len(cases))))


if __name__=='__main__':main()
