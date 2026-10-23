# Issue #55：完整案例集成阶段记录

任务：[Issue #55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，负责人 huangpingyang04-lgtm。分支 `task/55-full-block-integration`；阶段一状态为 pass_with_inherited_issues；首次精选交付正在准备，本任务PR尚未创建。当前没有冻结底座版本，尚未消耗主要底座候选轮次。

服务器根目录（下文所有相对证据从此开始）：
`/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z`

## 范围与输入

采用完整 openTPU `otpu_asic_top` small 与 `llaccel_core`，资源并集。完整 llaccel 的16个外部SRAM bank/DRAM/主机参加测试但不计核心物理面积；openTPU 内部存储不得遗漏。已有ACT/MXU/GEMM/VECTOR加后续辅助分区共同覆盖原设计，ACT+MXU合并版仅为替代输入。

主方案 M1–M8 固定、M9/M10 定制；必要迁线在派生副本且固定原单元和逻辑。报告是结构入口，不能从图片重建数据库。本次ACT/MXU选用团队Issue15更新的m9-act-03/m9-mxu-03；其实例数与10月22日HTML旧快照不同，版本没有混用。GEMM/VECTOR沿报告引用的Issue7版本。

原RTL版本分别为 `f237dab2f196855a59a083b1454786df8f01291f`、`f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5`。仅核验实际使用文件，未声称整个源仓库干净。OpenROAD显示unknown版本，使用ELF SHA标识；Yosys为0.68+post。详情和工具SHA见输入清单。

## 阶段一：完整清单与原始基准

实际完成：
- 原构建/文件表/完整顶层与21项源码归属前沿已记录；两完整顶层成功展开，包含全部辅助模块，叶单元及状态/内存归属留有逐项索引。
- 四个宏的完整原生库存及独立一致性核对通过，检查真实端点、变换后的pin和via盒；未发现未连接的输入或PG引脚。已有未用时钟负载输出保留。
- llaccel补充seed0/2，各30次连续启动，各60项检查通过；既有seed1和其他有效历史回归复用。此种子变化数据/形状，原DRAM服务延迟不变。
- open新增观察器实际20例通过：8个原stall控制对照+4个既有程序×seed0/1/2。每例完整256KiB输出对照；独立复核87,160行公开接口trace。含DMA/VPU、QUANT/MXU/VPU、rinit及预期WAIT超时。预期报错案例不是被隐藏的失败。
- open展开需opt_expr/opt_clean消除前端临时反馈；原始中间状态完整保留，89968已归因：442项原图无模块输出路径、1项在受限二态常量化后无输出路径、6项保留状态端口表达式一致；8项检查器测试通过。不是已完成原RTL完整形式等价。

| 核心Block | 尺寸μm（正方形边长） | 全部实例 | 信号位 | 当前定制层内部占用 |
| --- | ---: | ---: | ---: | --- |
| ACT | 326.205 | 16,178 | 860 | M9：69网 |
| MXU | 1100.455 | 441,518 | 2,172 | M9：11网 |
| GEMM | 1157.32 | 571,780 | 3,753 | M9：47网；M10：3网（不能直接相加当唯一网数） |
| VECTOR | 1148.52 | 733,546 | 2,246 | M9：40网 |

原时序证据：ACT/MXU/GEMM已有setup/hold满足各自边界预算；VECTOR setup最差−4.16659ns、59项电容违例，均为输入遗留。当前没有新RC/STA通过结论。四宏9031位端口不等于每周期有效吞吐。

证据索引：

| 产物 | 路径 | 实际作业 |
| --- | --- | --- |
| 原始输入、Block目录 | runs/catalog-01/{input_manifest,block_catalog}.json | 89960 |
| 源码、基准、归属 | inputs/{rtl_inventory,baseline_evidence}.json；deliverables/coverage_map.csv | 89950 |
| 原生库存 | runs/native-{act,mxu,gemm,vector}-01/ | 89947/89949 |
| 独立库存审查 | runs/stage1-readonly-01-driver/ 与 runs/catalog-and-reviews-01-driver/ | 89950/89960 |
| 原完整顶层展开 | runs/hierarchy-opentpu-04/；runs/hierarchy-llaccel-03/ | 89961/89958 |
| llaccel补测 | runs/baseline-extra-01/execution.json | 89956 |
| open观察器编译/实际回放 | runs/open-observer-compile-01/；runs/open-observer-replay-01/ | 89963/89965 |
| open独立复核 | deliverables/open_observer_89965_independent_review.json | 原结果只读复核 |

完整展开不是完整功能证明。原RTL回归的有限输入、二态模拟和FakeRAM模型边界继续保留；阶段二将使用相同输入检查实际集成DUT及握手/公开状态。

## 阶段二：补齐分区和完整集成

尚未通过。已定位未分块逻辑：open的VPU/QUANT/TMEM/SEQ与IMEM/DMA/collective/顶层剩余；llaccel的ATTN/DMA/命令控制/XBAR/DRAM仲裁/性能状态/顶层剩余。先保留全部逻辑形成可追溯辅助分区，再依据接口作物理划分，不增加流水、不缩减容量。现有物理核心与原RTL边界替换还需功能对照。

## 阶段三：迁线、接入、布局和冻结

尚未通过。ACT原始69目标网已通过几何连通和目标对全部邻近导体短接检查（89966，含12项检查器夹具）；原生FIXED导入及几何完全不变资格通过（89964）。迁线89967已结束并验收失败：单元/连接/非目标线路/PG/pin精确不变、M9/M10导体清零，但独立检查发现43处异网形状接触；路由工具自身最终报告1项short。该新引入的失败必须修复，不能归为继承问题或因工具完成就接受。43是形状接触对数，不代表43个独立故障网络。

引脚仍位于M5/M6。固定M8接入尚未实现；M9 via落脚比原pin宽，必须真实扇出，不能只改LEF层名。共同PG/clock/布局/冻结均未完成。

## 阶段四：同底座两案例定制与验证

尚未执行。没有共同底座上的最终布线数据库、完整集成回归、寄生/STA闭环或两案例独立读回通过结论。

## 失败与下一步

此前脚本适配失败保留：89948命令路径、89952/89953作业环境、89954/89955Yosys文件引号、89957前端临时反馈、89959DEF记录缩进、89962NETS导入模式。它们不应标成已通过物理实验；修正使用新版本、新运行目录。

89970已核对两例实际-G参数、锁定SV绑定/默认值及端口/生成分支，补充证据而不伪造工具未导出的参数字段。89969只读导出四宏各20条实际track pattern，无probe缺项；不代表引出已实现。

下一步精选上传阶段一到同一任务PR；同时推进辅助分区和ACT迁线资格。真实底座版本形成后再开始完整定制布线。需要的新辅助物理视图、M8接入、统一PG/时钟仍是本任务待实现输入；正式团队Block和M11/M12真实参数并非本轮主方案前置输入。

登记pending（管理中心PR5待合并）；Projects unverified、同步pending（缺config/board.json和已验证能力）；审查人待指定。Issue保持in_progress，不自动合并。

阶段一追加证据：runs/cleanup-opentpu-review-01/（89968）；runs/parameters-{opentpu,llaccel}-01/（89970）；runs/access-{act,mxu,gemm,vector}-01/（89969）。机器摘要与关键SHA见正式代码results/summary.json；失败和后续阶段不因本阶段通过而改为通过。
