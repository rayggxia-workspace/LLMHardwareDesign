# Block v1 节点内并行与实测资源

用户要求本任务可使用 6～8 个节点，并在节点内适当并行，尤其是 c96。沿用统一 dispatcher 的 `base_nodes=6`、`max_nodes=8`；RUNNING、PENDING 和提交状态不确定的 allocation 均计入上限，与其他成员任务分开核对。一个分组只申请一个 Slurm allocation，子任务使用独立目录、日志、起止时间与回执，线程上限之和不得超过实际分配。

并发数同时受 CPU、实测内存和依赖限制。依赖未完成不启动消费者；失败分支不能取消已在运行的独立分支。不得因耗时长取消既有任务，也不改写历史归档、回执或原始失败。新增分组优先把不同候选、初始化/激励或独立场解放在同一节点内执行。

## 已观察到的资源边界

| 实际任务 | 节点内工作 | 分配/耗时/TotalCPU | 结论 |
| --- | --- | --- | --- |
| 132/92204 | 两路真实 pin-access 各 8 核 | 16 核、3:35、53:58.362 | 分配 CPU 利用约 94.1%，此阶段并行有效 |
| 135/92222 | A/C 完整物理与 A/C 最终功能四路，各 16 核 | 64 核、48:10、4:55:06 | 整体约 9.6%，固定 DRC 线程和阶段尾部等待限制利用率；不能套用 pin-access 的并行度 |
| 148/92231 | A/C 只读 DRC 定位各 8 核 | 16 核、1:11、54.043 秒 | 两路实际重叠约 26.75 秒，峰值 1299772 KiB；声明 8 核不等于扫描过程实际使用 8 核 |

利用率计算为 `TotalCPU / (Elapsed × AllocCPUS)`，只描述相应完整 allocation。MaxRSS 是 Slurm 返回值，不据此宣称每条子进程各自的内存峰值。

2026-10-27 实际读取安装容器中的原生 `FreePDK45.lydrc`，SHA256 为 `4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`；其设置为 `tiles(1000.um)`、`tile_borders(1.um)`、`deep`、`threads(4)`。因此增加外层 `NUM_CORES` 不会自动将独立 DRC 改为 32 或 96 线程。[KLayout 官方 DRC 参考](https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html)说明 `threads` 控制 tiling 的并行核心数；实际效果仍应由安装版本和运行数据确认。

## 后续执行约束

1. 为各阶段分别估计并发，不把综合/路由线程数直接套到单线程扫描或固定 4 核 DRC。新轻量定位可按实测峰值加余量降低申请量，记录实际 CPU 限额；历史 148 保持原样。
2. c96 优先容纳多项独立工作，例如多个场解方向/offset、不同候选或激励。内存占用显著的完整 C8 接收继续使用严格内存预检，可退为两路/串行；不以凑满核数造成内存超额。
3. 长流水线保留阶段起止时间和完整 Slurm 终态。若要改变原生 DRC 的线程或 tiling 配置，先在保留全部规则、输入和输出的控制中证明结果一致，再以新归档运行；本轮未改变 DRC 配置。
4. 先解决 135 的真实间距问题，再创建后继资格/视图来源；147 已因依赖 135 失败而停用且无 job。134/141 仅在 128 两路实际完整成功后接续。

原始证据：`work/YUZE-LU/121/results/run132-terminal/index.json`、`run135-group-terminal/index.json`、`run148-group-terminal/index.json`，以及两份 `run148a/c-locate-terminal/index.json`。资源调度改善不代表 Block 物理资格通过。

## 159/160/162实际阶段占用补充

159两2CPU探针：1:49、TotalCPU3:09.295、MaxRSS1350256KiB，分配4CPU平均约43.4%；160两16CPU原生最终输出：8:54、TotalCPU34:45.937、MaxRSS41580320KiB，分配32CPU平均约12.2%，其中LEC/原生RCX阶段单任务扩展仍弱。162两8CPU C8全片原生检查：4:22、TotalCPU46:08.830、MaxRSS18331828KiB，分配16CPU平均约66.0%。这是不同任务/阶段的实际资源观测，不能当作同一工作负载的加速比。

