# Issue179：局部Block接续研究与协作欠项

2026-11-04，Asia/Shanghai。仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179)，负责人Melodydt。优先级/审查人/Projects处理管理员待指定。

## 21:54 CST 第6步局控RTL合同（优先恢复此段）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父e079924c7956c1fddf0994db5ba7cc67fede691a；独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-rtl-contract-e079924/delivery，无.git／HEAD／index，仅上传白名单，旧包不覆盖。本地发布前资料不等于Git提交；最终远端commit／原文／CI见PR180。

恢复先读规则、Issue／评论、PR180、PR176 head／正文／评论／review／逐行评论并核pr176-sync.json；有差异先同步，上传前再核，每轮进展继续直接补总方案。

[第6步合同](../local-blocks/LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)与project/control_rtl_contract_v0_1交付92逻辑信号／状态机候选、单PM端口／装载准入／信用／RX关闭、SystemVerilog声明与36组边界检查，累计173组。4份人工期望时序不是DUT轨迹，HDL编译／lint／仿真未执行；本机PATH未发现iverilog/verilator/yosys。来源／实际验证见work/Melodydt/179/control-rtl-sources.json及control-rtl-validation.json。

先运行管理检查、七套单测、声明／示例--check及既有两campaign重建；下一步实现配置／单口仲裁、CALL／FETCH、空任务和M clear的EXEC/WAIT/END功能局控RTL，再扩RX/TX／取消。逻辑端口不等于宏原生pin或物理冻结；内部tag不解决无tag迟到响应。真实provider复位、SRAM/CDC和完整Block仍为外部接入门，未授予控制RTL或物理资格。

负责人Melodydt继续；无服务器作业／节点／日志／结果或自动监测；研究in_progress、PR Draft／未合并；登记PR5 pending，看板unverified／同步pending（缺board.json／Projects工具），管理员／审查人待指定。

## 20:58 CST 第5步恢复研究（历史记录）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父c22dde6972e0f86600ecdc4060409e6947b19fb8；独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-recovery-c22dde6/delivery，无.git／HEAD／index，仅上传白名单，旧包不覆盖。本地发布前文件不等于Git提交，最终远端commit／原文／CI见PR180。

恢复先读规则、Issue／评论、PR180和PR176 head／正文／评论／review／逐行评论，比较pr176-sync.json；有变化先同步合同，上传前再核。每轮目标、上游、产物、实际验证、限制及下一步仍须直接补总方案。

[第5步合同](../local-blocks/CONTROL_RECOVERY_PLAN_V0_1.md)与project/control_exec_v0_1新增恢复模型／独立检查器。9取消／poison＋9恢复、168退休、2模型复位cohort；30新增、累计137组。旧9执行报告、镜像与人工参考不改；来源／实际验证在work/Melodydt/179/control-recovery-sources.json及control-recovery-validation.json。运行管理检查、六套单测、两种campaign逐字重建后，冻结局控RTL周期级接口／状态机／写口互锁与真实provider确认清单。

重要边界：无tag旧响应在新上下文中可能无法识别；隔离只在provider静默／复位合同下成立，观察标签不是native tag。RX关闭及RESET_ACK是模型合同；7／11参与者不含尚未建模的G／feeder／仲裁，真实Block复位范围需另核。S写不回滚，poison保留义务；完整重新装载和新epoch后才解除门控。未执行控制／宏／S RTL、完整Block、LLM数值或物理。

负责人Melodydt继续；无服务器作业／节点／日志／结果和自动监测；研究in_progress、PR Draft／未合并，登记PR5 pending，看板unverified／同步pending（缺board.json／Projects工具），管理员／审查人待指定。

## 19:46 CST 第4步二进制执行（历史记录）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父8cb31090ed936906f4cf5a7a9a5ce4fa8ce7f864。新独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-exec-8cb3109/delivery，无.git／HEAD／index，旧包不覆盖；本地发布前文件不是Git提交。最终远端commit、原文读回和CI见PR180回执。

