# PR176 接续研究：已有进展、容量约束与下一步方案

2026-11-04，Asia/Shanghai。负责人 Melodydt；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)。设计基线为 [PR176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176) 的固定提交 `08f2ea20a11dfdd09892a67599163e32b7237edb`；接续分支 `task/179-local-block-continuation`，PR base 为 `task/175-local-block-design`。本轮先交付进度与方案，后续在这个独立任务继续研究。

## 2026-11-04 补充：PR180以两级控制为研究主线

用户明确本人主要负责母控/局控探索，并要求编译器可使用的指令种类和编码。本轮形成[两级控制方案与R0–R7研究步骤](TWO_LEVEL_CONTROL_PLAN.md)、[ISA v0.1](CONTROL_ISA_V0_1.md)及[规范JSON/参考codec](../../project/control_isa_v0_1/README.md)。固定控制归属、宏适配、私有S、真实确认和金属/程序联合绑定均为proposed；本轮仅软件编码与文档交付，不新增RTL或物理资格。下文容量分析保留为控制对象布局的约束。

## 1. 已有研究到了哪里

PR176 已把方向整理为“局部可定制 Block＋两级控制＋各块私有 S”：M1–M10 固定全部有源电路；M11/M12 为研究中的后定制数据/确认路线；模型确定后编译程序和参数。Block 内部主要计算数据连接也允许后定制，有限预连要明确计价。程序 RAM 或真实金属 ROM 都是候选载体，仿真 hex 不等于物理 ROM。

五种候选为 P=M/G/S、U=N/E/S、C=R/G/E/S、F=G/E/S、J=E/S/T。示例池 P×3、U×2、C×1、F×1、J×2，共9块/28个基础宏，候选工作 S192KiB＋T12KiB；局控、端点、holding、程序/参数服务和外部 MEM 另计。数量和容量仍是候选，没有冻结为芯片规模。

PR176 提交了13对 Mermaid/SVG、Qwen3.5 全注意力/GDN、Falcon-H1 双分支/SSM、Granite 40/top8 的七宏和组合双层图；27个有向张量关系的并集只是路线需求。原 PR 的图渲染、来源和文档检查已报告通过，尚未合并；本轮没有重渲染图，也不把图检查当模型实现。

| 证据线 | 本轮读回的实际进度 | 接续研究如何使用 |
| --- | --- | --- |
| main 六叶宏 | main `4b1df2c7` 已有 M/N/E/G/S/T 的300MHz叶宏交付；该清单仍不含新 R | 复用其明确合同，组合/新 S容量/端点另验 |
| [私有S PR178](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/178) | head `a9e874d83fcb56f68a4330bd26db959a861b3fb3`；九实例/九组回归、144KiB、3 feeder，功能验证已交付；P4/N4/N5物理流程仍在进行，无新增合格物理宏结论 | 作为私有化接口依赖，不重复实现仲裁；每块仍16KiB，不能当成P.S32KiB |
| [R PR167](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/167) | head `c97353cfc5ffc222ffa5fddcf9a85499719f9348`；R256/R1024各16物理门、192最终网表功能交付，open/未合并/待审查 | 更新“R研究一概未完成”的旧时点说法；不把独立宏资格转给本组合，适配后的事务/延迟仍须核对 |
| [控制 PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152) | head `55243d2c58626547d0d452bfb25fa79b7499b486`；真实G1 A→F→F、真实S ACK和终态保持切片，89项不同定向检查；整体L5/G2/G3/完整质量未完成 | 复用真实确认经验；旧固定岛边界和有限A/F图域不等于本开放图/新局部粒度 |
| [控制与物理 PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163) | 本轮最新任务说明仍明确完整组合零冲突路由和300MHz三档RC联合验收未通过 | 保持原任务独立，未来只接收固定版本和完整证据 |

这张表是对在线说明、固定来源和元数据的核对，没有在本轮重新验收原服务器大包或检查实时作业。相关来源索引见本任务辅助资料。

## 2. 第一轮容量核算揭示的约束

[机器可读结果](continuation-capacity.json)采用S16紧凑打包的payload下界；位宽/对象形状来源于[原设计](../LOCAL_BLOCK_DESIGN.md)与[组合图册](COMPOSITE_MODEL_FLOWS.md)。这些数值不包含bank冲突、协议/地址状态、holding、对齐及实际适配器成本。

| 同时驻留假设 | 容量 | payload | 剩余 | 推论 |
| --- | ---: | ---: | ---: | --- |
| Qwen P：完整input＋gate＋up | 32KiB | 41KiB | −9KiB | 不能同时全存，必须安排分片/消费顺序 |
| Qwen P：input＋一份完整gate或Mid | 32KiB | 23KiB | 9KiB | 仅保留对象可放下；up/输出窗口仍需分配和验证 |
| 同上放在PR178当前S | 16KiB | 23KiB | −7KiB | 当前私有化实现不能直接承接这个驻留方案 |
| Qwen P：input＋512元素gate/up/Mid各一片 | 16KiB | 8KiB | 8KiB | 是可调查的局部窗口；不证明完整FFN可运行 |
| Qwen P2：一份完整Mid | 16KiB | 18KiB | −2KiB | 即使上游分片，down端仍需32KiB或明确重放/外存方案 |
| Qwen F0：context＋gate | 16KiB | 16KiB | 0 | 必须明确读前覆盖/原地消费和额外holding位置 |
| Falcon J0：X＋Attention＋SSM | 16KiB | 15KiB | 1KiB | 汇合窗口紧，双支进度与返回保持需逐片验证 |
| Granite P2：八份S16专家返回＋权重 | 32KiB | 24KiB＋16B | 8176B | 仅对统一尺度S16候选成立；S32返回需重新核算 |

