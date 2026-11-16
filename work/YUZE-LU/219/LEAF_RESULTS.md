# 原生叶宏配方、状态租约与五类混合计划

2026-11-07 CST；[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [Draft PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。这是 #220 编译器的后续实现，未修改其他任务的 RTL、控制器、物理结果或主工作树。

## 已实现

| 能力 | 编译器实际产生什么 | 证据边界 |
| --- | --- | --- |
| M 常量权重矩阵乘 | 显式离线B布局；沿K装载/Execute，首片clear、后片累加，末片ReadFinal；同一累加状态不迁移 | S16原生指令；最终右移0–63实测检查；动态B布局尚待实现 |
| G 激活/门控 | SiLU、Sigmoid、GELU、Softplus及gated SiLU，按实际两lane格式分片 | 四函数×门控开关，每配置97组实际RTL数值对照；P现有适配只登记gated SiLU |
| 紧凑E及格式处理 | 同形状Add/Sub/Mul；实际左右移、S32→S16 RNE/饱和 | 13种原生op×32个shift×37组数据；op13另用独立宽度/舍入参考 |
| 流式N | Begin/Stats/Finalize、EXP/FinishExp/Replay或NormReplay；原始输入和EXP可正常spill/reload | 统计上下文贯穿全行，不做逐片Softmax/RMS；已有2048行原生证据另保留 |
| R256 GDN | 衰减/预测片→全局误差→更新/查询片→最终读出；状态片显式回S，跨片dot/update留在同一R | 使用实际默认WORDS=256，不扩大成R1024；1–32、33、64、127、128、256行的全八lane状态及输出与完整参考比较 |
| T | Begin、逐字Write、Commit、Take、Release | 1/2/8/32/384字、背压与lease；拒绝0/385/1023非法长度 |
| 持久宏状态 | `state_groups`生成M/N/R的独占状态区间；等待内存也不得覆盖、迁移 | 初解、CP、独立检查器均纳入；覆盖DP不吞掉状态边界 |

M的`ReadFinal(width=16)`仍返回四个S32槽。本次没有把它当成紧凑S16：另生成E op13并计入时间、S和连接需求。格式以`bits/exponent/lanes/unsigned`明确表达；整数ONNX通过metadata带入，dtype/位宽/符号必须一致。FLOAT不会被直接重贴成整数。权重布局是显式离线工作，运行时换lane/打包没有规则时拒绝。

`leaf_catalog.py`按传入的宏实例、容量、IO和实际测量生成服务，核心求解器不固定五类数量或模型名称。`operations`可限制某个既有适配器实际提供的服务。计划IR包含原生命令、局控归属、状态组、输入/输出地址和完成事件；尚未称为MC/LC机器码。

## 服务器实际结果

最终三个作业均在c64、本人`yzl-*`名称、8核分配、UNLIMITED下`COMPLETED 0:0`。

| 作业 | 冻结目录 | 实际检查 |
| --- | --- | --- |
| 99949 | algorithm-fix-38-final | M/N/G/紧凑E/R256/T原生命令数值、状态和时间，三初态一致 |
| 99948 | algorithm-fix-37-banks | 实际P/非P 16KiB SRAM及原银行模型；四银行首尾地址三初态读写一致 |
| 99950 | algorithm-fix-39-final | 46项算法测试；五类混合图自动编译；生成命令三初态回放；真实完整Qwen2.5-3B重检 |

混合图的主链为`N归一化→M矩阵乘→G激活→E残差→T交接`，并有`R256分四片处理128行状态→E宽度/尺度转换`。最终38项任务、4组跨命令状态、7份分片输出，与独立完整算子参考一致；全部五类控制分组实际被使用，选中P.M/U.N/F.G及C/F/J的E、C.R、J.T。

每组私有S仍是实际16KiB。独立地址/生命周期/ACK检查通过，峰值为U96B、P208B、F48B、J32B、C2880B。计划10,446模型周期、386个128位外存传输字，16组逻辑宏读写通道，数据预连0。块间在该保守配置中经虚拟外存中转，未声称直接宽总线的性能收益。

730项去重时间配置来自实际探针。这里S读/写均3周期，边界是**普通叶宏请求/响应**；此前4/6周期属于U组客户端边界，不能互换或据此宣称提速。服务时间由实测叶命令加实测S访问串行组成，标记`integrated_lc_timing_qualified=false`；外存为#182来源的有限资源虚拟模型。各宏单独时钟的数值回放时间未被当作全系统周期。

两轮CP邻域均UNKNOWN，保留独立检查通过的初解，本次没有算法收益或全局最优结论。宏状态约束已进入邻域：开放R的某个阶段时会同时开放其整组状态任务。0.6B和假设FP32硬件不进入本轮证据。

## 输入、结果与失败记录

- [交互图册](results/leaf-v1/generated/report.html)：输入图、五类独立资源、计算/搬运/状态时间轴、原生命令和地址。浏览器本地file协议被策略拒绝，本轮视觉验收未执行；不绕过该限制。
- [完整结果](results/leaf-v1/generated/result.json)、[源核验](results/leaf-v1/source-verification.json)、[输出与来源SHA](results/leaf-v1/receipt.json)、[Slurm终态](results/leaf-v1/slurm.psv)、[46项检查](results/leaf-v1/tests.log)。44份LF规范化执行源与本次提交内容绑定；输入RTL另外逐文件核对。
- [完整3B覆盖](results/leaf-v1/full-audit/coverage.json)：ONNX哈希`0950df534497881f416a3f8b8fac1a265764ea2f4879943695a2d800a5c9158f`，2,277运行时节点、253离线布局；未改变此前3,085,938,688参数、36层及HF/ORT前端资格。
- 失败尝试保留在[回执](results/leaf-v1/receipt.json)和failures目录：依赖遗漏、驱动数组符号、已有lint路径/诊断、R驱动首次ready地址未初始化、SRAM延迟模型未指定timing、C++命名冲突和新增测试字段错误均未改成硬件缺失。99947的新测试字典访问已修正，最终46项通过。

`native_t_lint.vlt`仅限定既有T两个数组索引诊断的源行；非法长度和最大384字实际回归，未修改T RTL，也未全局关闭宽度检查。S银行交织为地址低2位，最终验证各bank的地址`bank`和`1020+bank`；此前按高地址划区的探针仅触及两个bank，最终99948补齐四bank。

复现根目录`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/`。`launch_fix.py`冻结到新目录，依次使用`native-probe.sbatch`、`native-sio.sbatch`、`leaf-replay.sbatch`；绝对依赖路径在脚本/输入SHA中记录，参考#198目录只读。`collect_leaves.py`核对终态、收回轻量结果并验证SHA，原始大数据留服务器。规则、依赖和入口见[实现说明](../../../project/experiments/block_synthesis/README.md)。

## 整网尚未完成的精确范围

完整Qwen2.5-3B首次停在词嵌入`Gather`的转换。FLOAT到原生定点格式的实际量化策略、动态B矩阵的运行时布局、位置编码/图重排及其余整网规则也尚未全部实现。当前规则支持声明的原生整数图，不能声称任意3–4B模型已可整网综合，更不能用本混合测试代替完整LLM对照。继续工作首先应实现Gather到现有虚拟外存的取数规则和真实量化/布局前端，然后再验收完整模型计划。此处没有发现缺控制器、必须预连或16KiB不够的证据；机器码、真实DMA和物理验收仍不作为本阶段算法前置条件。

本次按rayggxia-project-collab1.0.0交付；Issue保持in_progress，PR Draft，审查人待指定，未合并。项目登记management-hub PR5 pending；无config/board.json且Projects权限待处理，看板unverified/同步pending，处理人待指定。
