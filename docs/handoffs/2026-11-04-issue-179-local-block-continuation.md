# Issue179：局部Block接续研究与协作欠项

2026-11-04，Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)，负责人Melodydt。优先级/审查人/Projects处理管理员待指定。

## 16:25 CST 综合方案交接（优先恢复此段）

当前发布前源码基线 d6429607d5e0f607c321ab6372e78d5f53ec96ba，tree f7a1826fee23c24ed8d939f2325961e059e44257；任务 task/179-local-block-continuation / PR180，base 仍 task/175-local-block-design。最终新增 commit／CI／原文核验由在线 Issue／PR 回执记录，不伪填自引用 SHA。

本轮成果为[综合方案 v0.2](../local-blocks/TWO_LEVEL_CONTROL_PLAN.md)：Block 组成、四类连接、ISA／程序装载执行、最新进度及下一步；ISA v0.1 编码和代码未变。局控到宏固定预连、主机统一装载器仍为 proposed；宏级断电暂缓。

工作目录为 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-summary-d642960/delivery，是新独立部分 API 快照，无 .git／HEAD／index，不能称本地 Git 已提交。发布前改动仅本轮白名单；旧 control-plan-1f3e916/delivery、179/delivery、151 包保留。远端基于固定父树仅更新本任务文件；上传／原文核验结果以 PR180 回执为准。

实际检查和摘要见[control-summary-validation.json](../../work/Melodydt/179/control-summary-validation.json)，在线 PR 元数据／说明快照及固定文件版本见[control-summary-sources.json](../../work/Melodydt/179/control-summary-sources.json)。PR178／163 的最新状态仅按核验时的报告记录，不是服务器实时作业读回；没有新增服务器作业、节点、日志／结果目录或自动监测，没有停止原任务。

恢复第一步：Melodydt先核 Issue179／PR180 最新 HEAD、评论及分支，核本轮来源／产物 SHA，再在上述 delivery 运行管理结构、容量 --check 和 codec 的现有 8 项测试。随后 R1 交付资源／原生 ABI 注册、固定控制网与后制端点清单、镜像与配置装载接口、16／32KiB 对象生存期；再 R2 有限二进制解释器。

登记 PR5 已读回 open／未合并，pending；本任务头 config/board.json 仍 404，status-mapping 已读，但无 Projects 条目／字段工具，条目 unverified／同步 pending。管理员待指定，需核实际卡片、Project ID、Status=In progress、Priority 待指定并读回；未因本轮结束聊天而标 done。审查人待指定，PR Draft／open，研究 in_progress。

下方早前两级控制／容量交接为历史记录；路径和当时进展保留，不代表当前本轮工作目录。

## 本轮更新：两级控制与指令编码优先

用户明确主要负责母控/局控研究，并要求后续模型编译能使用的指令种类与编码。现交付[方案/研究步骤](../local-blocks/TWO_LEVEL_CONTROL_PLAN.md)、[ISA v0.1](../local-blocks/CONTROL_ISA_V0_1.md)及[参考工具](../../project/control_isa_v0_1/README.md)。24操作码/9类记录和软件编码工具已形成；完整镜像装配、native参数注册、语义编译、执行解释器及新RTL/物理未完成。R1–R7仍待执行，不因文档/编码通过标done。

本轮基线commit1f3e916ed5c40fc54a0e7af90c675017c87317e4/tree0beb612ccc0dacc350e1ab5765b583efdf1fe324，仍通过PR180和task/179-local-block-continuation交付。新的独立本地API目录为D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-plan-1f3e916/delivery，无.git/HEAD/index，修改均为发布前工作文件而非本地Git提交；最终远端SHA见PR/Issue回执。旧179/delivery与151包保留。

恢复先读取Issue179/PR180最新HEAD和评论，核本轮来源/验证索引，再在新目录运行管理结构检查和project/control_isa_v0_1/test_codec.py。随后开展R1：真实宏/私有S端口与native字注册、程序/描述符容量及地址/资源/拓扑检查。容量下界旧研究继续约束S布局。没有新服务器作业、节点、运行日志或结果目录；这些项目为未启动，不取消其他任务，无自动监测。后续服务器实验先读远程规则并按启动/RUNNING/终态回执交付。

[本轮来源](../../work/Melodydt/179/control-plan-sources.json)及[实际验证](../../work/Melodydt/179/control-plan-validation.json)随白名单提交；没有重验PR178/167/163大包。登记PR5仍open/unmerged，pending；缺board.json/Projects工具，看板unverified/同步pending，管理员待指定。下方为原容量交付的历史恢复入口，和本段一起保留。

## 分支、版本与位置

- 来源PR176未合并，固定设计commit `08f2ea20a11dfdd09892a67599163e32b7237edb`、tree `70d56e60b162ce3ef17e6f0ffdd55b570ec5d4d7`。
- 新任务分支`task/179-local-block-continuation`，[Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)以`task/175-local-block-design`为base；首交付commit `8513c23d70ac6156a9735f04da271cf6764a1f7c`，最终HEAD在Issue179/PR180在线回执读回。PR176合并后先核差异再考虑改base，不自动合并。
- 独立本地API包`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/delivery`，管理/来源快照与本任务白名单文件；无.git/HEAD/index/暂存，因此无“本地已提交”状态，未提交资料指发布前本目录的新文件。远端通过Git tree API继承固定父树，仅上传白名单。
- 根参考资料副本和work/Melodydt/151旧包不覆盖；main仍为`4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`（本轮读回）。本任务未改服务器或原作业。

## 成果与验证

[研究报告](../local-blocks/CONTINUATION_RESEARCH.md)、[8项容量下界](../local-blocks/continuation-capacity.json)、[核算输入/程序/来源和验证入口](../../work/Melodydt/179/README.md)、[个人进度](../../progress/Melodydt/STATUS.md)。实际发布SHA和验证结果见Issue/PR回执与work/Melodydt/179/validation.json；本地资料与远端每个上传blob逐字核验后才报告上传完成。

管理结构不是业务验收；容量算术不是完整生存期/调度证明。没有新增RTL/模型/EDA/服务器实验；作业号、节点、日志、服务器结果目录均不适用（未启动），没有自动监测。

## 未完成项与恢复第一步

负责人Melodydt先读取Issue179及PR最新头、PR176和PR178/167/152/163最新状态，确认无并行更新；保留其他任务及其作业。然后在本目录运行：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B work/Melodydt/179/analyze_capacity.py --check
```

接着从Qwen dense FFN起，给出16/32KiB候选的对象地址、紧凑打包、bank、M单上下文、down端完整Mid重放位置与成本及真实ACK/释放顺序。先形成可检查合同/轨迹，再落地新仿真；Falcon数值、系数表、Granite质量和最后同资源物理对照仍待接续。完整三模型能力未验收，不标done。

## 登记与看板交接

本轮读回management-hub PR5 open/unmerged，登记pending；复用该登记不重复建PR。PR176基线config/board.json返回404，status-mapping.json已读取；当前连接器没有Projects条目/字段读写工具，因此本任务实际看板/条目ID/status未核验，并非已证明Melodydt缺read:project权限。状态unverified、同步pending。

管理员待指定：确认正确看板及受众，补配置，查Issue179是否已有卡片，复用或添加；同步Project ID=llm-hardware-design、Status=In progress，Priority待指定不猜测；读回条目ID、字段及时间并写回本Issue/PR。未完成前不报告synced，不修改权限或另建看板。
