# R局部状态宏最终报告：R256与R1024完整验收及实收

核验时间：2026-11-04T02:36:22.521798+08:00。Issue #166 / PR #167。R256/R1024分别完成独立宏原300MHz物理验收、各192项最终功能及本地完整包实际接收。PR待审查，不代表已合并或系统/M11/M12资格。

## 实际实现

状态存储按每lane、每分区16×32bit组织，保留两份状态和8路计算。读地址选择、局部数据和分区汇合分别寄存；各lane选择寄存器在综合及物理实现中保留，局部选择的直接顺序端点上限32，另外审计缓冲树后的总负载、线长和实际周期成本。用分区与寄存边界限制选择网络的作用范围，完成真实物理收敛。

容量参数是每份状态中的32bit元素数量。R256为2×256×4=2048B，R1024为2×1024×4=8192B；容量不包含操作数、流水和交接寄存器。使用普通DFF标准单元存储。

算术及原独立整数参考保留：32bit状态、16bit K/Q、8lane、64bit点积及128bit数值检查/舍入中间量；支持GDN、SSM和四抽头因果深度卷积原执行序列。功能边界及实际所有端口见[r_stream_local.sv](../../../project/rtl/r_local_state/r_stream_local.sv)。128bit装载、128bit状态读回和512bit响应使用原流式协议。外部读为E0接受→E1选择→E2局部数据→E3汇合→E4入队；写为E0接受→E1局部选择/数据→E2提交，同拍读写返回旧值。调用方须按valid/ready及响应事务接入。

