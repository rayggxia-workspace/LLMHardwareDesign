# Issue173：FIFO直供M的实际服务器交付

## 2026-11-03 22:44 CST物理补充

- [500/300MHz完整物理流程与结果](../../../docs/DRAM_M_FIFO_PHYSICAL_RESULTS.md)、[精选证据索引](physical-evidence/evidence-index.json)、[全部原件路径/SHA](physical-evidence/raw-index.json)。原首次RTL内容和47原件保留如下。
- 最终P&R96364/node1/16CPU，28分40秒；独立STA96378，1分13秒；最终单元网表96377，7分26秒，均自然COMPLETED0:0、UNLIMITED。DRC/setup/hold/电容/转换违例均0，最终393矩阵及坏数据拒绝通过。
- 实际执行源、源码/库/网表/二进制SHA及继承CTS检查点在各回执中可核对。正式报告与gate使用同一最终Verilog SHA a25b4f3c…；全部实际物理数据留本人全新授权目录。只撤回尚未启动的32核资源请求后改16核；调度原件保留，未停止运行中的正常作业。
- 采集501项轻量原件/派生摘要逐一SHA核对，上传162个证据文件/索引；大ODB/DEF/SPEF、连接/端点大表及剩余原件留服务器并索引。失败实现20hold/26cap、只修hold后23cap、启动诊断一并保留。
- [本地证据核验](physical-verification.json)及[可复核脚本](verify_physical_evidence.py)：所选原件SHA、三视图数值/计数一致、最终网表与物理/STA绑定、时序属性单位、原M Git blob、源代码和新增链接均核对；这不是替代服务器硬件验证的测试。
- 项目管理检查与硬件验证分列；本次仅Nangate45 typical用户读接口后通路，不含实际DDR/PHY、多PVT、模拟MTBF或整机资格。成果待独立审查、Issue in_review，登记/看板缺项及审查人待指定沿用下节回执，不自行合并。

## 首次RTL交付原记录

- 任务：[Issue173](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/173)；成果：[PR174](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/174)；负责人huangpingyang04-lgtm。
- 分支：task/173-dram-m-fifo；main基线4b1df2c7；执行源aae9a51f015df96e2140a99f59aab483b5ba1f04。
- [结果总结](../../../docs/DRAM_M_FIFO_RESULTS.md)、[接口及复现](../../../project/experiments/dram_m_fifo/README.md)、[原件索引](evidence-index.json)。
- Slurm96226/node1/8CPU自然COMPLETED0:0，18/18测试、2340正确矩阵、两个数据破坏负控制拒绝。源码7项、构建及运行日志、下载包SHA核验通过，M Git blob保持。启动失败与修复原件一并保留。
- 正式源和实验分别放project/rtl/dram_m_fifo、project/experiments/dram_m_fifo；原main M仅作冻结输入，不在本PR改动。外存是用户读事务模型，非DDR器件/PHY；没有S、没有完整AXI D/C控制链，不宣称物理CDC或PPA资格。
- 实际运行使用项目既有SIF和Verilator；只在本人PingyangHuang全新任务目录写入，不覆盖已有数据，不操作他人作业；主线文件/PR172保持。
- 本地验证：固定main管理输入最小快照执行python -X utf8 scripts/check_project.py；独立核对源/日志SHA、18组参数覆盖、数值案例总数、负例、所有新链接与代码空白。管理检查不代表硬件检查，未执行本地硬件仿真。
- 大编译产物和完整运行目录留服务器，仓库保留47份轻量原件及索引。Slurm终态和最终PR/GitHub逐文件读回证据见PR回执，PR待独立审查不自行合并。
- 下一步：独立审查本RTL与合同；如需实际DDR/AXI、多个在途或物理实现，按相应接口补齐并独立验收。

规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design。登记沿用management-hub PR5 pending；本次固定main树无config/board.json，已读status-mapping，无Projects条目能力，实际看板unverified/同步pending、管理员待指定。审查人/优先级待指定。业务结果形成可审查交付，Issue提交后in_review，不提前done或自行合并。