先重新读取规则、Issue／评论、PR180和PR176 head／正文／评论／review／逐行评论，核pr176-sync.json；有差异先同步合同，上传前再核。每轮研究仍须把目标／上游／产物／实际验证／限制／下一步直接补总方案。

[第4步说明](../local-blocks/CONTROL_EXECUTION_MODEL_V0_1.md)和project/control_exec_v0_1交付按二进制PC执行的母控／局控与有限peer；9次实验100退休／193观察，新增26、累计107组测试。来源与验证为work/Melodydt/179/control-exec-sources.json／control-exec-validation.json。运行端不读人工案例，compare仅做观察映射／独立检查，既有镜像和参考未改。

恢复核来源后运行管理检查、五套单测、run_campaign重建；下一步补运行取消／排空／poison、provider协同复位确认和迟到响应，随后冻结RTL接口。当前仅14类直线指令、M op6／RAW16；无控制RTL／完整Block、原生宏／S RTL或物理／LLM数值执行。ModelBound不是架构错误终态或死锁证明；失败实验的loader失效不代表已实现协同复位。

负责人Melodydt继续控制研究；无本轮服务器作业／节点／日志／结果和自动监测。研究in_progress、PR Draft／未审查未合并；登记PR5 pending，看板unverified／同步pending（缺board.json／Projects工具），管理员／审查人待指定，需核实际条目／字段后读回。

## 19:14 CST 第3步镜像／装载（历史记录）

仓库／负责人／Issue／PR同上；分支task/179-local-block-continuation，base task/175-local-block-design，父add63270a2faf707fac035898dd13028ceb1135f。新独立部分API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-images-add6327/delivery，无.git／HEAD／index，本地发布前文件不是Git提交；只上传本轮白名单，旧目录保留。最终远端版本、原文核验及CI见PR180在线回执。

恢复第一步：重新读取规则、Issue179／评论、PR180及PR176 head／正文／评论／review／逐行评论，比较pr176-sync.json；上游有变化先同步合同，上传前再核。每轮目标／上游／产物／验证／限制／下一步仍须直接补进总方案。

[第3步合同](../local-blocks/CONTROL_IMAGE_LOADING_V0_1.md)和project/control_image_v0_1交付7份完整镜像、manifest／SHA与配置状态模型；[来源](../../work/Melodydt/179/control-image-sources.json)及[验证](../../work/Melodydt/179/control-image-validation.json)记录实际版本／命令／产物SHA。修正旧参考CALL arg0=1；累计81组检查，START仅准入，未执行PC／RTL。运行管理检查和四套单测，再开始独立二进制执行器；不得用cases.json给运行端排程，它只给oracle。

未完成：PC执行、真实配置总线／互锁RTL、provider复位确认实现；完整Block／模型数值／物理为外部门。负责人Melodydt继续控制研究；没有本轮服务器作业／节点／日志／结果或自动监测。研究in_progress、PR Draft／未合并，登记PR5 pending；缺board.json与Projects工具，看板unverified／同步pending，管理员／审查人待指定，需管理员核实际条目及字段后读回。

## 18:21 CST 第2步用例与参考轨迹（历史记录）

每次恢复先核PR176最新head／说明／评论／review／逐行评论，比较pr176-sync.json并同步受影响合同；上传前再核。用户新增要求：每轮目标、上游差异、产物、实际验证、结论／限制和下一步必须补入总方案，不能只记聊天或个人进度。

[第2步](../local-blocks/CONTROL_REFERENCE_CASES_V0_1.md)交付project/control_cases_v0_1的3组程序／29指令／分离记录、4条人工轨迹和27组检查；不执行PC，不验证RTL或实际S写。源TX必须收到ACK才释放，接收token本用例在写确认＋ACK发送接受后完成；M错误轨迹为peer非正常注入。