输入/输出流水边界的参考来自[OpenTitan prim_ram_1r1w_adv](https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1r1w_adv.sv)，其接口提供可选输入/输出寄存级。普通逻辑存储降为逐字DFF与地址译码的背景见[Yosys memory_map](https://yosyshq.readthedocs.io/projects/yosys/en/0.41/cmd/memory_map.html)。本项目的16行分区、寄存复制/保留、实际布局约束及验收是独立实现和测量；参考项目的资格不作本项目证据。

## 最终物理与功能结果

| 项目 | R256 | R1024 |
| --- | --- | --- |
| 状态容量 | 两份共2KiB | 两份共8KiB |
| 计算 | 8lane | 8lane |
| 工艺/内部层 | Nangate45 M1–M10 | Nangate45 M1–M10 |
| die尺寸 | 1000×1000µm | 1800×1800µm |
| 标准单元面积 | 298093µm² | 778670µm² |
| 原300MHz最终setup裕量 | +10.2522ps | +67.4889ps |
| 最终hold裕量 | +1.91164ps | +0.210554ps |
| setup/hold/cap/slew违规 | 全部0 | 全部0 |
| 详细布线DRC | 0 | 0 |
| 完整原GDS / 准确全die原生规则 | 0 / 0 | 0 / 0 |
| 原独立物理门 | 16/16通过 | 16/16通过 |
| 严格最终LEC及故障对照 | 通过 | 通过 |
| 最终单元网表功能 | 192/192通过 | 192/192通过 |
| 最终资格汇合 | 252，9/9通过 | 744，18/18通过 |
| 本地完整包接收 | 327062766B / 816文件 | 2579966048B / 1693文件 |
| 六文件、所有包成员SHA、实际PNG查看 | 全部完成 | 全部完成 |
| 实际冻结source index | 14份源 | 50份源 |

每版192项均为3种初始化×63项数值以及3项协议。R1024正式证据来自原722数组及723完整汇总，所有用例重新执行；它只复用通过精确字节核验的已编译模型，不复用旧测试结果。提供718最终V与实际编译V SHA均为c7c59ae0560563f317650e729e88bf173b89ca3b5c5c2b7c17508971c8b98ab8；718版图仍独立完成全部原物理门。全部周期和对应300MHz逻辑时间在[实际周期表](evidence/final1024-744/CASE_CYCLES.csv)，不换算成未经测量的完整模型性能。

形式门包括实际全状态ABC映射046/047（D/CK/Q/QN及端口）和最终物理网表严格LEC/负控；信任Yosys降低步骤，不声称通用行为RTL顺序SAT已经结束。原长证明作业保留。

R1024原719分块原生195条诊断及失败回执保留。最终733用准确同源730统一全芯片规则0、全部工具/源码/技术/几何/连接/规则负控证明及完整原GDS0接收，16项原门全部true；没有逐marker筛除。完整约15MB物理原回执已经随包实际接收，仓库的[物理摘要](evidence/final1024-744/PHYSICAL_SUMMARY.json)明确标为derived_summary并记录原件路径、大小和SHA。

734在18项资格检查通过后，因证据文件循环变量覆盖功能回执而打包失败，原件保留。744只将该循环局部变量f重命名为evidence_file，整个AST经名字归一化与原版完全一致；所有验收表达式/阈值/输入不变，完整重新验收、生成源索引和交付包。没有接收734不完整产物。

实际最终工作流另有[39份原文件实收](evidence/final-workflow29/RECEPTION.json)，包括607份自身提交索引、734原失败/744修复及完成记录、723完整功能汇总和未执行743转接745的计划。补充队列及原长证明不作为本交付资格。

本次最终文档执行`python scripts/check_project.py`通过；普通`git diff --check`会将按原SHA保留的Windows原回执CRLF标为尾随空白。保留证据原字节，使用`git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check 4b2c0a14746a0f99c1ce10208f42769289da643a HEAD`检查完整交付差异通过；正文及修复代码的普通差异检查也通过。管理结构检查不代替电路资格，实际电路资格来自上述原物理/功能回执。局部状态组件009覆盖全部地址、部分写、冲突、连续请求、背压及三种初始化；010整机数值/协议通过后再分别接入R256及R1024，最终各自完整布局布线与实际最终单元网表验收。

## 实际交付入口

- [R256完整包](D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-166-r-local-state/.local/166/deliverables252/R-local-state-256-300MHz.tar.gz)；SHA256 5733b1c0c9ed45aba7d8fa9f3edfcd76bc04b8464f7aef3853edb3cc1d7cca55。
- [R1024完整包](D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-166-r-local-state/.local/166/deliverables744/R-local-state-1024-300MHz.tar.gz)；SHA256 d370432b4b236fa80c20551256333d8ca684ea1259d2e8e2a4709271f33978ac。
- [R256原报告](R256_QUALIFIED.md)、[R1024资格回执](evidence/final1024-744/QUALIFICATION.json)、[最终功能原回执](evidence/final1024-744/FUNCTION_RECEIPT.json)、[完整包索引](evidence/final1024-744/ARCHIVE_INDEX.json)。
- [R1024本地实际实收](evidence/final1024-744/LOCAL_RECEPTION.json)、[实际查看回执](evidence/final1024-744/VISUAL_INSPECTION.json)、[六文件索引](evidence/final1024-744/SIX_FILES.json)、[实际冻结源绑定索引](evidence/final1024-744/FROZEN_SOURCE_INDEX.json)。
- R1024包内原始文件约20.96GB，完整包保持压缩形式；六份原生文件v/sdc/def/odb/spef/gds和LEF/Liberty均已单独解出、按原SHA核验：R256位于D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-166-r-local-state/.local/166/deliverables252/native-views，R1024位于D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-166-r-local-state/.local/166/deliverables744/native-views。
- 服务器原包：/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt744/R-local-state-1024-300MHz.tar.gz。

![R1024实际已验收GDS](evidence/final1024-744/layout.png)

这张图来自实际已验收GDS，并已本地查看；图像不代替DRC。Liberty/LEF视图随包，资格范围为独立宏原工艺角和I/O条件，hierarchical_lib_timing_qualified与m11_m12_system_qualified保持false；不是旧ISA的逐拍替换。

正式192项使用16CPU独立任务、cap36动态补位；最终实际节点见原功能回执（node1/15/17），8候选节点均满配，没有因假设内存不足降低并发。补充单线程742仍独立运行，未计入正式192；其尚未执行的743打包计划保留原文件后转接同样修复的745，未改变运行中的742源/脚本/任务或门，也未停止其他计算作业。

协作按rayggxia-project-collab1.0.0：负责人YUZE-LU；业务结果与完整本地交付完成，PR167提交待审查，Issue进入in_review，不标done、不自行合并。management-hub PR5实际读回open/unmerged；登记pending。缺config/board.json，看板unverified、同步pending，管理员/审查人待指定。未改main、PR160、#162/#163或其他任务。
