"""Stage report from actual receipts; deliberately no automatic winner."""
from pathlib import Path
import csv,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'work/YUZE-LU/157'
def write(name,text):(D/name).write_text(text.strip()+'\n',encoding='utf-8')
def main():
    rows=list(csv.DictReader((D/'SYSTEMC_RESULTS.csv').open()))
    def select(attempt,arch,workload):
        return next(x for x in rows if x['attempt']==attempt and x['architecture']==arch and x['workload']==workload+'.bin' and x['dram_latency']=='20' and x['dram_bytes_per_cycle']=='16')
    table='|策略|架构|模型周期|DRAM字节|S峰值保留字节|\n|---|---|---:|---:|---:|\n'
    for attempt in ('attempt003','attempt005'):
        for arch in ('A0','B256','B512','B1024','B2048'):
            r=select(attempt,arch,'W0-m0-n2048-t128');table+=f'|{attempt}|{arch}|{r["cycles"]}|{r["dram_bytes"]}|{r["S_peak"]}|\n'
    queue=json.loads((D/'evidence/attempt001/results/queue-state.json').read_text())['tasks']
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
    write('FUNCTIONAL_VALIDATION.md',f'''# 功能、数值与证明证据

更新时间：{stamp}。这是阶段报告，尚非完整研究验收。

## 已完成

A0/A1/A2均使用冻结原始bench，各自完成all-ones、随机初始化seed157、seed158三次运行。每次passed=true，240递推案例、100卷积案例、379979检查、178456周期。九次原始回执见evidence/attempt001/results/*-rtl/receipt.json中的initial_runs。小规模选择网络符号正例通过，错误银行极性真实负例被SAT拒绝；不能代替完整证明。

63份合成输入共93954508字节，逐文件SHA与全部完整期望状态见evidence/attempt003/results/corpus/MANIFEST.json及远程corpus目录。Python任意精度整数oracle与SystemC内独立C++128位整数实现比较全部输出、溢出标志与全部新/旧状态，不只比较摘要。两轮各1512配置，1212条数值PASS、300条UNSUPPORTED_CURRENT_MODEL；不支持的300条是C的252条及A0超过容量的48条，不能计作正确执行。

同一批二进制输入另由冻结原始R RTL执行：51份PASS、12份W2明确UNSUPPORTED_ORIGINAL_CAPACITY，共57377526检查、29225412个RTL驱动周期。见evidence/attempt006/results/RTL_CORPUS_RESULTS.json。每个可支持case按逐token/layer检查完整状态与输出，并核对EXEC延迟GDN=4*rows+15、SSM=3*rows+11、卷积14。读取、配置和背压的驱动周期也保留在该RTL报告中；它与SystemC模型总周期不是同一指标。

M另完成24组八元素精确S32乘法重构，包含INT32极值、U32极值、signed/unsigned及随机输入；600次M命令、4800个S8乘积逐值核对。25项S8分解精确，但宽归并目前在软件中，不是已有硬件功能。

## 尚未通过的门

完整顺序等价状态（采样）：{json.dumps(queue,ensure_ascii=False)}。A1/A2仍运行，未得到equiv_status -assert零未证明点，不能标等价通过。A1/A2标准单元综合依赖该门，无旁路。A0重综合仍运行。

SystemC目前把数值转移与时序资源分开建模：时钟化有限FIFO、串行DMA、S窄端口、DRAM和R阶段延迟均明确，但没有逐拍驱动所有原R命令/响应，也没有实现并发宽/窄仲裁的RTL对照、完整新控制器或缓存数据交换的逐位硬件证明。因此CSV的PASS只表示整数转移及该策略执行无错误，不能表述为端到端周期模型或新架构验收通过。

corpus中拒绝提交/reset/invalid等flags目前约束事务模型的最终发布决策；RTL corpus复核以abort保留旧状态，并未把这些flags都转换成对应接口负例。真实无效命令、在途reset、epoch耗尽、背压、提交失败的接口测试来自冻结bench，不能声称SystemC也已逐拍覆盖这些协议。

## 扩展语义

超过2048元素按相同8lane纵向扩展，保持S32状态、S16 key/query、U32 decay/beta/factor、逐点RNE和fits32检查，所有分块的预测/读出先用有符号宽整数全局累加，最后一次RNE；不能分块舍入。GDN先全状态预测再一次误差广播。任意溢出全事务拒绝，旧版本不变。SSM skip与四抽头历史在全事务成功时才发布。4096/8192参考仅为独立整数扩展，原始R不支持，不能标作原RTL通过。
''')
    write('BOTTLENECK_ANALYSIS.md',f'''# 瓶颈转移：当前可复核结果

原始92059个bank_role直接负载是历史run342映射/run030 GP的数据，匹配A0 SHA4032c5ed。65536 active、26123 shadow、396其他/共享读取、4写控制及共享反相器；91686个MUX2_X1/S加373个其他输入。主要根因在逐元素银行读取选择，不是每位写使能。原始 nominal pin-C=176628.130638 fF；GP placement估计电容不是提取电容。历史详证在baseline-evidence/REPORT.md，不赋予新候选资格。

## 状态驻留与搬运策略

下面为W0 GDN、2048元素、128 token、单上下文，DRAM参数20周期/请求启动、16B/cycle，每请求至多1024B；时钟周期仅模型单位，不据此推导芯片频率。attempt003为串行窄口DMA/外存分块；attempt005在容量允许时增加S内双版本交换缓存。两者均非最优调度。

{table}

小R外存分块先全局DEC/PRED，保存decayed candidate，再全局UP/READ；旧DRAM版本一直保留。candidate写回和读回流量计入intermediate_bytes，不能把它忽略。单上下文本地可容纳则跨token驻留，不每token强制flush。

S缓存的可用条件为2*(elements-capacity)*4+512元数据+1024单DMA缓冲 <=16384；R本地两bank不计入S。每次换块都逐16B交换两个版本，S仍只有一个16B窄口；没有四个免费并发端口。B256在此例S峰值保留15872B，逼近容量。S缓存把DRAM从4403200B降至225280B，但增加8402944B S读取和同量写入；总周期从1641728升至2375744。原外存瓶颈转为串行S/互联换块瓶颈，当前策略没有延迟净收益。不能据此否定尚未实现的并行或更优缓存调度。

W1的24层×1024状态×128 token，在当前串行换层策略下，A0/B1024/B2048均为10684416模型周期、27033600B DRAM；不因为R2048能容纳两个1024元素就虚构双上下文控制。B1024存在值得后续检验的容量点，但面积及控制开销未测，不能称为获胜者。

W2原A0明确不支持。B2048等模型支持全局归约及双版本外存工作流，但新增调度/提交控制器尚无RTL和面积。W3虽然只有32个宽乘积，是否取消专用R仍取决于M分解、历史事务及共享资源争用，尚无系统代价结论。

## 无R能力边界

E输出基本S16饱和，不能把宽状态乘法先饱和再恢复；M可读S64结果，但输入是S8/S16数位。实际测得一种base128五数位×五数位方案：8路S32乘法25次M命令，执行延迟合计300周期，加载/执行/读回/握手合计600周期，均未含宽归并硬件、DMA、事务控制和抢占其他M工作负载的代价。全24组共600命令/14400周期，见M-s32-probe.log。此方案可行但不保证最优；S32×S16可少于25项，不能统一按25项冒充最优结果。

## 尚未测量

A1/A2映射后的bank_role与地址/写使能最大扇出、总负载电容、门级深度；新设计的STA、线长、拥塞与电气；R-lite及新控制器/互联总面积；C完整周期和流量；并发调度及其他M/E任务争用。均未测。不能依据RTL里的mux样式或SystemC事件数填写这些物理指标。
''')
    write('PARETO_ANALYSIS.md','''# Pareto分析状态

目前不能形成包含面积、完整token延迟、能耗和通信的合格非支配解集合。新候选面积和物理结果未测，C未实现宽归并与完整系统模型；SystemC是已执行的受限串行策略，不是全部接口逐拍校准的端到端结果。

因此不淘汰大型R/R-lite/C，也不启动新候选P&R。只记录同一策略、同一DRAM参数及工作负载内的周期/流量对照，见BOTTLENECK_ANALYSIS.md。面积缺失不能填0；未标定能耗不能用操作次数充当焦耳。

参数化能量应分开统计S32×U32、S32×S16、S8乘、宽加/舍入、各级读写及每条互联字节：E=sum(N_op*e_op)+sum(B_level_read*e_read+B_level_write*e_write)+sum(B_port*e_port)。当前CSV只有部分事件计数，操作分类、R局部bank访问和物理校准未齐，能耗为未测。M中非对角零乘与有用乘积要区分，不能把数值非零率自动当硬件门控率。

下一步先补齐完整协议/存储/互联事件与C，再综合R-lite和新增控制硬件，保留所有低于精度/原子性要求的失败。只有系统筛选后最多1—2个新候选进入物理，不能把历史A0物理验收转移给新候选。
''')
    write('FINAL_RECOMMENDATION.md','''# 阶段建议；尚无最终架构推荐

当前证据不足以决定保留大型R、缩小R或取消R。保留三条研究线，不把未测系统面积、未实现C或未通过完整等价的A1/A2写成成功。

已确认的取舍：大型R在单上下文连续token驻留时减少搬运；1024元素上下文频繁换层时，当前模型内R1024与R2048周期相同；小R的S双版本缓存能降DRAM字节，却可能增加窄口与互联周期。取消R存在精确M整数分解路径，但现有M/E没有免费八路S32乘法，也没有完整全局宽归并及提交控制器。

下一决策门：A1/A2完整等价→同配置映射扇出/面积；SystemC完整接口时序及S仲裁校准→C及R-lite控制器实现/面积→完整系统敏感性与Pareto→最多1—2个新候选物理。当前未进入物理阶段，未产生最终setup/hold、拥塞或布线结论。
''')
    # Preserve exact historical data separately from the still-running resynthesis.
    with(D/'SYNTHESIS_RESULTS.csv').open('w',newline='',encoding='utf-8')as f:
        fields=['candidate','status','source_sha256','area_um2','cells','DFF','MUX','BUF','bank_role_direct_fanout','bank_role_pin_cap_ff','physical_status'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        candidates=json.loads((D/'CANDIDATES.json').read_text())
        for kind in ('A0','A1','A2'):
            src=D/'candidates'/kind/'block_v1_r.sv';row={k:'未测'for k in fields};row.update(candidate=kind,status=queue[kind+'-map'],source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),physical_status='NOT_RUN');w.writerow(row)
    write('STAGE_STATUS.json',json.dumps(dict(updated=stamp,task_status='in_progress',queue_snapshot=queue,systemc_rows=len(rows),systemc_scope='partial serialized policy; not complete architecture acceptance',physical_started=False,final_recommendation=False),indent=2,ensure_ascii=False))
    print('Updated reports from actual evidence; no final recommendation.')
if __name__=='__main__':main()
