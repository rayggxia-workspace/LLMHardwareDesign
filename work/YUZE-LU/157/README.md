# R架构探索：独立实验 Issue157

任务 https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/157 。按rayggxia-project-collab v1.0.0记录；独立分支task/157-r-architecture，不修改Issue143/PR144生产、验收或作业。

冻结基线为Git e836741d334429be7d991cdc260f1ba955a7562e，实际输入字节/Git blob见BASELINE.json。A0 R源SHA4032c5ed，与run342映射及run030 GP ODB匹配。92059负载仅属于这个历史候选，不转移到A1/A2。

本地复现：python project/experiments/r_architecture/freeze.py；python project/experiments/r_architecture/candidates.py。远程固定镜像SHA49eae8...，Yosys0.68+post，Nangate45 typical库SHA8d540a...。完整候选源和原综合脚本在inputs/candidates；远程结果按独立attempt目录存放，源码归档和每份回执绑定SHA。

阶段：A0/A1/A2回归与小规模正负形式控制→严格完整等价→同配置综合；SystemC建模并行。完整证明失败/超时禁止该候选综合。最多1—2个通过系统筛选的新候选进行物理，不提前批量P&R。模型指标、分析预测、RTL测量和物理测量分别记录。

S合同：四个256×128bit单1RW Bank，总16KiB；只有一个窄请求口。宽读独占所有bank，同周期窄请求失去仲裁；各响应寄存器可背压，不把四个bank虚构为四个并发窄端口。现有SystemC #145是无时钟事务模型，不能直接当周期模型。

输入数值取自冻结test_recurrent_macro.cpp的独立宽整数定义。project/experiments/r_state/reference.py为不同算法/重试合同，不用作当前R oracle。

已取得阶段结果，见FUNCTIONAL_VALIDATION.md和BOTTLENECK_ANALYSIS.md。FINAL_RECOMMENDATION仍不提前选择。没有标定能量参数，只记录部分事件和参数化能量；新增控制/互联硬件未综合前不报告系统总面积数字。登记management-hub PR5 pending；无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。

## 实际作业与源码

独立远程根目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/`。全部源归档按Git blob原字节构建，BUNDLE.json记录源commit、路径、blob及SHA，FILES.sha256逐份核对，source.tar另有总SHA；回执见evidence/deployment*.json。远程source.tar是当次实际代码，不以当前分支代替旧作业源码。

|attempt|Slurm|实际结果/范围|
|---|---|---|
|001|94557，node21，96CPU|六个16CPU槽按依赖动态补位；A0/A1/A2回归通过，A1/A2完整证明及A0映射仍运行。映射必须消费同SHA完整证明通过回执|
|002|94563|SystemC初次编译失败，clock事件API错误；日志保留，不计通过|
|003|94565，node1|SystemC3.0.1串行外存策略扫描完成，1512配置|
|004|94571|宿主glibc不满足Verilator二进制，启动失败；日志保留|
|005|94573，node1|S双版本交换缓存策略扫描完成，1512配置|
|006|94574，node1|在固定容器内完成51份原R RTL corpus复核、12份容量不支持及M精确分解微基准|
|007|94576|afterany:94557依赖排队，不占运行节点；结束后只统计真实通过且映射SHA匹配的网表|

001最大六槽，当前只有三个重任务可运行，其余综合受完整等价依赖限制。重任务每项128GiB预测，按20%及16GiB保护，三个为476.8GiB；第四个超过480GiB预算。启动实际MemAvailable检查及--mem=0全节点内存约束保留。该预测不是实测逐进程峰值；worker回执maxrss_children_kib为整个worker已回收子进程的累计最大值，不用于冒充单任务峰值。SystemC批量队列为8个独立单核进程动态补位，编译/RTL交叉检查用16CPU分配。没有进入其他作业的allocation，没有取消已有作业。

## 复现命令

候选、输入与历史只读证据已冻结在本目录；无需先从当前RTL重新复制。若主动重新冻结，需确认Git含e836741d提交及原只读报告路径可访问，并另存新版本，不能覆盖本次输入后仍引用旧SHA。

在独立目录、固定EDA容器（README首部所列SHA）及96CPU allocation中：

```sh
source /OpenROAD-flow-scripts/env.sh
python3 project/experiments/r_architecture/worker.py --out /absolute/new-results
```

SystemC采用只读依赖`/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install`；共享库SHA为`930767c0ec7a203c38552201a22fa2a27a319c47d4d9019096457a674bca0848`。宿主GCC/C++17编译命令完整保存在各environment.json，不修改该安装和Issue153源码。

```sh
python3 project/experiments/r_architecture/systemc_sweep.py --out /absolute/new-systemc --sweep
python3 project/experiments/r_architecture/systemc_sweep.py --out /absolute/new-cache --sweep --cache
# 以下必须在上述固定容器内，宿主glibc不兼容Verilator：
python3 project/experiments/r_architecture/crosscheck.py --out /absolute/new-crosscheck --corpus /absolute/new-systemc/corpus
```

`--sweep`的四组外存参数为latency={20,100}周期、bandwidth={4,16}B/cycle；每次burst最多1024B，延迟按burst收费，单位时钟1ns仅用于SystemC计数，不是物理频率。全部工作负载为合成数据，不是真实模型。二进制完整输入和每token/layer期望状态保存在远程corpus（约94MB），仓库只放生成器、种子、配置、格式和逐文件SHA清单。

本地/有SSH权限的复收：`python project/experiments/r_architecture/collect.py`，之后`python project/experiments/r_architecture/report.py`。collect只读取指定报告，逐文件核对远端SHA并保存EVIDENCE.json；它不会拉取整个ODB、修改源或启动生产任务。表格中的旧A0物理量见baseline-evidence，重综合的A0即使源码一致也另行记录，禁止混用。

## 当前指标边界

SYSTEMC_RESULTS.csv共3024行。PASS表示完整整数数据相等且有限资源串行策略已执行，不表示新架构或所有控制接口逐拍校准通过。CSV的cycles为策略模型周期，尚未补齐完整命令接收/响应、控制器和下游握手；不能当最终完整token延迟。S_peak为模型显式保留容量峰值，真实RTL瞬时占用未测。未实现的C、物理/面积/功耗以及缺失的协议、冲突、FIFO、局部R存储事件，均不推断填数。详细限制与下一步见FUNCTIONAL_VALIDATION及PARETO_ANALYSIS。