父afd96b359c369c7ea039cca2c642677b0ab5f665，任务分支／PR base不变；新目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-traces-afd96b3/delivery，无.git／HEAD／index，只上传白名单，旧包不覆盖。最终commit／原文／CI见PR180；[来源](../../work/Melodydt/179/control-case-sources.json)及[验证](../../work/Melodydt/179/control-case-validation.json)记录实际命令。

恢复核源与测试后，下一步完整镜像／配置装载合同和半装载有效互锁，再实现二进制执行器来产生独立实际轨迹。完整Block、模型数值和系统物理仍是外部门。无本轮服务器作业／节点／日志／结果或自动监测；研究in_progress、PR Draft／未合并，登记PR5 pending，board.json／Projects工具欠缺，看板unverified／同步pending，管理员／审查人待指定。

## 17:39 CST 第1步接口合同（历史记录）

用户要求每次研究先看PR176更新并及时同步。恢复第一步：用本人连接读取PR176 head、状态／说明、评论／review／逐行评论，和work/Melodydt/179/pr176-sync.json比对；有变化先读diff，更新受影响接口／profile／来源和兼容版本。上传前再查一次；不是后台监测。本轮开始head08f2ea20未变且评论／review空，最终检查见同步记录。

[接口合同](../local-blocks/CONTROL_INTERFACE_CONTRACT_V0_1.md)与project/control_contract_v0_1现有6模块149原生端口、12个P服务、2个16KiB研究profile及15组静态检查；不是控制RTL／Block实现或R2执行器。M上下文、G包与S真实ACK必须分别推进。查[来源](../../work/Melodydt/179/control-interface-sources.json)／[验证](../../work/Melodydt/179/control-interface-validation.json)后，先运行管理和两套编码／字段单测，再按空任务／单服务写独立预期轨迹及镜像／配置装载合同。

发布父提交df3e7a2657a96bf0e5031a958d48155010bd7380；任务分支／PR base不变。新工作目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-interfaces-df3e7a2/delivery，无.git／HEAD／index；修改仅白名单，旧包保留，最终commit和远端原文核验见PR180。源RTL仅只读绑定，未上传／修改PR178原模块，没有新服务器作业／节点／日志／结果或自动监测。

负责人Melodydt继续控制研究。第1步为P接口基线，R1整体／R2未完成，完整Block与系统物理仍为外部依赖。登记PR5 pending；缺board.json／Projects工具，看板unverified／同步pending；管理员／审查人待指定。研究in_progress、PR Draft／未合并。

## 17:05 CST 控制研究范围（历史记录）

用户明确本分支只研究母控／局控，不负责完整 Block 实现。最新[方案第0、9节](../local-blocks/TWO_LEVEL_CONTROL_PLAN.md)改为接口合同、镜像与装载、二进制控制模型、局控 RTL＋有限协议 peer、母控多局控协同及控制程序生成。基础宏／S／完整 Block 数据通路与系统物理／模型质量由外部任务负责；真实集成验收要求保留，任务／负责人待指定。

发布前基线614cdab41cfde66ee31c92fc3e44a9e1733a338a，任务分支／PR base不变；最新目录 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-scope-614cdab/delivery，无 .git／HEAD／index。修改仅本轮白名单，旧资料包不覆盖，最终 commit和读回见PR180。没有本轮服务器作业／日志／结果目录或自动监测。

恢复第一步：核 Issue179／PR180 最新版本和本范围约束，读[文档验证](../../work/Melodydt/179/control-scope-validation.json)，运行管理检查，然后开始 R1 控制接口／profile及装载准入。用协议 peer 可启动研究，明确假设和有限资源，不把 peer 写成真实 Block。登记PR5 pending；看板unverified／同步pending，管理员待指定；研究in_progress、Draft／未合并。

## 16:25 CST 综合方案交接（历史记录）

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