关键区别是“局部窗口放得下”和“整个任务能前进”。例如512片段使P0局部payload降为8KiB，但P2的M只有一份完整累加上下文。若down先只算8个输出通道，它需要后续通道能重新读取全部Mid；必须声明Mid保存在32KiB私有S、显式MEM，还是重算及其代价，不能藏在测试平台数组或额外未计价缓存里。

Qwen GDN约2MiB/层、Falcon SSM约4MiB/层的状态也不能由C0.S或R的小状态块容纳。必须定义外部MEM的old/next与分片导入/导出；R本地COMMIT不等于整个token的原子提交。U的Softmax原始值/EXP回放实际格式和重叠窗口尚未核算，不凭S16输入推断所有回放都是2B。

## 3. 对当前方案的判断

P/U/C/F/J适合作为下一轮研究起点：保留矩阵、统计、函数、状态和交接的局部性，同时让Qwen的归一化回路、Falcon双支汇合、Granite动态专家返回形成可比较的路线差异。当前证据不足以选定最优粒度、32KiB S或预连比例。

优先检验两个风险。第一，容量、bank/feeder争用和回放可能抵消局部性收益。第二，为覆盖三模型而预制的驱动、端点、选择器和控制存储可能比共同固定互联更贵。静态有向关系23/18/15或并集27不能直接换算线长、面积或性能收益。

研究期间保留9块候选池作为共同起点；容量对照中若比较16/32KiB，分别成为明确的资源版本。正式同资源比较时必须在每个版本内固定同样实例、容量、摆放、有源库存和数值函数，再比较产品特定后制路线与共同固定路线/有限交换。不能给后制方案更大S或更多驱动后宣称是金属定制的收益。若需要有限选择器，必须在共同有源库存中预先计入；不同硬件预算的比较另列为架构对照。

## 4. 后续研究方案和验收门

| 阶段 | 要完成的具体研究 | 可接收的证据 |
| --- | --- | --- |
| A：完整合同与资源账 | 对每个对象列shape/格式/尺度/RNE/饱和、S字布局/bank、生存期、TX/RX/ACK/holding归属；列全部宏上下文与程序容量。先比较Qwen dense FFN的32KiB驻留与16KiB显式分片/重放 | 逐事件资源账、实际原生端口适配表、数值参考、无隐形存储；无法映射时给出具体拒绝原因 |
| B：有界可执行切片 | 先打通Qwen FFN的M/G/E/S与残差交接，再做Attention；随后分别进入GDN/SSM与动态top8。每步复用已接收版本，不把协议peer当完整计算宏 | 真实目的S写确认后才释放源；背压、单上下文、fork/join、非零旧状态、连续job、错误/复位、饱和/tail等有正负例及固定源码/数据SHA |
| C：程序与路线联合生成 | 从合法IR生成有限程序、对象地址和静态端点绑定；未知于预制时的新合法小图也能编译；非法格式/容量/不可达端点明确拒绝 | 相同RTL换程序/参数执行，程序可装载/验证，不能只按模型ID选择三份完整表；代码容量和装载开销计入 |
| D：同资源物理对照 | 在冻结的同一资源版本比较①三模型特定M11/M12产品路线②覆盖三模型的共同固定路线/有限交换③必要的有限预连比例；产品同时覆盖自身所有层型，Qwen不能逐层重布金属 | 逐根数据/ACK/控制接入；完整P&R/PG/几何、M1–M10不变、300MHz setup/hold/电气及声明RC；线长/通孔/驱动面积/总延迟/带宽/能耗有真实测量及失败记录 |

这是分阶段研究门，不预设所有候选都会通过。若A暴露能力不足，应选择明确的合同适配、局部资源调整或重排方案，再以新版本验证，保留原始失败。新物理/服务器实验开始前先读取远程规则，并按仓库要求给出提交、RUNNING及终态回执。

数值方面有三项优先决定：Falcon注入舍入顺序与B/C位宽、Qwen/Falcon运行时系数表的域/步长/容量/误差、Granite统一S16专家返回的真实质量。当前G没有通用EXP，E没有任意S32/S64归并，不能用图中的算子名掩盖这些能力缺口。原[差异表](SOURCES_AND_GAPS.md)保持有效，R新物理结果不会自动消除数值差异。

## 5. 本轮实际验证与恢复

容量核算只用Python标准库，命令从仓库根运行：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B work/Melodydt/179/analyze_capacity.py
python -X utf8 -B work/Melodydt/179/analyze_capacity.py --check
```

首条仅检查管理结构，后两条生成/核对8项payload下界和资源池汇总。生成结果绑定输入与脚本SHA；没有执行新RTL、模型推理、服务器或EDA，也没有创建自动监测。本轮先向用户介绍进度和方案，后续在本任务接续，不把聊天结束当研究完成。

[任务资料](../../work/Melodydt/179/README.md)与[可执行交接](../handoffs/2026-11-04-issue-179-local-block-continuation.md)区分本地API资料、远端分支及main。Issue保持in_progress，Draft PR供后续研究。登记PR5 pending；缺board.json与Projects条目/字段工具，看板unverified/同步pending，管理员待指定。
