# Issue19：ACT/MXU 三视图接口与既有连接合同

2026-10-22（UTC+08:00），负责人 Liangruizhi。[Issue19](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/19)／[PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)，依赖PR18/14/12，待审查，未合并。结果对应旧 wave2-06 普通视图，不推广到PR17的新M9 matched宏。

## 实际结论

在显式兼容profile下，**3032个信号位**的Yosys端口、Liberty pin和LEF PIN名字／宽度／方向一致；保留每bit的原始名称、来源行、PORT/RECT、层、微米和DBU。复用Issue7已有685bit连接合同，生成2346个边界网、4694条端点归属。原始输入另外存在**两处Liberty缺分号和四处PG方向差异**，不能称所有视图合格。

| 冻结候选 | 逻辑端口 | signal bit | input / output | PG | Liberty bus |
|---|---:|---:|---:|---:|---:|
| ACT20 | 19 | 860 | 220 / 640 | 2 | 15 |
| MXU20 | 37 | 2172 | 1529 / 643 | 2 | 20 |

八组原合同为ren↔act_ren(2)、r_use↔computing(1)、r_blk↔act_blk(16)、r_blk2↔act_blk2(16)、r_hi↔act_hi(2)、r_grp↔act_grp(8)、r_data↔act_data(512)、r_scale↔act_scale(128)。ACT驱动640bit，MXU驱动45bit；684个私有网加computing反馈网，共685接口连接。computing同时驱动ACT.r_use与父层输出；共享clk由父层驱动两宏。父层40端口、1662bit（input1063／output599）。边界方向检查得到2346个driver、2348个sink，PG不计入信号图。

MXU的done/pf_u共享Yosys模块内bit247；a_addr[30:31]、b_addr[30:31]为4个常量0。保留其逻辑属性及各自物理pin，未把别名/常量合成同一边界网。合同的既有bit相等性证据来自固定上游记录；本轮没有重新做完整父层RTL等价。

## 发现的输入缺陷与未闭合条件

| 证据 | 原始位置与事实 | 本轮处理 |
|---|---|---|
| ACT Liberty | area行139缺分号；140行is_macro_cell | 默认strict拒绝；显式窄兼容profile记录1次恢复，syntax_strict=false |
| MXU Liberty | area行174缺分号；175行is_macro_cell | 同上；原字节及SHA不改 |
| ACT VDD/VSS | Lib行221/226为input；LEF PIN行6892/6909为INOUT POWER/GROUND | 原值并列，direction_match=false |
| MXU VDD/VSS | Lib行694/699为input；LEF PIN行17388/17431为INOUT POWER/GROUND | 原值并列，direction_match=false |
| cmd_t | boundary.sv引用类型，但定义不在此次捕获内 | 240bit宽度取Yosys展开；不声称独立展开完整RTL类型 |
| 实验配置 | external_driver_load_model未指定、phase_lec禁用；synthetic fakeram | 原声明保留，不提升为物理/功能资格 |

兼容profile是liberty-single-cell-interface-area-semicolon-compat-v1，仅接受直接cell作用域内单行普通数字area后、紧邻下一行is_macro_cell:true/false;之间这一种缺分号。其他缺分号／未知接口语义仍拒绝；它是接口审计的明确解析边界，不是修复后的合法Liberty交付物。完整时序原文在原始.lib中，未验证arc覆盖、minimum_period、PG连通或合法信号接入。

## 来源、版本与实际执行

- 输入版本：act-mxu-three-view-wave206-v1；捕获源码 **16be20bfe644e51158279ad69a8983270e81cc00**，工作区清洁；捕获时间2026-10-22 09:40:45–09:40:47 UTC。
- 正式run03清洁源码：**c3916f4f457fcf72fc96f2b2f53ad706e50012e2**。输入未改，运行前后核对源码和快照。
- 从获授权集群wave2-06的ACT/MXU各取boundary.sv、elab.json、experiment.json、output-files.sha256、typ.lib，共10文件 **7,559,708 bytes**；严格known_hosts、路径白名单、单文件/总量上限、前后stat与SHA。仅只读Python，无服务器写入、EDA或Slurm作业。
- 两LEF原字节来自Issue16归档，ZIP SHA为42555df9e5ba32b405b2bc124722d4aea5fec94ef8a874adc37aeaf4020f5bcf。每宏boundary/elab/experiment/Lib/LEF与本次捕获的生产索引比对，共10项通过；生产索引非第三方签名。
- 固定上游合同：PR10 commit2b76f692830a2bdfc157cefb21c3bc1bc91fc409，原文件SHA b1c0ec308e63bd7f20e211c78776f8517a9d01540d899c475dc3217daf73e444。四个elab/experiment预期SHA取自PR17固定commit a01ac5872979338b7d5a7b3ad15685a4f4c15440；运行期间PR17已推进到a3952c9，未替换本轮冻结输入。
- 输入声明RTL commit f237dab2f196855a59a083b1454786df8f01291f；不等于已证明其与网表完整等价。Yosys creator原文为0.68+post，git sha1 UNKNOWN；OpenROAD/ORFS/镜像精确版本仍待核实。
- 本机Python3.13.14，远端捕获Python3.6.8；工具版本、进程缓存路径及源码逐文件SHA见两个manifest。所有临时文件/可指定缓存位于本任务D盘目录。

