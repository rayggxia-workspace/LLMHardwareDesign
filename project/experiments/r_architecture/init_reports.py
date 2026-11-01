from pathlib import Path
import csv,json
R=Path(__file__).resolve().parents[3];O=R/'work/YUZE-LU/157'
docs={
'README.md':'''# R架构探索：独立实验 Issue157

任务 https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/157 。按rayggxia-project-collab v1.0.0记录；独立分支task/157-r-architecture，不修改Issue143/PR144生产、验收或作业。

冻结基线为Git e836741d334429be7d991cdc260f1ba955a7562e，实际输入字节/Git blob见BASELINE.json。A0 R源SHA4032c5ed，与run342映射及run030 GP ODB匹配。92059负载仅属于这个历史候选，不转移到A1/A2。

本地复现：python project/experiments/r_architecture/freeze.py；python project/experiments/r_architecture/candidates.py。远程固定镜像SHA49eae8...，Yosys0.68+post，Nangate45 typical库SHA8d540a...。完整候选源和原综合脚本在inputs/candidates；远程结果按独立attempt目录存放，源码归档和每份回执绑定SHA。

阶段：A0/A1/A2回归与小规模正负形式控制→严格完整等价→同配置综合；SystemC建模并行。完整证明失败/超时禁止该候选综合。最多1—2个通过系统筛选的新候选进行物理，不提前批量P&R。模型指标、分析预测、RTL测量和物理测量分别记录。

S合同：四个256×128bit单1RW Bank，总16KiB；只有一个窄请求口。宽读独占所有bank，同周期窄请求失去仲裁；各响应寄存器可背压，不把四个bank虚构为四个并发窄端口。现有SystemC #145是无时钟事务模型，不能直接当周期模型。

输入数值取自冻结test_recurrent_macro.cpp的独立宽整数定义。project/experiments/r_state/reference.py为不同算法/重试合同，不用作当前R oracle。

当前结论均待实验，FINAL_RECOMMENDATION不提前选择。没有标定能量参数，只记录事件和参数化能量；新增控制/互联硬件未综合前不报告系统总面积数字。登记management-hub PR5 pending；无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。
''',
'ARCHITECTURES.md':'''# 候选与统一比较边界

A0：原始2048×S32双bank R。A1：各bank先选8元素，再选active/shadow，覆盖DEC/PRED/READ/UP预取及命令11动态四字读；写逻辑逐字保留。A2：32组×64元素，局部行选择/银行选择、再组选择，更新和装载均按组译码；保留两bank、八lane和逐拍接口。

系统容量曲线B256/B512/B1024/B2048均为每bank可存S32元素数，保留八路宽乘资源、一个本地上下文；B2048是原规模对照。C为无R的M/E/S组合，S32状态不可被S16饱和截断；须精确整数分解并单独计宽归并/舍入/溢出/事务控制扩展。

用户列出的具体矩阵产生8条记录（A0/A1/A2、四容量、C），其中B2048与A0共享容量基准；不为凑“六种”删除明确要求的容量或无R对照。系统级容量与RTL重排两个实验轴分开，A1/A2没有测得周期变化之前不得假定更快。

跨块GDN先完整decay及全状态预测归约→一次误差计算→广播到所有块→更新→全读出归约；不得每块独立EXEC/COMMIT。SSM先decay/注入、全读出与skip，四抽头历史只在全事务提交后更新。外部old/candidate双版本；所有块、输出溢出、owner/epoch/position及写回完成均通过后发布一次全局版本。

M目前S8数位、双S16需9发射；E基本S16饱和，不能免费宽乘。C的S32分解、宽中间归并和S64舍入/检查都需要真实资源/周期/流量预算；扩展尚未实现的指标保留未测。
''',
'FUNCTIONAL_VALIDATION.md':'''# 功能与逐拍等价

当前待执行。原始RTL基准bench三初态（all-ones、seed157、seed158），含GDN/SSM、完整动态读、连续递推、四抽头卷积、溢出回滚、无效命令、背压、reset和提交失败。A0/A1/A2均使用同一冻结bench。

小规模选择网络正例+错误银行极性反例仅验证工具及代数，不替代完整证明。完整设计经proc/memory_map进行通用证明降级，equiv_make/equiv_simple/equiv_induct后equiv_status -assert全通过才准综合；保留所有状态、输出、时钟/复位和错误分支。不以bounded、局部或黑盒证明代替完整。

SystemC数值模型尚未通过逐位RTL对照，任何早期性能结果都不能视为合格架构。大于2048状态的参考扩展须独立明确64位跨块累加、最终一次RNE和全局事务。
''',
'BOTTLENECK_ANALYSIS.md':'''# 瓶颈转移分析

原A0直接根网92059负载读取占主导；原完整扇出/空间证据见baseline-evidence。A1/A2须共同检查bank_role、row、cmd_index、写使能、局部译码和反相分支，不能只报目标网下降。

系统比较必须同一工作负载同一数值：本地面积减少时加上S容量/扩展控制/互联；计算省拍时加上搬运、端口仲裁、双版本写回及提交；驻留与多层切换分别计价。未有完整链路结果前不判净收益。

当前所有新候选结构/时间/通信/存储净收益：未测。阶段结果到达后逐候选写原瓶颈、新瓶颈和系统净变化。
''',
'PARETO_ANALYSIS.md':'''# Pareto方法与当前状态

仅在数值/事务验证通过、相同W/外存参数/宏实例预算下比较面积、完整token周期、外存字节、互联流量和参数化能量。未知面积、未标定能量或无物理线长不能填0，也不能据缺项把候选判为非支配。

当前非支配解：未确定。完整控制器/互联/宽算术扩展面积未测，尚不能比较全系统面积或给出面积最优结论。
''',
'FINAL_RECOMMENDATION.md':'''# 最终建议（尚无最终结论）

当前不推荐冻结大型R、R-lite或无R中的任何一个。先完成真实功能/完整等价和同条件结构对照，再以W0驻留、W1切换、W2全归约及W3历史事务的完整周期/流量确定适用域。最多1—2个新候选进入物理。

保留大型R是否值得，取决于驻留收益能否抵消存储/选择网络代价；R-lite是否有效取决于两遍GDN、S端口与DRAM双版本流量；无R必须真实计入S32分解、宽归并、M/E占用及控制扩展。当前这些全系统指标未测，不将单项扇出改善写成成功。
'''}
for n,s in docs.items():(O/n).write_text(s,encoding='utf-8')
with (O/'SYNTHESIS_RESULTS.csv').open('w',newline='',encoding='utf-8')as f:
    w=csv.writer(f);w.writerow(['candidate','status','source_sha256','area_um2','cells','DFF','MUX','BUF','bank_role_direct_fanout','bank_role_pin_cap_ff','physical_status'])
    for row in json.loads((O/'CANDIDATES.json').read_text()):w.writerow([row['candidate'],'NOT_RUN',row['sha256']]+['未测']*7+['NOT_RUN'])
with (O/'SYSTEMC_RESULTS.csv').open('w',newline='',encoding='utf-8')as f:csv.writer(f).writerow(['candidate','workload','validation','cycles','token_latency','dram_state_read_bytes','dram_state_write_bytes','coefficient_bytes','s_peak_bytes','s_port_stall_cycles','interconnect_bytes','mac_utilization','system_area_um2','energy_model'])
print('Initialized',len(docs)+2,'requested reports')
