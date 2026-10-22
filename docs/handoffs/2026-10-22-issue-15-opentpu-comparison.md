# Issue #15 工程入口与接入待办

本记录同时保留尚未解决的协作接入事项；不表示停止正在获授权执行的实验。

- 仓库：`rayggxia-workspace/LLMHardwareDesign`，project_id `llm-hardware-design`。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，负责人YUZE-LU，实际身份已读回；[草稿PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，base `task/7-parallel-blocks`，依赖PR10，不自合并。
- 当前分支 `task/15-opentpu-compare`；14轮runner `7139190aa944dd3c88b44eb3234b869e6c3c46e8`，提取后15轮 `03f8b20904eb2dc7f7dcb81309041a32c60550fe`，16轮 `46e4ee97727f53e76269087d57ac8ef5389d4dc9`。实际已执行runner分别绑定每条submission回执，不能用更新后的HEAD替换旧运行身份。
- 本地独立工作树 `D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-15-opentpu-compare`；原始输出 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/`。不修改已有PR8／PR10工作树和封存结果；89448不属于本轮。
- 正式代码 `project/experiments/opentpu_compare/`，轻量回执 `results/`，[实验定义与实测](../experiments/issue-15-opentpu-comparison.md)，个人进度 `progress/YUZE-LU/STATUS.md`。

## 已验证与继续入口

已运行管理结构检查、Python编译、差异检查及每轮上传Bash语法检查。真实计算节点核对镜像、工具、输入输出SHA；全部Slurm作业实读UNLIMITED，无耗时取消策略。ACT功能锥及负例、透明分层SPEF自检已通过。块内／父层严格门槛和功能证明按实际终态分别记录，不把结构检查、进程退出或cap计数0当作验收。

第一步运行 `python project/experiments/opentpu_compare/collect.py`，随后 `quality.py`。正式三块m9-act-03／89671、m9-mxu-03／89677、m9-merged-03／89678均严格通过，三块功能证书89687通过。父层从共同封存CTS89700／89701继续，当前合并06／89711正在DRT，拆分07／89722针对宏输出电容加入近端缓冲；后续因真实违例更新候选时，以回执及实验报告最新选择为准。03／04曾因旧引脚命令缓存误判被提前停止，89705直接读ODB证明原几何正确；更正在results/correct-cached-pin-export-diagnosis.json。保持2.5ns／0.5ns、同功能／状态／SRAM，任何调整使用全新尝试目录；不得放宽原预算掩盖违例。

尚需两组父层实际终态、完整分层STA与PG检查、共同引脚几何核对和最终成本对照。synthetic SRAM无真实GDS，上游RTL等价和制造签核未完成；实验为允许M10父层PG和新增缓冲的H1，不是H2冻结底座。

最新入口（2026-10-23 03:36 CST）：拆分20／89821自然COMPLETED0（1:02:26，UNLIMITED），DRC4771→211→106→12→2→2→0、天线0及最终PG通过。完整真实setup／hold +0.102314／+0.036146ns及电气通过；宏模型setup／hold +0.0754514／+0.0747274ns、最差cap +3.396215916fF，但act_data[145]的slew 209.263235ps超过199.000001ps上限10.263235ps，严格不合格。功能89822／RC覆盖89823均通过，不能抵消该接口失败。只读89824及规格比较89825定位place13151 BUF_X4；X8／X16旧RC均无电气违例且最差setup／hold相同。拆分21／89826于03:33:56 CST启动，runner6de7b3773398f15ef36362568977c541a01143e2，实际仅place13151 X4→X8，无新增缓冲／guardband；源时序复现、接线／合法化通过，已重新完整DRT。匹配21／13功能89827、RC覆盖89828依赖排队，runner46e6fdc57332467bd107b98b38b13a5200415c90，三项实际UNLIMITED。合并13继续作完整合格主对照；最终PPA仍待合格拆分和匹配证据。 恢复先collect／quality，来源匹配选择selection-split21-merged13.json；全部门槛通过后才compare／plot／report并做三图和HTML实际目视核验。失败则保留新终态、继续实际违例修复，不按耗时停止。当前工程commit 46e6fdc57332467bd107b98b38b13a5200415c90，实际作业runner按submission回执。以下续记是历史过程，不替代本条最新入口。

最新补充（2026-10-23 03:53 CST）：增加独立线路复用候选top-split-reuse-20-01／89829，03:42:18 CST提交，16CPU、UNLIMITED，runneredc6479bbf993669aba7eae405ede1610baa538a。与21同从源20只改place13151 BUF_X4→X8；合法化后实际1个单元改变、2条关联普通线路清除，11952条既有普通线路保留到DRT输入，信号接线不变。原生DRT已推进至约30%，中间违例0，尚无终态资格；不宣称最终线路冻结，路由器仍可修复任何网络。现有21／89826继续自然运行。匹配复用候选／合并13的功能89831、RC覆盖89832、五个完整最终ODB线长复核89833依赖排队，runner401ce9bdd927d7483b24ede0803689f1ab447eae，均1CPU、UNLIMITED。 当前代码401ce9bdd927d7483b24ede0803689f1ab447eae，初始线路复用实际runner edc6479。恢复先collect／quality检查两条路线；复用候选必须带native-wire-reuse20-13-01完整ODB成本证明，再selection-reuse20-merged13.json→compare→plot→report，十一份来源／证明全部满足UNLIMITED、工具身份、封存与匹配来源。现有21继续自然运行；若某条路线合格不取消另一条有效作业。完整ODB成本API89830已通过，原生两种统计实际差异保留，1%只防成本漏计，不放宽电气／时序／物理验收。尚未生成最终对照／三图／HTML或做最终视觉QA。

## 管理员与审查待办

- 登记：沿用[管理中心PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)的pending证据，未声称registered。
- 看板：本仓库仍无 `config/board.json`；既有凭据缺少 `read:project`，当前Projects工具也未提供任务条目核验能力。实际条目／字段状态unverified，加入／同步动作pending。
- 待具备权限的管理员（待指定）核对组织总览Projects1是否适合本项目，查找并复用Issue15条目，按 `config/status-mapping.json` 写入真实Project ID和Status后读回，记录条目ID／链接／时间；不能猜测条目或字段ID，也不能自行扩充凭据权限。
- 审查人、优先级待指定；任务仍in_progress，实验完成也须独立审查及合并才能按规则标done。没有期限要求，不填写杜撰日期。

19:12补充：合并06完成DRC／PG但真实分层时序和电容失败，拆分07仍在DRT；08／09的EST-0104错误保留。后续joint_repair.py采用独立OpenROAD进程、真实ODB检查点交替修复并每次重路由／估算RC。89750核对40846个未标注驱动均无连接负载。新轮以submission绑定runner，不将当前HEAD倒填旧轮。

2026-10-22 19:29 CST：06／07均完成DRT／PG但时序和电容失败，完整分层setup −0.053027／−0.002414ns。当前作业12轮89764／89765，原生插入辅助接口SIGFPE改为显式ODB接线（探针89763通过），每步真实连接断言、合法化、重布线和最终功能证明仍要求通过。继续入口先collect，再查看joint-repair.json和joint-final-quality.rpt；未通过不得生成最终PPA。

2026-10-22 19:52 CST：当前作业13轮89772／89773，runner182898cca91c3b403985b6d2278b143ef2dd9852。12轮已保留4阶段严格失败；13轮追加原生长线分段，每轮ECO后完整GRT再估算RC。SDC一致性、preamble／时序缓存和既存普通信号线的排查结果在89768／89770／89771及实验记录；不得把最新runner倒填旧作业。

2026-10-22 20:12 CST：拆分13／89773因重复GRT的GRT-0229失败；合并13／89772仍正常运行，不因新方案而取消。当前14轮89776／89777每个电气ECO使用新的OpenROAD进程：真实ODB／SDC检查点、下一进程重建路由／RC、最终不修改网表的独立审计通过才写DRT guides。runner7139190。先collect，查最新joint-*-drive-*-changes.txt与joint-*-audit.rpt及joint-repair.json。所有作业UNLIMITED，不设置耗时取消；最终实际DRT／PG／完整分层STA、父层功能及RC覆盖证书和PPA尚未完成。

2026-10-22 20:31 CST：合并13／89772独立GRT审计通过并进入DRT；14轮仍在修复。提取后定向15轮合并89781／拆分89782，runner03f8b20，已从06／07封存终态恢复、核对SPEF复现原时序、按实际报告修改并通过接线／合法化，进入新DRT。源失败结果仍保留；15轮GRT估算为诊断，最终所有真实DRT／PG／电气／完整层次STA门槛不变。优先检查这三路DRT及随后真实提取；通过后选择同资源父层对，补最终父层功能和原生RC覆盖审计，再compare.py和plot.py。不得把预估余量或插入成功当作合格PPA。

2026-10-22 21:15 CST：合并13／89772已COMPLETED，quality.py和真实分层STA均通过，setup +0.065642ns、hold +0.013027ns；最终PG通过，是当前合格物理父层候选。低面积合并15／89781严格失败，真实分层setup +0.031373ns但3条真实电容负余量；已封存，16轮89786从其恢复继续定向ECO并进入新DRT。拆分15／89782继续DRT，14轮亦仍迭代。先collect，再quality.py，待选定两组最终终态后新建父层功能与RC覆盖审计spec（旧03和旧合并06证明不能替代新来源），通过后运行compare／plot。未形成最终对照，不提前标in_review／done。

2026-10-22 21:45 CST：拆分15／89782已FAILED1封存，DRC／天线0、最终PG通过，真实setup／hold +0.027594／+0.014875ns但19条真实电容仍失败。拆分16／89789通过afterany依赖等待封存后启动，runner ef82700a84652c2fa2d212e103d3490518b935cf；同一实际RC时序复现通过，带35%cap／20%slew优化余量选择167个宏输出隔离和213个驱动升级，另修cmd[138] hold及临界长线，接线／合法化通过并进入DRT。合并14／89776、合并16／89786继续DRT，拆分14／89777仍迭代，UNLIMITED。先查看上述作业最新终态，不改写失败或按耗时取消。合并13仍可作为已通过物理／完整时序门槛的对照候选，最终父层功能与原生RC覆盖证书尚待补齐。

2026-10-22 22:03 CST：合并13的父层功能89790（1662锥差异0）及原生RC覆盖89791（40846空载驱动、部分未标注0）通过，已有完整合格合并候选。合并16／89786的setup／hold与PG通过，但input330/Z电容−4.802629fF及宏模型cmd[108] slew仍失败，终态封存；合并17／89792依赖等待封存后启动，runner10e97f8，27个输出隔离、99个驱动升级并新DRT。当前关注拆分16／89789、合并17／89792及合并14／89776的真实终态；拆分14已经失败封存。若两组通过，按选定来源再补成对功能／RC证书，compare.py还要求封存原生逐层路由日志SHA与总线长／通孔指标一致，plot.py增加逐层线长图。全部UNLIMITED，不取消有效作业。

2026-10-22 22:31 CST：合并14／89776自然COMPLETED0，DRC／天线0、最终PG和真实分层STA通过（setup +0.093988ns、hold +0.013043ns），但宏模型u_merged/b_rdata[141]有1条slew违例，quality.py不通过，未入主表。当前仅拆分16／89789及合并17／89792仍DRT。compare.py新增实际输入摘要到封存输出的绑定、首次终态清单不变和共享模型摘要一致门槛；已在三块与合并13证据上核对24处绑定、9份清单及21个共享路径，负例成功检出。合并13可作完整合格备选；等待合格拆分和成对功能／RC证书后再生成最终对照／三类图。

2026-10-22 22:55 CST：上一组拆分16／89789及合并17／89792全部自然COMPLETED0、DRC0／最终PG／真实STA通过，严格宏模型仍失败，不能选入主表。双子块RC89798、候选成对功能89799及覆盖89800通过，须匹配来源。当前拆分17／89802 runner51db398、合并18／89803 runner84aad06，接线／合法化后重新布线，实际UNLIMITED。先collect／quality.py检查新来源；合并13可作完整合格备用。通过后再建立匹配来源的父层功能及annotation_sources作业，最终stitch_proof选stitch-two-child-02，再compare／plot。不修改旧回执或按耗时取消。

2026-10-22 23:39 CST：合并18／89803已自然FAILED1封存，DRC0／最终PG通过，但真实setup −0.000681ns和宏模型cap／slew仍失败。主对照采用完整合格合并13。当前拆分17／89802仍DRT清理，匹配13的功能89809／原生覆盖89810已afterany排队，runner743f654。先collect／quality，再按selection-split17-merged13.json执行compare；失败仍须修复新来源并重新匹配证明，不能跳过严格门槛。若全通过，plot.py、report.py生成三图及中文HTML，并目视核验后补最终文档／提交。工具身份与UNLIMITED双回执已强制绑定；实际16／17失败对被完整compare拒绝。89810曾恢复一个尚未提交作业的本地SSH预检查连接，任何原生作业均未中断。

2026-10-23 00:05 CST：拆分17／89802自然COMPLETED0、DRC0／最终PG／真实STA通过且cap／slew收敛，仍宏模型setup −0.0201057ns，不能选主表。17／13功能89809及RC89810通过。只读89811带实际cap／slew／input pin字段，规划器4158b65修正转义后从封存报告选17段单负载、>90ps线延迟且路径余量<120ps的长线。当前拆分18／89812 runner75bcd9b，17个BUF_X8中继加27个hold输入BUF_X2，接线／合法化通过并DRT。新18／13功能89813、原生覆盖89814 afterany排队，runner2d7649f；全部UNLIMITED，不因新候选或耗时取消。恢复先collect／quality，全部过后用selection-split18-merged13.json→compare→plot→report，再目视检查；失败则从新封存实际报告继续ECO并匹配新证明。临时本地HTML预览服务已关闭，尚未生成最终报告或做浏览器QA；不影响原生作业。

2026-10-23 01:20 CST：拆分18／89812自然完成DRC0、最终PG和完整真实STA（setup +0.002857ns、hold +0.036308ns），但宏模型setup −26.9984ps及3条输入slew仍失败。89816原生旧RC规格比较后，拆分19／89817已将3个父层时钟缓冲改为BUF_X16、升级11个接收端驱动及1个pf_block弱中继，接线／布局通过并重新DRT；匹配功能89818／RC覆盖89819排队，实际UNLIMITED。合并13保留完整合格主对照，最终PPA仍待合格拆分。 runner9de8caf9cdf4b736f3b79d4d129590a07a706430；功能／覆盖runner81d5a1bfcbb35051985300c204953d8259b451cb。恢复先collect／quality，若19全部通过，再selection-split19-merged13.json→compare→plot→report并做实际三图／HTML目视核验；若失败，继续从新封存真实报告修复，不设置运行期限。89816旧RC时钟规格比较无物理资格，不可选主表。