后续优先把独立候选/接收子任务装入同一allocation，按阶段线程和实测内存安排并发；有多少真实独立任务才并行多少，不为填核增加无目的参数扫描。132/135/148及以上原结果保留，不修改正在运行作业的线程数或按耗时取消。161按4×8CPU完整接收，134按2×32CPU完整C8物理，141按2×24CPU真实组合；总任务allocation上限仍为8，其他成员不计入且不操作。


## 2026-10-27 17:28 CST 实际终态与后继入口

165/92314实际C8 A/C探针全部11门通过，4:36、TotalCPU7:29.230、MaxRSS4128260K，node25同allocation双2CPU。A45/C29网改动，其中15/4处via9落点；原生upper诊断合并标记A37/C25降至0，完整upper接触0、固定低层/其他网/完整V及源SHA保持。这不是162原raw49/37项的完整GDS接收。166/92326只读严格LEC诊断双1CPU实际通过，0:50、CPU1:20.266、MaxRSS71428K；A/C时序实例143988逐名相同，无新增/删除，A501/C277处DFF_X1变DFF_X2，无字面x/z输入，但尚未证明原生未匹配PI对应，不豁免严格门。141/92256实际FAILED/1:40:06/CPU3:20:52/MaxRSS358556384K，同样被严格C8 LEC拒绝，未完成组合功能。新167准备从实际165接受ODB重新原生最终输出/默认flow LEC/RCX及全片DRT，c96双8CPU，200GiB/路加20%余量；本次提交时尚未运行。T6K161完整接收和164视图通过仍不等于宏边界资格；164 Liberty PG及完整flat timing源另以新版本修正。17:25本任务4个RUNNING allocation（057三路、067）；统一预算基础6/上限8，含PENDING/未知；其他成员未操作。完整P0–P6未完成。

证据：results/run165-group-terminal、run165a/c-terminal、run166-group-terminal、run166a/c-terminal和run141-group/a/c-terminal（均位于work/YUZE-LU/121/）。167采用native_pipeline_c8_escape.json、native-c8-finish-group / native-c8-run-shared109-a/c，保持严格状态边界LEC未通过标志；不启动已知依赖失败的完整接收。


## 2026-10-27 17:44 CST 实际执行

168/92335实际T6K两路typed PG与完整flat timing网表交付通过，0:58、TotalCPU2:54.816、MaxRSS3193048K，node21双8CPU。原始模型保留，VDD/VSS仅转换pg_pin，精确逆变换证明全部其他模型字节不变；实际原生读回power/ground及is_pwr_gnd全部通过。candidate-timing.v严格复制161实际ODB完整信号导出，两路各保留189保护单元并绑定完整proof，旧6_final.v继续保留但不能充当full-SPEF flat源。169/92336用PR128固定5eda23a源只读导出实际ODB占用，node22双1CPU，2:47、CPU4:07.617、MaxRSS3592768K；A453227实例/2229968个master OBS、C451330/2232347；完整占用666023293/664926056字节保留服务器并封存SHA。仅导出通过，独立覆盖/边界资格仍待#127。167/92333仍RUNNING，node20双8CPU，不能先称C8新RC/全片DRC通过。新170准备补查严格C8前后完整图的无驱动使用bit及未使用输出，不改图/日志/严格门，本次提交尚未运行。完整P0–P6及宏冻结/两个新增层产品未完成；登记pending、看板unverified/同步pending、待独立审查。

168/169 group与全部peer终态索引均位于work/YUZE-LU/121/results/run168-*及run169-*；同源交接inventory为t6k-qa127-handoff-168.json，每路30角色，仅索引，独立pack仍需前后hash。

## 2026-10-27 18:22 CST

173/92348组合控制在node22同allocation双1CPU通过，16秒/TotalCPU9.489秒，MaxRSS=0为无有效采样；短任务约29.7%的分配CPU平均占用包含工具/容器启动开销，不是加速比。后继174已部署为双8CPU完整C8接收，按200GiB/路和20%余量预检，受167/172/173实际成功依赖阻挡，尚无job。167双8CPU、172双2CPU继续运行，当前共六allocation。优先并行真实独立候选/激励/验证阶段，保留源/终态和资源证据，不为凑满96核增加无目的扫描。
