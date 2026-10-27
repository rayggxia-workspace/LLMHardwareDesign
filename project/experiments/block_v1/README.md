# Block v1 执行入口

当前物理边界唯一为 **M/V/R/S/T**，每种一个基础实现。`five_macro.py` 提供完整 M 和独立 S 的功能/完整映射任务；`five_macro_physical.py` 在各自前置通过后跑最终原生流程，独立完整接收仍必需；`five_macro_delivery.py` 从选定 T6K C 的实际 ODB/GDS 导出接点与图。旧 `make_library.py` 的裸 M8 / 混合 VS 仅历史试验，不能作为最终宏。

M 的独立参考为 `test_matrix_macro.cpp`（含S8/S16、P15样例、全K上界、跨组/RNE/背压/守卫），S 为 `test_store_macro.cpp`（全地址、随机读写、响应占用与reset保留）。V/R新 RTL 及三者的新最终物理接收均继续实施；文档规格不等于功能已实现。

本轮用户范围纠正：以[首版积木实施计划](../../../docs/plans/block-v1-library-implementation.md)与[物理清单](../../../docs/BLOCK_LIBRARY_V1.md)为主线，必须完成每个入选块的最终M1–M10布局布线。下文旧P0–P6/十二层工作是保留的历史工程入口，不再全部属于本轮验收。

Refs #121；授权计划见 `docs/plans/block-v1-nangate45-m11-m12.md`，进度/输入证据见 `work/YUZE-LU/121/`。

只用Nangate45原生M1–M10做预制，新增研究M11/M12和via10/11做定制互联。有源和原生几何冻结后不允许repair新增或移动单元。

本目录当前实现P0/P1的一部分，不是已完成物理Block库。

## 本地输入与生成

```powershell
python scripts/check_project.py
python project/experiments/block_v1/import_sources.py .local/issue121/upstream/selected109.zip work/YUZE-LU/121/source-manifest.json --root . --receipt work/YUZE-LU/121/source-import.json
python project/experiments/block_v1/make_wrapper.py --check
```

源包从原冻结发布路径读取，完整身份固定在manifest，不能换用当前活动目录。生成器保留33份原始依赖，wrapper生成物入Git，可直接审查RTL。

## 协议

transaction6k只有一个消费者引用，不提供隐含多读者。begin必须1..384个128bit word，index从0连续写；错误index不消耗且sticky error。填满SEALED后才能commit；commit前revoke优先，commit后revoke无效。读是同步两阶段，每拍保持到take；最后一拍被take后才能release。release握手前拒绝新begin；协调硬reset可以清控制，不初始化RAM。

shared121将原result接口改为**已提交**数据流；原软件driver需要适配，不能直接把旧provisional检查器当新顶层验收。candidate_ready仍供上游accept/reject；accept后必须等core的root ACK/DONE才发布T；core DONE ACK在T引用释放前被阻挡。M/A失败、R/G reject和可取消abort撤销尚未提交T。

## 服务器

计算任务由 `dispatch.py manifest.json --submit` 一次调度pass提交，后续不加--submit则只采集/保存状态；Python3.6兼容。manifest在run创建后不可变。所有run位于同Issue根下，共用预算锁，默认六槽，elastic最多八槽；每task一个node allocation。任务名yzl-bv1-*，按本任务状态计槽，其他账号作业不受影响。未知sbatch结果不会盲重试，须凭comment核对再恢复。

当前集群RealMemory=1占位，manifest使用--mem=0保留节点内存，按/proc/meminfo和MaxRSS实际核算；不以1MB配置推断实际容量，不修改集群配置。worker按实际SLURM_CPUS_PER_TASK限制编译/工具线程。串行映射申请1CPU；仿真编译按分配并行，节点内回归分片后续按RAM装箱。

worker模式：transaction（独立队列scoreboard）、map-s16k/map-t6k/map-c8-full（存储完整映射，不blackbox）、core-build（原基线binary构建＋新wrapper lint）、overlay（几何生成及OpenROAD/ODB读回）。每模式保留命令、输入输出SHA、日志、失败和returncode；最后三项并不替代新顶层完整数学回归/DRC/提取。

early RC文件是显式参数估算，**不是**覆盖12层的OpenRCX规则。未完成提取校准和全层几何检查前，P1技术验收保持未完成。

校准场景的 `pattern-prepare` 模式逐路径读取真实 DEF 和 ODB NDR 宽度；信号及 cntxM 上下文同场保留。`reference-pilot` 在已验证独立求解器上并发求解每个 family/目标层和最大上下文，保存选定 master 的完整 Maxwell 行及统计误差并检查互易性；该先导不替代全量校准或正式模型。具体范围见 `docs/decisions/2026-10-27-block-v1-calibration-scenes.md`。


2026-10-27增量：完整上下文候选拟合后实际留出仍有跨层耦合缺失，版本2.0/2.2/2.3均未合格。`fv-install`、`fv-case-N`、`direct-view-N`另验证直接场解路径：六种小几何经独立有限体积、SPEF读回及GDS核对全部通过，完整Block分布式提取尚待完成。依据和严格适用范围见 `docs/decisions/2026-10-27-block-v1-direct-field-extraction.md`。`odb_geometry.tcl`按实际路径/过孔导出导体，不将OBS当金属；尚未支持的实例pin/特殊线显式拒绝。