第一次run在源码16be20bf下因同名capture模块导入冲突失败，尚未创建输出目录；修复提交95dd5d58并加回归。第二次严格run在95dd5d58下正确拒绝真实area缺分号，同样无成功输出。第三次采用显式兼容profile与PG差异报告后完成。两次失败记录保留[validation目录](../../work/Liangruizhi/19/validation/)，未把它们改写为成功。

## 验证和归档

- python scripts/check_project.py：PASS，仅管理结构。
- python scripts/check_research.py：**148项PASS**（17+16+34+81）；含位序、缺位、重名、类型范围、方向继承与覆盖、PG差异、同名模块、严格/兼容语法等检查。
- verify.py：22个索引文件、Git源码blob、原始输入索引、完整成员集合核验及六个业务输出逐字节重放PASS。
- [独立审计](../../work/Liangruizhi/19/audit/audit-run03.json)：**205390项比较PASS**，不导入生产parser，重新读取实际Liberty/LEF/Yosys和连接合同；范围是所选字段/几何/边界图，非完整Liberty语法或物理签核。
- [六个篡改负例](../../work/Liangruizhi/19/audit/negative-run03.json)：修改collector SHA、旧归档SHA、输出缺位、错误Lib行号、错误LEF几何、虚假合法接入结论；重算外层manifest后仍全部拒绝。生产目录未修改。
- 已核对ZIP SHA、解压到D盘新目录并离线重放PASS，23个ZIP成员。归档含原始十文件、两LEF、合同、配置和旧LEF capture，以及本次capture/运行manifest、views/graph/summary/CSV。

归档：[evidence.zip](../../project/experiments/interface_contract/results/issue-19-run03/evidence.zip)，**1,585,317 bytes**，SHA-256 **2d2047b761323ba22e3c209d83a25a89fc77e901beae166103908df72de986d7**。capture SHA：73338bf67196bc075cd363ef947df5fa5b43abe97685f5a7a17e55750d00eb19；run manifest SHA：dd4c0c5f8ec678abcc8dc849cd22966f2e2f0e66ed65b200ea84c70d32e9e154。逐文件索引和摘要在同目录。

独立审计脚本SHA：4712affa87cb4ad8a279f6e5fb4d116ca69b3f6ba3b33c84effeba50bbf64f55；报告SHA：d8c497096d97bc9924bb456887a3377c9ef1b707c6978ad5f3a63cff8d473498。负例脚本SHA：f27e10bb284563a71d4179eec3ff4b296e70d82a6de52daf12a0a72d07ed779a；报告SHA：4440d5ba35a45d08ead377bc558e4227db541161c088ab59a6b5b121a66654ac。

## 对后续Block划分与DAC证据的用途

本轮把“宽接口”落实为可逐bit追溯的真实边界负载：ACT→MXU的640bit与45bit返回通路，并保留computing反馈和共享时钟。这是后续端点映射、外部负载与接口预算的输入；它不能单独证明分离/融合更优，亦不能用普通LEF矩形替代合法access point。

下一步先重新核对Issue15/PR17终态，绑定新matched视图的新版本，处理其实际Liberty语法/PG/时序门槛，再结合DEF方向与工艺via/enclosure/OBS建立合法访问候选。固定映射数K和总搜索预算的端点感知对照仍待这些条件闭合；不把新增有源缓冲的H1对照称为H2冻结底座收益。协作及恢复入口见[交接](../handoffs/2026-10-22-issue-19-interface-contract.md)。
