## 目标与授权
按用户在本会话明确要求，以当前发布的七宏版本及仓库样本模型，开始六项连接方案研究；已有方案须详细说明数据/控制流程、实际改动，以及协调/适配逻辑位于Block内部、外部预制bridge宏还是测试胶合逻辑。

## 负责人、范围与依赖
- 负责人：Melodydt；优先级、独立审查人待指定。
- 六项：普通注意力、额外Norm、门控FFN、Qwen3.5 GDN、Falcon SSM、Granite MoE。
- 固定来源：main模型图、#143/PR144七宏、#130/PR132供数、PR133专项互联、#145/PR146事务模型；开始先核对各head。
- 复用并明确与#63通信描述、#121/#130/#143叶宏及其他成员专用消费者研究的边界；不重复接管或修改其代码、作业、服务器目录。
- 本轮交付为第一阶段研究文档、逐连接/改动归属清单、固定版本来源及轻量结构核验。未获验收的新连接标候选；不以文档或静态检查替代RTL/物理验收。
- 不运行服务器、模型推理或EDA，不修改现有RTL，不扩大ref-project维护范围。后续实现/仿真通过本Issue或明确子任务继续跟踪。

## 验收标准
- [x] 六项分别列出算子→宏映射、数据路径、输入/输出格式、存储/回放、控制与提交步骤。
- [x] 已有S内loader、pair测试mux、独立bridge/bank/booster/return等逐一核实源码/物理边界和适用版本。
- [x] 每条候选改动标明宏内、外部预制适配/bridge、协调器或纯金属，记录兼容/带宽/容量与验证缺口。
- [x] 明确v1与v2、RTL组合与SystemC与物理证据，不转移资格；说明SystemC版本同步缺口。
- [x] 研究报告、机器可读索引、实际检查结果、本人进度及交接通过独立任务分支/PR交付；不自合并或提前done。

## 任务隔离与状态
本地项目根是管理参考副本，尚不是完整Git checkout。将使用本Issue独立子目录准备研究交付；远端仅新任务分支，保留基线树及其他成员文件。任务—分支—目录对应关系在建立后补入PR/交接。
第一阶段启动时状态：in_progress。登记沿用management-hub PR5；看板及条目将按当前配置/能力核验，缺项据实留交接。

## 第一阶段研究交付（2026-10-31 16:28 CST）

[PR #152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)已提交，当前head 49a34e75657025244fd33af56111029868008db8，base为main。六项方案、bridge归属、候选协调机制、索引/核验、本人进度与交接共10文件；逐文件读回及白名单核对通过。36份固定来源Git blob/SHA-256、65个文档链接及管理/空白检查通过；同head Project structure CI成功。

上述勾选仅表示本Issue声明的第一阶段研究交付项已形成可审查结果。RTL/SystemC/综合/P&R/系统验收未执行；候选连接与数值服务尚未冻结。PR未合并，独立审查人待指定，不标done。后续先审查系数/宽归并服务及wrapper边界，再确定最小组合实现范围。

任务—分支—目录：task/151-six-connection-study；D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/，delivery为独立API资料包而非完整Git checkout。现有main树、其他会话根目录参考文件、#121/#130/#143实施分支及作业未改。

协作回执：rayggxia-project-collab 1.0.0；project_id=llm-hardware-design；负责人Melodydt；登记management-hub PR5 pending；无board.json且无Projects条目工具，看板unverified/同步pending，管理员待指定。具体恢复见docs/handoffs/2026-10-31-issue-151-six-connections.md（本PR）。


## 第二阶段：固定产品的六类连接与分层控制总方案

用户在本会话补充并确认：同一M1–M10预制底座，在M11/M12定制时确定目标模型；每个成品运行期间无需更换任意逻辑顺序。本轮继续复用本Issue和PR152，不创建重叠任务。

- 研究范围：固定产品控制程序/选择机制、两级母子控制与唯一资源所有者、分散bridge和共享S访问、六类阶段/事件/存储模板、显式数值缺口、物理边界与公平对照验证计划。
- 首选候选：相同预制顺序器与局部FSM，预置有限产品程序，通过预留M11/M12选择端固定产品；比较一次装载控制存储等备选。六种算子模板不等于八个整模型程序已经编译完成。
- 交付：总设计、控制规格、六模板规格、proposed决策、机器可读合同及有意义的静态校验、来源/检查回执和本人进度/交接。全部新增系统硬件标候选，不宣称RTL或PPA完成。
- 验收：连接/格式/资源所有权和事件语义闭合；容量、单M结果上下文和R/T提交限制明确；静态正负例与文档来源核验有实际结果；PR可审查、状态如实。
- 不修改现有叶宏RTL，不接管他人成果/服务器，不运行RTL/SystemC/EDA，不维护ref-project。
- 第二阶段启动时状态：in_progress；本轮开始时间UTC 2026-10-31 10:18:05 UTC。负责人Melodydt；独立审查人待指定。登记PR5仍pending。当前无Projects条目能力，在线同步pending/状态unverified；按交接继续处理，不将该情况归因为已证实账户权限不足。


## 第二阶段总方案已交付待审查

本轮commit 46b29c7664fefedf2de767ddcfb94a766cf341fb，继续[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，累计19文件。总方案、控制规格、六模板、proposed决策、机器合同/来源与静态正负例回执已提交；本人进度、交接及架构命令同步。

验收材料已形成：固定产品绑定、两级控制、端口唯一归属、六类阶段/容量/事件、R多tile外部版本服务及NUM数值门槛均有详细候选规格。静态检查6模板64阶段、15项端口唯一归属、17拒绝用例、43固定文本来源与122链接通过，19文件空白检查通过；辅助交叉审阅已修正重要次序和取消边界。完整产品程序编译、RTL/SystemC/EDA/数值与系统验收未执行。

当前状态in_review：等待独立设计/PR审查，审查人待指定，不自合并、不标done。PR5登记pending，看板unverified/同步pending，具体缺项见PR/交接；当前head CI与上传读回结果以PR最新回执为准。下一步先评审方案与未决服务，再创建实际RTL/实验子任务。


当前head线上核验：2026-10-31 10:47:15 UTC，19文件blob及PR范围读回通过；Project structure run41193985271/41193981929均success（管理结构）。PR仍open/未合并，Issue保持in_review；本轮详细设计已形成待独立审查，硬件与完整程序验收未执行。


## 合入PR144实现基线（用户授权）

用户明确要求将PR144内容拉取到当前连接/控制研究分支并继续。固定来源643c6012a11cbf461146ac40fbf61485223fe946，目标原head46b29c7664fefedf2de767ddcfb94a766cf341fb，真实共同祖先6a681d6632e7f7be537ff96eae1827df834bcfe8。执行三方整合，保留原始祖先和研究；不合并PR144到main、不改PR144分支，不运行服务器/EDA。

PR144含较多上游历史，compare的300文件不是完整清单；使用分层Git树比较，只处理实际差异，ref-project同树未展开/改动。公共文档冲突保留main/研究与实施记录。PR152将作为依赖PR144的研究PR（基分支task/143-seven-block-v2），上传后重新核验当前树与检查结果。当前in_progress，完成后回in_review。


## PR144实现基线已整合并推送

双父merge commit faabeda68b3b098ba562d68517319e02725f5bc3，父为原研究46b29c7664fefedf2de767ddcfb94a766cf341fb与PR144固定643c6012a11cbf461146ac40fbf61485223fe946；保留原实现/研究历史。PR152现base为task/143-seven-block-v2，不合main、不改源分支。source project整树保留，19项整合文档/14核心源读回一致，当前PR36差异文件中RTL/ref-project均0改动。

隔离包五项检查exit0：管理、原研究、系统合同、RTL字节/入口、上游轻量Tcl夹具；19文档空白检查通过。当前head管理CI41198679694/41198673859均success。未跑RTL/SystemC/EDA或新物理资格，没有服务器作业。R仍未合格，跟踪候选与原源数据库不混用；PR133/146未自动带入。

实现入口docs/SEVEN_BLOCK_RESEARCH_BASELINE.md，检查/来源回执见PR152及integration-checks.json。依赖同步完成后回in_review；独立审查人待指定，下一步拆最小FFN/257Softmax系统wrapper任务。登记pending、看板unverified/同步pending保持，不提前done。


## 第三阶段：按实际RTL重建总方案

用户要求根据当前已有RTL重新生成总方案。固定本研究分支当前faabeda68b3b098ba562d68517319e02725f5bc3（已导入PR144的643c6012），逐项核对M/S/T、N/E/G与R的真实端口、操作码、格式、生命周期及已有/缺失适配。重写总设计、控制规格和六模板，补原生接口审计、可复核命令和验证边界。PR144后续更新不会自动混入该基线。复用PR152；范围仍为研究文档/静态核验，不改叶宏RTL，不运行RTL/SystemC/EDA。负责人Melodydt，当前in_progress；独立审查、登记与看板缺项继续单列。

## 第三阶段已上传：按当前RTL重建总方案v0.2

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)本轮commit 36f9c9dbb3cab8247008403ccb08ce26c0fdc99f（父faabeda），继续task/151-six-connection-study、base task/143-seven-block-v2。实质重写总设计/控制规格/六模板，新增七宏原生接口与操作码审计（MST/NEG/R三附录），更新机器合同、SSM两遍次序、原生命令例子、本人进度和可执行交接。

具体修正包括M.op4/scale、S写ACK、N目标总长度/mask、E/G尾字/数值单位、G gated Sigmoid、R按F转换/param_valid/局部提交与按范围导出、loader无abort，以及T首读后连续refill。GDN保留conv/SiLU/QK L2往返、16→32头复用和仅Q额外缩放；NUM/外存/版本服务明确为缺失能力。固定产品ROM、两级控制和全部有源适配仍待实现与冻结前预算，不把文档当完成硬件。

五项实际静态检查exit0；6模板64阶段、15owner、17拒绝用例、43固定来源版本、14核心RTL字节、7接口签名与示例编码核对通过。24/24上传blob与父提交24文件白名单一致，project/ref-project子树不变。当前head管理CI41201716861 success。未跑RTL/SystemC/整数oracle/完整模型程序/质量/EDA，没有服务器作业。源PR144后续提交未自动混入，R仍未获最终资格。

入口：[总方案v0.2](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/36f9c9dbb3cab8247008403ccb08ce26c0fdc99f/docs/SIX_CONNECTION_SYSTEM_DESIGN.md)、[原生审计](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/36f9c9dbb3cab8247008403ccb08ce26c0fdc99f/docs/RTL_NATIVE_CONNECTION_AUDIT.md)、[实际检查回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/36f9c9dbb3cab8247008403ccb08ce26c0fdc99f/work/Melodydt/151/rtl-redesign-checks.json)。回in_review，PR未合并、独立审查人待指定，不标done。下一步评审后定义最小wrapper实施任务及NUM/外存/版本服务边界。

rayggxia-project-collab 1.0.0回执见PR152：Melodydt；登记management-hub PR5 pending；无Projects条目工具/实际字段读回，看板unverified、同步pending，管理员待指定；不能把上传完成说成在线协作接入完成。


## 第四阶段：用户明确覆盖全部合法连接

用户澄清：六类算法只是常见连接组合，目标是打通支持范围内所有允许连接组合。本轮把研究总方案升级为按原生端点/角色、类型/尺度、拓扑与生命周期定义的可组合连接能力；六算法降为回归样例，不以六固定模板限定合法图。建立7×7有向类型对索引并下钻角色/profile，区分语义合法、资源可映射、硬件实现和已验证，合法但缺实现保持gap，不能通过缩小允许集合伪造覆盖。继续固定成品程序、M11/M12绑定与两级控制，不据此要求运行时任意改图或49条直接物理总线。复用本Issue/PR152，文档/机器合同/静态覆盖核验；不改叶宏或运行RTL/EDA。负责人Melodydt，当前in_progress。

## 第四阶段用户边界收敛与v0.3交付

用户追加确认：可以假设只有有限大模型类型；仅M11/M12永久绑定，不依赖启动装载。因此当前主方案为有限且明确FamilySpec/有界结构参数→预制完整家族程序ROM与通用原语→永久选择和参数绑定。逐bit金属编码控制存储仅是必要时另评审扩展，非默认必须；六类算法只作回归，不限定数据连接目录。

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)已推送commit 39bd7bf66c47e17c18aa39483c1d974a1e079aa2（父36f9c9db），22文件增量、22/22 blob读回及白名单通过，当前head管理CI41205510340 success。新增[全合法连接规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/ALL_LEGAL_CONNECTION_SPEC.md)、[原生角色/适配profile](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/LEGAL_CONNECTION_PROFILES.md)及目录/校验，总方案/控制/六模板/候选决策与本人进度/交接同步。

静态目录49宏对、23源角色/27数据目的角色、15适配族、7同实例规则、15拒绝用例通过；另有原6模板64阶段/15owner/17拒绝、43来源版本、7原生接口与14核心字节检查。总共六静态命令exit0，22文件空白通过。S loader通用导出采用最多1024B整描述符spool避免串行S访问死锁；同R/N lease的RESUME与新context重入分开，不错误要求所有回访先commit。

新增系统路线实现数仍0，目录不是逐角色完整分母或硬件打通率；合法但缺实现/程序/资源/路线保留gap。家族目录/完整控制程序和ROM预算、逐角色recipe、通用适配/宽转换/NUM/外存/版本服务、RTL/整数oracle/活性/物理验收均未完成。核心RTL/ref-project未改，没有服务器作业。

交付回in_review，PR未合并、不done，独立审查人待指定。rayggxia-project-collab1.0.0完整回执见PR152：Melodydt；登记PR5 pending；当前无Projects条目工具/实际读回，看板unverified、同步pending，管理员待指定。下一步审查有限家族目录与全角色覆盖，再落实实际RTL任务。


## 第五阶段：执行前三步，现有样本与片上合同

用户授权开始家族范围、合法连接账本和统一接口/资源合同前三步；当前仅考虑仓库现有八个样本模型，规模不明处使用有依据的保守估计并标注，暂不考虑外存。继续Issue151/PR152与task/151-six-connection-study，输入39bd7bf；新隔离API包steps123-39bd7bf/integrated，原包/根参考副本保持。

交付目标：可机读FamilySpec/来源与估计记录；从49宏对下钻的角色级连接配方与缺口；无外存地址域/自动spill的task/handle/event/lease、片上容量/信用/ROM候选合同；详细工作报告解释改动、原理、动机、容量限制及验收边界；实际验证与来源指纹、进度/交接及PR回执。叶宏RTL不改，不运行推理/RTL/EDA或服务器，不维护ref-project。大型样本的真实形状保留，片内容量不足记录CAPACITY_GAP，不暗中缩形状或把外存作为后路。负责人Melodydt，当前in_progress；独立审查人待指定。

## 第五阶段前三步规格已交付待审查

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)已推送commit 86d564850d8f539934a6356e3a26c4dfbab65657（父39bd7bf），31文件、31/31 blob与父提交白名单一致，当前head管理CI41209674396 success。当前范围仅仓库八样本/十层型，无EXT/DMA/spill，M11/M12永久绑定无控制程序启动装载。

成果：[详细工作报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/86d564850d8f539934a6356e3a26c4dfbab65657/docs/STEPS_1_3_WORK_REPORT.md)、[FamilySpec](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/86d564850d8f539934a6356e3a26c4dfbab65657/docs/SAMPLE_MODEL_FAMILY_SPEC.md)、[角色配方账本](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/86d564850d8f539934a6356e3a26c4dfbab65657/docs/SAMPLE_LEGAL_CONNECTION_LEDGER.md)、[片上接口/资源合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/86d564850d8f539934a6356e3a26c4dfbab65657/docs/SAMPLE_ONCHIP_SYSTEM_CONTRACT.md)。包含621数据候选槽＋460受控参数槽/153规范配方、96项样本连接义务、明确字段/64bit控制flit/信用/S容量及保守控制/ROM估计。405条件槽/216未决槽保留，不把1081槽写成合法或已通。旧外存全系统合同明确为历史参考，不参与本轮准入。

样本真实规模不缩小：源配置位置32768..262144与B1/S2 FP32导出分开；一层FFN即使按S8较小存储场景最小仍9MiB，GDN/SSM单层S32 state2/4MiB，原生S16KiB和默认9KiB计算区不足的需求报gap。独立loader capture1KiB、新控制32KiB、ROM2MiB均为未实现候选预算，非现有容量。实际图RepeatHeads→L2、epsilon未知及Falcon conv bias缺口均记录，不改算法掩盖问题。

9实际本地命令exit0；19来源Git blob/SHA、10配置原回执、70静态规则/容量用例、7接口与14核心RTL检查通过；账本和内存需求逐字节重生成一致，31文件空白通过。未运行RTL/SystemC/推理/服务器/EDA，完整定点图/程序/精度/活性/物理接收未执行，新增系统RTL仍0。完整模型片上准入未证明；本次为前三步可评审规格而非底座冻结或全部连接实现。

状态回in_review，PR open/未合并、独立审查人待指定，不done。按rayggxia-project-collab1.0.0回执：Melodydt；本轮登记PR5已读回open/unmerged→pending；无Projects条目工具且实际卡片未读回，看板unverified/同步pending，管理员待指定。下一步先审查估计/片上资源选择及缺口，再推进适配/存储RTL任务。


## 2026-11-01：外存边界与N接口澄清

用户明确系统有外存，当前暂不研究，保留接入灵活性。P0片上验证的EXT credit0/valid0、无DMA/自动spill不构成产品永久禁外存；GAP_ONCHIP_*不要求所有权重/KV/state永久片上。JSON分离architecture_memory与memory_policy，保留region/地址/MEM/完成语义扩展；真实接口/PHY/搬运需在相关有源逻辑冻结前确定，不声称当前已实现。

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)本轮commit e44c4f5f492b2ef0fef12846dd25c1b1ea637664，父86d5648；22文件、22/22 blob与白名单核对通过、当前head管理CI success。N固定RTL说明：一个顶层module以cmd_op选择操作，共用128bit rsp口但向量/统计/ID/factor格式不同；内部子模块不等于多个可独立调用的宏。详见[澄清](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/e44c4f5f492b2ef0fef12846dd25c1b1ea637664/docs/MEMORY_SCOPE_AND_N_INTERFACE_CLARIFICATION.md)。

生成器重生成＋4验证命令exit0，70静态案例、19来源/10配置、7接口/14核心字节通过；621/460槽及153配方、模型卡与容量预算保持。本轮无RTL/推理/SystemC/服务器/EDA或外存实现。新隔离目录work/Melodydt/151/memory-scope-86d5648/integrated，原包/根副本保留；任务分支/base不变。

负责人Melodydt；PR待独立审查/未合并，Issue保持in_review、不done。登记PR5读回open/unmerged→pending；无board.json且当前工具无Projects条目能力，看板unverified/同步pending、管理员待指定。实际检查、进度与可执行交接已随PR同步。下一步先评审本边界及前三步设计，外存集成另研究，不把P0限制推广为系统架构。


## 第六阶段：按静态编译与共同底座重新研究前三步

用户授权在软件保证角色/类型/尺度/布局、硬件执行必要动作的基础上重做前三步。现有八样本/十层型与e44c4f5输入保持，叶宏固定643c6012；系统有外存，本阶段暂不研究其具体接口/带宽/调度；P0不是产品永久无外存约束。

本轮范围：步骤1明确模型绑定与共同/产品/运行时变量；步骤2把角色配方降为编译期证明、固定接线、已有op、必要共享适配动作及缺口；步骤3收敛静态程序/母子执行控制与资源合同，不默认运行时通用role或256bit handle/512bit task。保持全部合法连接目录，不把候选槽或recipe当硬件数量。

验收：逐模型绑定表、角色到动作的可检查映射与有意义正负/数值例子、明确共同底座固定项和M11/M12永久选择、字段/队列/缓冲/存储预算及剩余缺口；真实检查和报告/进度/交接通过原PR152上传。不声称完整模型编译、RTL/精度/活性或物理验收，不修改叶宏或接管服务器。

任务—分支—目录：Issue151；task/151-six-connection-study；PR152 base task/143-seven-block-v2；D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/static-rework-e44c4f5/integrated，为独立API资料包而非Git clone，无本地HEAD/暂存，旧包/根参考副本保留。负责人Melodydt，审查人待指定；当前in_progress。登记PR5读回open/unmerged→pending；无Projects条目工具/board.json，看板unverified/同步pending，管理员待指定。


## 第六阶段已交付待审查：静态编译与共同底座

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)本轮commit 343f4d4775ffab61b2ed2df13de243cc659c157a（父e44c4f5），31文件、31/31 blob与父提交白名单核对通过，当前head管理CI success。当前[工作报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/343f4d4775ffab61b2ed2df13de243cc659c157a/docs/STEPS_1_3_WORK_REPORT.md)与三个步骤规格、三机器合同、可复现工具/案例、候选决策、本人进度和交接已同步。

实质变化：步骤1逐八产品区分共同预制/永久参数/运行变量；步骤2保留621/460/153/96分母，降为16类共享动作、优先接线与已有op，不强制每包role/通用handle或每配方独立电路；步骤3固定ROM/模板、单前台job、必要阶段锁及独立S helper。严格同一M1–M10硬件，不逐产品重综合；系统有外存，当前仅暂不研究其接入。

控制候选逻辑运行存储3448B/4KiB点、永久表648960B/1MiB点，容量未完整编译/综合证明、不宣称节省率或性能。十服务接收bank真实计640B；R版本根固定层索引仍保留old/next/发布状态，payload另计。

12实际命令exit0；37探针、22561精确有理数RNE对照、27预算/packing、18回放配方/46槽op、原70规则/19来源/10配置及7接口/14核心字节检查通过；两个主要产物逐字节重生成。新增系统RTL/完整产品编译/物理资格仍0，无推理/RTL/SystemC/服务器/EDA。输入原始模型/角色资料不改，不接管#143/#153。

本轮回in_review，PR未合并、不done，独立审查人待指定。登记PR5本轮读回open/unmerged→pending；无board.json和Projects条目工具，看板unverified/同步pending，管理员待指定。下一步先独立审查编译期证明与最低执行动作，再确定实际RTL/NUM/存储工作包；详细命令、SHA与恢复第一步见PR及交接。


## 第七阶段：正式采用七步研究路线，执行P1

用户授权将已提出的七步骤作为本研究正式路线，并开始第1步。P1版本/接口合同→P2 S服务+最小MST及母控/ROM骨架→P3 E/G FFN8→P4 N Softmax257→P5通用拓扑与重入→P6 R及必要NUM/状态版本→P7完整八产品、外存闭合与同底座验收。当前仅启动P1，不把后续实现标已开始/完成。

P1交付范围：固定源码版本与14文件指纹、7顶层接口与命令/格式/阶段/错误/端口owner合同、最小MST整数参考/预期向量、七宏后续RTL验收矩阵、版本升级规则和阶段接续。只做文档/契约/轻量软件参考，不改叶宏，不运行RTL/服务器/EDA。

版本选择：研究输入343f4d4，沿用已合入643c6012为P1与初始MST基线。已读PR144最新adb819c4d49516008e971a201a7d52c0248df8f9，14核心文件13相同，仅R内部源码不同，7顶层声明一致；不把端口一致当数值/周期/物理等价。最新R不自动导入，R仍未最终合格，后续升级独立记录。

任务—分支—目录：Issue151；task/151-six-connection-study；PR152 base task/143-seven-block-v2；D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/phase1-343f4d4/integrated，为独立API包、非Git clone、无本地HEAD/暂存，原目录不覆盖。负责人Melodydt，审查人待指定，当前in_progress。系统有外存但具体接口/调度暂不研究；role主要编译期，M1–M10固定与M11/M12永久选择保持。登记PR5 pending；无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。

## 七步研究路线P1已形成交付材料，待独立审查

用户指定的七步骤已写入[正式路线](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/be10e69bb9ad625079f68361fb47b4747d6ce040/docs/SEVEN_MACRO_INTERFACE_ROADMAP.md)，本轮仅P1。沿用643c6012，已对PR144观察点adb819完成14核心路径/7顶层接口比较：13路径同源，仅R内部变更；不自动升级，不把相同接口视为数值/周期/物理等价。

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)本次提交be10e69bb9ad625079f68361fb47b4747d6ce040（父343f4d4），非强制fast-forward；30文件、30/30远端blob与父提交白名单核验通过，本次RTL/ref-project0改动，当前head管理CI41280811622 success。负责人Melodydt；独立审查人待指定。

交付[P1报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/be10e69bb9ad625079f68361fb47b4747d6ce040/docs/PHASE1_INTERFACE_BASELINE.md)、[原生合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/be10e69bb9ad625079f68361fb47b4747d6ce040/docs/PHASE1_NATIVE_INTERFACE_CONTRACT.md)、[MST整数参考](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/be10e69bb9ad625079f68361fb47b4747d6ce040/docs/PHASE1_MST_REFERENCE.md)、机器版本/149端口/24通道合同、固定向量与33要求后续验证矩阵；可复现脚本/命令、技术取舍、本人进度和交接同步。首个P2 fixture为S8×S8 K8/N8，经S→loader→M→S→T，输出8个S64；S192B预留/T64B载荷。P2—P7未开始。

9命令exit0，合同和清单逐字节重生成，11错误合同突变被拒绝，527124条有界Python断言通过；这些是静态与受限软件参考，不是RTL/引脚握手或整模型通过。未运行RTL/SystemC/推理/服务器/EDA、完整产品程序/数值质量/MEM集成；新系统RTL仍0。系统有外存、当前具体接入暂缓，编译期角色证明与固定有源底座/M11-M12永久选择边界保持。

按rayggxia-project-collab1.0.0回执：成果已上传，本Issue回in_review；P1待独立接收、PR open/未合并，不done。登记management-hub PR5本轮读回open/unmerged→pending；无board.json且当前工具无Projects条目能力，实际卡片/字段unverified、同步pending，管理员待指定；不推断账号权限不足。完整命令/指纹/限制见[checks](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/be10e69bb9ad625079f68361fb47b4747d6ce040/work/Melodydt/151/phase1-checks.json)和PR回执。下一步先审查P1，再进入P2真实控制/最小top，母控ROM骨架并行。

## P2启动与PR144最新RTL同步（本轮授权）

用户明确要求获取PR144最新RTL后开始第二步。开始读回PR144为707878621b2add4ed218b8c43df2e95c9a56e2ba；14核心源逐文件读取，13相同，仅R由旧643实现更新为S128中间量实现（与之前adb819观察点相同），7顶层接口将再次核验。当前研究输入be10e69，沿用本Issue/PR152、task/151-six-connection-study、base task/143-seven-block-v2。独立目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/phase2-be10e69/integrated，为隔离API交付包，不是Git clone；本机git启动DLL错误，旧包和根参考副本保留。

实施范围：P2可综合S普通端口单在途服务、最小S→loader→M→S→T及输出sink顶层、固定ROM母控骨架；独立literal数值、真实握手/背压/重复运行/协调reset与错误测试；不进入P3–P7、不接管#143物理任务或#153 SystemC研究。用户此次明确授权继续P2；P1独立审查/PR合并仍未完成，不把该授权写成已有独立验收。M1–M10固定/有限产品M11-M12永久绑定及外存暂缓边界保持。

验证将在本地尝试真实RTL工具，记录实际版本/日志/指纹。未执行的项目保留未执行。负责人Melodydt；审查人待指定。登记PR5沿用pending待复核；config目录仍无board.json、无Projects条目工具，看板unverified/同步pending，管理员待指定。当前in_progress；最终上传通过原PR、实际检查与回执交付，不done。

## P2首个RTL原型已上传，整体P2验收仍未完成

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)提交1cc43a93a0c985587745ceba5e0d8d425d43a843（父be10e69），原任务分支/基分支不变，非强制fast-forward；44文件白名单、44/44上传blob及额外13个保留核心源读回共57项匹配，ref-project0改动。当前head管理CI41282503498 success。

已同步PR144固定707878621b2add4ed218b8c43df2e95c9a56e2ba的14核心RTL；上传前再次读回PR144仍是该头。13核心不变，仅R从643实现更新为S128临时算术，7顶层149端口兼容；源码更新/编译不授予R数值、周期或最终物理资格，不接管#143。P1旧回执不改写，独立审查仍待完成。

本次新增S普通端口单在途helper、21×16bit固定ROM母控与真实S/loader/M/T顶层，独立TB和复现runner。S8 K8/N8八S64结果经S保存/ACK、T提交/交付/释放后才done；abort为协调同步reset，已接受写/输出不回滚。逻辑声明419bit控制态/336bit程序ROM仅为有限原型，不是原完整64bit ABI或物理结果。

实际本机ModelSim六项工具命令exit0，14核心编译成功，helper6/MST13共19 CASE_PASS；含literal输出、ACK/背压/保持、busy start/done、重复、协调abort/reset、两类真实原生描述符错误与恢复。三个根检查exit0；MST整数参考重放527124条Python断言通过，仍不是RTL条数。没有服务器、系统安装或新EDA/物理任务。

[实施报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/PHASE2_MST_IMPLEMENTATION.md)、[详细验证报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/PHASE2_MST_VERIFICATION.md)、[实际RTL回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/work/Melodydt/151/phase2-rtl-evidence/run-receipt.json)、[检查](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/work/Melodydt/151/phase2-checks.json)和[逐要求矩阵](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/work/Melodydt/151/phase2-verification-status.json)已随本人进度/交接/架构命令同步。

P2整体尚未完成：S16/append/多段/op5/op12/多行错误、A/B独立stall与reuse_b、T全尺寸/非法序列、完整reset/drain矩阵、64bit模板capture/十bank/epoch-credit等保留缺项。P3–P7未开始，完整模型/MEM/物理不宣称通过。下一步补P2缺项和资源反馈，按既定路线继续。

rayggxia-project-collab1.0.0回执：Melodydt；本次部分交付in_review，PR open/未合并，不done，独立审查人待指定。登记management-hub PR5本轮读回open/unmerged→pending；无board.json/Projects条目能力，看板字段unverified、同步pending，管理员待指定；不推断账号权限不足。源码/日志/工具SHA及恢复第一步见PR和交接。

## 粗粒度大Block层次方案研究启动

用户提出新的候选组织：固定底座由多个大Block组成，每个大Block内部组合七类宏并由本地控制器调度，M11/M12只连接大Block，母控调度大操作；大Block类型依据仓库八样本/十层型拆分。用户随后授权涉及仿真可在MobaXterm所连服务器按REMOTE_RULES执行。本轮先研究可行划分、原生能力/资源/数值缺口、本地与母控接口、永久程序绑定及验证路线，不直接改现有RTL或接管#143/#153。

研究输入1cc43a93a0c985587745ceba5e0d8d425d43a843，14核心RTL来源7078786；三份样本算法图文档在当前ref的blob与既有19项来源索引一致。主比较为全七类型同构执行岛及有限子层profile，异构子集和整decoder层封装作为对照；不把profile数当实例数，不假设每层需要一个物理大Block。

任务—分支—目录仍为Issue151 / PR152 / task/151-six-connection-study（base task/143-seven-block-v2）；独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/coarse-block-1cc43a9/integrated，旧P2包/根参考副本保留，无Git HEAD/暂存。本轮未创建服务器目录、上传服务器文件或提交作业；未来仿真计划目录/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue-151/coarse-block/，软件安装/节点/作业命名遵循REMOTE_RULES，不使用他人工作目录。

负责人Melodydt，独立审查人待指定；当前in_progress。验收材料为可追溯的大操作分解、八模型/十层型逐项覆盖、固定有源/定制被动边界、内存与控制活性缺口、P2封装差距及可执行后续验证计划；研究不冒称新RTL/仿真/PPA结果，原P2剩余矩阵保持。

## 粗粒度七宏执行岛候选研究已交付待审查

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)本次提交a37e37cad757af5bfc94ed65db3e2e728023c251（父1cc43a9），原任务分支/base不变，非强制fast-forward；30文件、30/30远端blob与父提交白名单匹配，project/RTL/ref-project0改动，当前管理CI41289449207 success。

研究建议：先以每岛全七类型+本地控制/必要适配的同构岛作参照，母控按A完整Attention、F FFN、D GDN、H Falcon Attention+SSM hybrid、X MoE五子层profile派发；异构子集、整decoder层作对照。保留八样本十层型242层完整序列、全部Norm/残差、96义务；484个逻辑调用不是实例/ROM字数。同一岛可按永久产品程序复用多个层/profile，M11/M12只连接预制粗端点及永久选择，不能新增有源逻辑/启动程序装载。

[总报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/docs/COARSE_BLOCK_HIERARCHY_CANDIDATE.md)、[模型映射](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/docs/COARSE_BLOCK_MODEL_MAPPING.md)、[控制合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/docs/COARSE_BLOCK_CONTROL_CONTRACT.md)、[资源研究](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/docs/COARSE_BLOCK_RESOURCE_STUDY.md)和机器表/复算工具/来源/回执/决策/本人进度/交接已同步。明确单M merged生命周期、S16KiB/T6KiB/R双bank8KiB、GDN/SSM完整状态、NUM/MEM、stored ACK/释放/发布与同岛等待环缺口；无PPA或完整程序准入结论。

六实际静态命令exit0，313模型一致性/57字节单位/17控制算术检查通过；19源文档/配置/导出blob从父ref读取并与继承索引匹配，30文件UTF8/LF/空白通过。这不是新RTL/仿真/活性或物理证明。P2既有19场景仅保留其小核证据，P2剩余矩阵和P3–P7状态不变。

用户授权后续仿真可用服务器，已读REMOTE_RULES；计划路径/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue-151/coarse-block/，软件/Slurm命名和资源按规则。当前未创建服务器目录、上传文件或提交新作业，不接管#143/#153。

rayggxia-project-collab1.0.0回执：Melodydt；部分研究交付in_review，PR open/未合并、不done，独立审查人待指定。登记management-hub PR5本轮读回open/unmerged→pending；无board.json/Projects条目工具，看板unverified、同步pending，管理员待指定，不推断账号权限不足。完整命令与SHA见[checks](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a37e37cad757af5bfc94ed65db3e2e728023c251/work/Melodydt/151/coarse-study-checks.json)。下一步审查功能边界/容量/控制并细化岛壳和双岛验证，不提前冻结物理岛数或声称五profile已实现。

## 按样本确定大Block功能类与宏种类/数量研究

用户要求分析当前仓库样本模型，给出覆盖所需的大Block功能类别，并逐Block明确宏种类与实例数量。本轮继续Issue151/PR152，输入a37e37cad757af5bfc94ed65db3e2e728023c251，叶源7078786；在5个语义子层profile基础上量化普通/带门Attention等资源变体。

交付范围：8模型10层型的功能/配置映射、每Block七宏整数BOM、单实例串行构造与中间值生命周期、并发增配条件、全芯片复用实例数算例、必须另外计入的控制/MEM/NUM/存储/完整推理边界。数量以明确调度和存储前提的参考配置给出，不伪称算法最小、吞吐最优、PPA或当前RTL已完整覆盖。不为每个逻辑层机械复制宏，不因裁剪op忽略跨产品需求并集。

任务分支task/151-six-connection-study，PR152 base task/143-seven-block-v2；独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/block-sizing-a37e37c/integrated，原包/根副本保留，无Git HEAD/暂存。负责人Melodydt，独立审查人待指定。当前in_progress；研究本轮不改RTL、不启动新仿真/服务器作业。用户服务器仿真授权保留，若后续执行按REMOTE_RULES本人目录/安装/Slurm规则，不把计划目录当已部署。

## 大Block功能类与每Block宏数量已交付待审查

[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)提交051fddb9a3d2cecd4b76c43d07ec8581db9402ce（父a37e37c），原分支/base不变，非强制fast-forward；26文件、26/26远端blob与父提交白名单匹配，project/RTL/ref-project0改动，当前管理CI41293290920 success。

给出5语义功能类/6资源变体，按M/N/E/G/R/S/T：A_plain=1/1/1/0/0/1/1（5叶）；A_gate、F、X=1/1/1/1/0/1/1（各6叶）；D、H=1/1/1/1/1/1/1（各7叶）。每物理Block局控另1，全chip母控另1。选择M1串行、S1/T1分片接口并明确MEM/NUM/局控/回放前提；不作数学最小、性能或完整映射承诺，不把所需其它有源能力藏进七宏数。

8模型10层型242逻辑层保留，484调用为A_plain178/A_gate8/F210/D24/H32/X32；A_plain由N自带EXP/E RoPE支持G0，Qwen3.5门控A增G1。单M merged不能交错保留，完整mid/score/状态需保存；H完整7叶或正确owner拆分12叶/2CTRL，一次inputNorm不重复。全chip7/13/32叶是可复用算例，不是要放全部6配方或按层复制；32比五全七包35少3R及48KiB主要bank数组，非面积/同吞吐结论。完整embedding/输出/采样平台另列未闭合。

[BOM总报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/docs/COARSE_BLOCK_MACRO_BOM.md)、[模型数量](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/docs/BLOCK_VARIANT_MODEL_MAPPING.md)、[资源调度](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/docs/BLOCK_RESOURCE_SCHEDULES.md)、[控制归属](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/docs/BLOCK_CONTROL_OWNERSHIP.md)及机器表/工具/来源/决策/本人进度/交接已同步。五实际命令exit0，313模型一致性/20控制计数/资源循环和交叉核验通过，42宏整数三表一致；全部只是静态研究，不作新RTL/PPA或程序准入。

本轮无新仿真/服务器部署或作业，用户服务器授权保留，后续按REMOTE_RULES本人目录执行。P2剩余验收和P3–P7状态不变，不接管#143/#153。rayggxia-project-collab1.0.0回执见PR：Melodydt；本次部分研究交付in_review，PR open/未合并、不done，审查人待指定。登记PR5本轮读回open/unmerged→pending；缺board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。实际命令/输入输出SHA见[checks](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/work/Melodydt/151/block-sizing-checks.json)，下一步按真实MEM/性能目标接收程序和决定增配，不直接冻结此表。

## 六种大Block的连接与同步缺口及实现步骤研究

用户要求明确粗粒度架构是否仍需小宏端口同步、六配置各需哪些连接、当前已有/缺少哪些，以及具体实现步骤。本轮以051fddb9a3d2cecd4b76c43d07ec8581db9402ce为输入，14核心叶源7078786；继续Issue151/PR152，先只做真实RTL/证据审计和研究，不直接实现新RTL或启动仿真。

范围：按A_plain/A_gate/F/D/H/X列逻辑数据依赖与实际物理/存储路由，区分原生端口、legacy组件、当前P2有限组合实测、完整profile/跨岛缺口；不把128bit相同当协议可直连，不要求49条全互联，不将旧V接口或未合入专用bridge当v2整链。整理cmd/rsp、S写ACK、M状态/结果、N回放、G窄流、R状态提交、T批次及跨岛stored ACK/发布等合同，建立实现依赖与验收门，保持原P2–P7路线。

独立目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/island-routes-051fddb/integrated，为隔离API包无Git HEAD/暂存；分支task/151-six-connection-study，base task/143-seven-block-v2。负责人Melodydt，审查人待指定，当前in_progress。其它包/根参考副本、#143/#153代码与服务器作业不接管；ref-project范围不扩大。服务器仿真授权保留，本轮没有新服务器目录/上传/作业。


## 2026-11-01 六配置岛内连接/同步研究交付

- 延续本Issue/PR152，负责人Melodydt；task/151-six-connection-study，base task/143-seven-block-v2；commit bd7cb2f3060c61e5d28a2ece0653dd9336a024af（父051fddb）。[连接主报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bd7cb2f3060c61e5d28a2ece0653dd9336a024af/docs/COARSE_BLOCK_CONNECTION_IMPLEMENTATION.md)及角色/源码/W0–W11附录已上传，25/25远端blob与父提交白名单读回匹配；无RTL/ref-project改动。
- 仍需宏间端口同步，归本地CTRL；母控调子层任务。提出S物化＋capture/gather/serializer并保留Sloader→M。172角色/14类物理hop为需求，不是直连/实现覆盖率。当前v2/P2仅固定MST的原19场景；当前legacy可借但ABI不兼容，PR133桥未入当前树；六完整profile未验收。
- 实际四命令exit0：管理结构、542角色及字节重算、18工作包、178交叉源/证据/范围检查，53当前＋1历史源字节/blob核验；22本地代码文件不变。无新RTL/SystemC/推理/服务器/EDA；旧P2资格不扩大，P2剩余矩阵及P3–P7不变。[检查/SHA回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bd7cb2f3060c61e5d28a2ece0653dd9336a024af/work/Melodydt/151/island-connection-checks.json)；[当前管理CI成功](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/41296524345)。
- 实施先审查W0，再W1共同壳；双岛/MEM边界、E/G与N可并行；完整A/F须N和实际存储，NUM提前，R与MoE分别闭合，X不依赖R。完整产品/程序/MEM/NUM/状态/活性/物理仍缺，未转为done。
- 规则rayggxia-project-collab v1.0.0；登记management-hub PR5本轮open/unmerged，pending；config无board.json且当前无Projects条目工具，看板unverified/同步pending，处理人待指定。独立审查人待指定，PR open未合并，本次部分交付in_review。
- [本人进度](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bd7cb2f3060c61e5d28a2ece0653dd9336a024af/progress/Melodydt/STATUS.md)与[交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bd7cb2f3060c61e5d28a2ece0653dd9336a024af/docs/handoffs/2026-11-01-issue-151-island-connection-route.md)记录分支/隔离API包/首个恢复步骤。后续服务器仿真授权保留、按REMOTE_RULES本人目录执行；本轮服务器无新目录/上传/作业。


## 主线一/W0执行范围与验收（2026-11-01）

按用户要求逐条推进八主线，本轮只实施第一条“固定合同与证据范围”。负责人Melodydt，继续PR152/task/151-six-connection-study，输入bd7cb2f3060c61e5d28a2ece0653dd9336a024af，base task/143-seven-block-v2。独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/contract-lock-bd7cb2f/integrated（非Git clone，无HEAD/暂存），其他会话/旧包保留。

验收交付：①核对PR144最新d1f26884与当前14核心及P2代码来源并记录升级差异，②形成七原生端点的命令/格式/phase/ACK/error/reset/cancel合同，③为既有172角色边逐条指定owner、物化/配对/回放/完成与证据/未来工作包归属，④区分原19场景实测和P2剩余门，⑤定义W1最小可实施合同范围及明确未决项，⑥可复算校验、文档/进度/交接和分支PR读回。未知数值/存储/物理字段保留gap，不填假定通过。

本轮不新增RTL、运行仿真或启动主线二；无服务器目录/上传/作业，不接管#143/#153或ref-project。主线一产物准备完成仍待独立审查，不等于P1/P2全面验收或六完整profile完成。当前in_progress。登记及看板按规则交付时再核验。

## 2026-11-01 主线一/W0交付回执

- 规则rayggxia-project-collab v1.0.0；project_id=llm-hardware-design；负责人Melodydt；优先级待指定。继续PR152/task/151-six-connection-study，base task/143-seven-block-v2；commit bfe62ad179af72aef591622aa5c7a000f5d8b681（父bd7cb2f）。[主线一总报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bfe62ad179af72aef591622aa5c7a000f5d8b681/docs/COARSE_BLOCK_W0_CONTRACT_BASELINE.md)及原生/角色/证据附录、机器合同与脚本已上传，35/35文件远端blob与父提交白名单读回一致。
- 本轮核对PR144 d1f26884的14核心与707逐字节相同，未更新核心/导入整分支/转移物理资格。七宏149端口/24通道、46源码范围/20锚点；P2三RTL/两TB与原实际输入5/5 SHA一致。
- 172目录键完整，新增逐角色owner/shape/domain/lifetime/ACK/phase/未知绑定/验证归属：153适用、14条件、5当前A_gate无source option，不当硬件永久禁连或实现率。原33要求、13 open P2门、20未来测试保留；原19场景不扩大，全部完整角色准入仍false。
- 下一W1最小DOT8入口合同已准备：固定程序/地址/shape，只变数据；有效72B/传128B，56B padding真写零，8写ACK后RUN；必须替换literal S_INIT，frame+RUN16与RUN8笔S事务分开。五组未来向量整数预期已核算，未执行新RTL。
- 六命令exit0：管理、native/角色/证据门重算、47证据/预期检查与414交叉检查；875角色研究检查/准入探针，四份主要合同字节重算一致。五Python AST/UTF8LF通过，22 native/P2代码文件不变；[实际命令/SHA](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bfe62ad179af72aef591622aa5c7a000f5d8b681/work/Melodydt/151/w0-checks.json)；[当前管理CI成功](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/41299489609)。无新RTL/SystemC/模型/服务器/EDA，未执行P2剩余测试或W1接口测试。
- W0合同资料准备待独立审查，不是主线一全部验收、P2完整退出或六profile通过；按用户逐条推进，L2–L8未开始。原CTRL01/02 capture/no-stale义务保留，旧表示取舍待审查。
- 登记management-hub PR5本轮open/unmerged，pending；config缺board.json且当前无Projects条目工具，看板unverified/同步pending，处理人待指定。审查人待指定，PR open/未合并，本次部分交付in_review，不done。
- [本人进度](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bfe62ad179af72aef591622aa5c7a000f5d8b681/progress/Melodydt/STATUS.md)与[交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bfe62ad179af72aef591622aa5c7a000f5d8b681/docs/handoffs/2026-11-01-issue-151-w0-contract-baseline.md)记录隔离API目录和恢复第一步；包外原始源快照不上传。服务器授权保留，本轮无目录/上传/作业。下一步核对W0未决项后再按用户指示进入主线二。


## 主线二/W1首切片开始（2026-11-01）

用户已明确开始主线二。负责人Melodydt；复用PR152/task/151-six-connection-study，输入bfe62ad179af72aef591622aa5c7a000f5d8b681，base task/143-seven-block-v2。隔离API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w1-bfe62ad/integrated（非Git clone，无HEAD/暂存），旧包/其他会话保留。

本轮实现W0给出的W1_FIXED_DOT8_VARIABLE_TENSOR首切片：新数据入口8×128、padding56B硬件清零、8个实际S写ACK后才启动；固定S8 K8/N8/地址/程序/scale，替换literal S_INIT；单S owner、M状态/结果分流、T输出与RELEASE、frame/完成/abort/reset生命周期。新增独立TB和真实RTL仿真，保留并回归原P2证据；记录源码/工具/配置/输入/日志/输出SHA及范围。

验收：五组独立dot8预期精确一致；不完整/未ACK输入不能start；不同frame不串数据、padding非旧RAM；入口/输出/DONE背压稳定；全frame+RUN16与RUN8 S事务、M7/T4及release计数；部分输入/已存未RUN/RUN/DONE的reset/abort与重复恢复。完整W1通用端点/shape、跨岛stored ACK、E/G/N/R/NUM/MEM、完整六profile、物理仍为后续gap，不进入主线三。

当前in_progress；外部W0/PR独立审查仍pending，不冒称整体接受。服务器仿真授权保留，已读REMOTE_RULES；优先复用已可用的合法仿真环境，若服务器使用只在Melodydt本人目录并按Slurm资源规则。无权接管#143/#153或维护ref-project。

## 2026-11-01 主线二/W1首切片交付回执

- 规则rayggxia-project-collab v1.0.0；project_id=llm-hardware-design；负责人Melodydt，优先级待指定。继续PR152/task/151-six-connection-study，base task/143-seven-block-v2；commit 99d6df2e094febe4ea8fc9896301adbbfdc803ed（父bfe62ad）。[实现报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/99d6df2e094febe4ea8fc9896301adbbfdc803ed/docs/W1_MINIMAL_ISLAND_IMPLEMENTATION.md)、2份新RTL/1份TB及文档/日志/索引已上传，54/54远端blob与父提交精确白名单读回一致；22份本地旧native/P2源不变。
- 新block_w1_mst_top接8×128入口、硬件写零56B padding、8实际S写ACK后start；slot2 INPUT_CHECK替换literal S_INIT。入口/RUN共用S helper，M状态/结果分流，T四字take及RELEASE后done，frame忙/完成/复位/abort生命周期明确。固定S8 K8/N8/op/地址/factor1，无runtime配置/程序加载，未改七叶接口/op或制造独立bridge硬宏。
- 实际本地ModelSim2020.4沙箱外运行：原P2回归19CASE；首W1 compile exit2（两声明顺序/4errors）保留；r02 28CASE通过后独立审阅发现DONE同拍计数需强；最终r03 TB178318...强化后28CASE/4422周期、compile/sim0，最终源码与run snapshot SHA一致。[执行/工具/输入/日志SHA](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/99d6df2e094febe4ea8fc9896301adbbfdc803ed/work/Melodydt/151/w1-execution-index.json)；[最终原始日志](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/99d6df2e094febe4ea8fc9896301adbbfdc803ed/work/Melodydt/151/w1-rtl-evidence/w1-r03/simulation-block_w1_mst_tb.log)。
- 正常帧逐次检查S16req/16ACK（入口8/RUN8）、M7cmd/rsp、loader一次/T4take+release。全程abort/reset有意丢弃在途差额已逐项解释，不能写全局无条件守恒。28为检查标记而非28独立完整任务。五输入/极值/非均匀、dirtyRAM、未ACK启动屏蔽、背压/两帧/关键reset-abort/DONE同拍和原生EXEC错误恢复均有限覆盖。
- 后置管理和137项证据检查exit0，2Python AST/源/doc/JSON LF通过；[当前管理CI成功](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/41304951075)，不替代RTL/物理。[独立源码与根执行证据审阅](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/99d6df2e094febe4ea8fc9896301adbbfdc803ed/docs/W1_MINIMAL_ISLAND_REVIEW.md)14门无open blocker，代理未运行sim、该审阅不是外部PR批准。
- 只交付主线二最小切片；完整W1/gather/serializer/shape、E/G/N/R、跨岛stored ACK、NUM/MEM/产品程序/活性/物理与P2剩余门仍未接收，主线三及后续未开始。W0外部独立审查保持pending，不接管#143/#153或ref-project。
- 本次部分交付in_review；PR open未合并，外部审查人待指定，不done。登记management-hub PR5本轮open/unmerged，pending；config无board.json且当前无Projects条目工具，看板unverified/同步pending，处理人待指定。本人进度和[交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/99d6df2e094febe4ea8fc9896301adbbfdc803ed/docs/handoffs/2026-11-01-issue-151-w1-minimal-island.md)已更新。
- 本轮使用现有本地工具，无安装/PATH/license或凭据查看；服务器授权保留，本轮无服务器目录/文件上传/作业。包外源快照/仿真二进制不上传，早期不同W1源作为小型证据附件保留。恢复先核当前Issue/PR与w1-index/最终r03 SHA，审查后按用户安排扩展。


## 主线三/W3开始（2026-11-01）

用户明确开始下一主线：E/G端点适配与FFN8基础核。负责人Melodydt，继续PR152/task/151-six-connection-study，输入99d6df2e094febe4ea8fc9896301adbbfdc803ed，base task/143-seven-block-v2，native707。独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w3-99d6df2/integrated（无Git HEAD/暂存），代理草稿分目录，旧包/其他任务保留。

范围/验收：先固定有界数值profile：x/Wgate/Wup/Wdown S8 Fin7；gate/up M op5 S16 RNE4→Fin10；G SiLU×up RNE10/clipS16；down M A16/B8 op5 RNE7→Fin10；E shift残差与ADD。输入16×128实际写ACK，S448..473有界布局，单S helper owner；E gather按op所需A/B/C、E12/13布局/舍入/tail；G 128↔32拆并、双源/计数/在途/写ACK门。新FFN8top无host opcode/address/shape配置；saturation独立于error，程序固定。独立整数reference/源LUT验证、多向量逐阶段与最终RTL对照、背压/错误/复位/重复及原P2/W1回归。正常参考32笔S(26写6读)、15Mcmd/rsp、3loaders、T1word/release，实际实现若变需更新可审查合同不编造通过。

本轮不接N，不将FFN8核称完整F；一般跨岛/MEM/NUM/完整产品/物理与旧P2剩余门保持。W0/W1外部审查仍pending，不自行合并，不接管#143/#153/ref-project。服务器授权保持、已读REMOTE_RULES；优先现有本地ModelSim，若服务器使用按本人目录/Slurm。当前in_progress。

## W3 有限切片交付（2026-11-01）

当前提交：0101cc7e1e6d5718455fb45b61c7428439efc09a；[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)。本次交付新增E/G外部适配器及固定FFN8本地序列，非完整F；覆盖与未完成项以[报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0101cc7e1e6d5718455fb45b61c7428439efc09a/docs/W3_EG_FFN8_IMPLEMENTATION.md)和[实际执行索引](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0101cc7e1e6d5718455fb45b61c7428439efc09a/work/Melodydt/151/w3-execution-index.json)为准。主线四及后续未开始。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id=llm-hardware-design；https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人Melodydt
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；commit 0101cc7e1e6d5718455fb45b61c7428439efc09a；70文件已上传并逐Git blob SHA读回；个人进度 https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0101cc7e1e6d5718455fb45b61c7428439efc09a/progress/Melodydt/STATUS.md
验证：管理结构PASS；独立整数/数学LUT2564节点PASS；六向量/两TB再生成逐字节一致；ModelSim最终FFN21检查/7524周期、adapter46/2231、P2/W1回归47检查均真实exit0；证据复核PASS；原25个project文件未改
登记：pending；management-hub PR5本轮读回open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：unverified；远端config无board.json，现有工具无Projects item读写能力；同步pending，处理人待指定。不得将Issue标签更新当作看板已同步
审查与状态：外部审查人待指定；PR open/unmerged；Issue151 in_review，非done
下一步：外部审查及一般退出门；随后按用户节奏进入L4 N归约/统计/回放；看板处理人待指定，继续入口 https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0101cc7e1e6d5718455fb45b61c7428439efc09a/docs/handoffs/2026-11-01-issue-151-w3-eg-ffn8.md
核验时间：2026-11-01 13:37:24 UTC
```


### 本轮最终在线核验补充

当前head管理结构CI [41312013653](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/41312013653) completed/success，仅验证管理结构。全部70文件读回SHA一致，父提交99d6df2→0101cc7e1e6d5718455fb45b61c7428439efc09a远端compare恰为70文件、ahead1/behind0。

PR152当前GitHub mergeable=false/mergeable_state=dirty。本轮开始时head99d6df2已同样为dirty，因此是既存基分支合并冲突；本次不把上传完成写成可直接合并。需要在后续独立处理基分支三方同步/冲突，保留研究与上游成果，未批准前不自合并；处理人Melodydt，外部审查人待指定。本次测试仍绑定所列固定源与输入SHA，不转移到尚未整合的新基线。正式交接入口及本Issue回执均应在恢复时读取。登记PR5最终读回仍open/unmerged；远端config仍只有labels/status-mapping，看板unverified/同步pending。


## 主线四启动（2026-11-02，Asia/Shanghai）

用户明确授权开始L4（W4 N端点阶段/回放及W5 A/F纵向集成）。负责人Melodydt；复用本Issue/PR152，研究head0101cc7e1e6d5718455fb45b61c7428439efc09a，base task/143-seven-block-v2/PR144 d1f26884。独立API工作包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w4-0101cc7/integrated；草稿按nctrl/oracle/f8/baseline分目录，原包/其他会话保留。

执行顺序：先三方核对并处理既存基分支冲突，固定源；实现外侧N controller，真实S+helper的RMS/L2/Softmax1..257有界服务，明确BEGIN/STATS/FINALIZE/EXP原码保存回放/gamma/目标计数/持组、最后实际写ACK及错误poison/reset；独立整数oracle与真实RTL仿真（包含Softmax257末项新max/tail1/33字）；新增有界F8 preNorm门，把N Fin10→RNE3/clipS8 Fin7的真实转换和original X残差分别保活；保留并回归原P2/W1/W3。固定程序与地址，数据/权重可变；不改叶宏/旧验证模块，不接管#143/#153/ref-project或服务器作业。

验收须以每个实际新增服务/链和数值profile分别列证据；有界Norm-F8不是完整F/A或样本真实尺寸/质量。完整A的QK/Softmax/PV、真实大shape容量映射/NUM/MEM及全产品PPA仍须独立闭合，不以本轮小切片提升整个L4或Issue为done。服务器授权保留，优先现有本地ModelSim；若实际使用服务器严格按REMOTE_RULES本人目录和Slurm。当前in_progress；外部审查、登记pending/看板unverified同步pending保持，最终按规则读回交付。


## 主线四首批有界交付（2026-11-02）

基线同步commit0e8e970（双父01+d1）已解决既存冲突；当前业务commit1d722477564e14f7dc93e39ce8e28b8e2d150cb0，[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152) readback clean/mergeabletrue、未合并。交付N单组RMS/L2/Softmax1..257服务及RMS-preNorm F8，完整L4/W5/A/F不标完成。[报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1d722477564e14f7dc93e39ce8e28b8e2d150cb0/docs/W4_N_F8_IMPLEMENTATION.md)、[实际执行索引](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1d722477564e14f7dc93e39ce8e28b8e2d150cb0/work/Melodydt/151/w4-execution-index.json)和[继续入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1d722477564e14f7dc93e39ce8e28b8e2d150cb0/docs/handoffs/2026-11-02-issue-151-w4-n-f8.md)为准。旧实现/证据保留；L5–L8未开始。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id=llm-hardware-design；https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人Melodydt；优先级/外部审查人待指定
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；baseline merge0e8e970359452b745cde09f77efeac041df5fd10（01+d1），业务commit1d722477564e14f7dc93e39ce8e28b8e2d150cb0；73/73文件blob读回与相对merge0e的73文件白名单一致；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1d722477564e14f7dc93e39ce8e28b8e2d150cb0/progress/Melodydt/STATUS.md
验证：本地ModelSim N29检查/20336周期，F8 25/16323，原P2/W1 47＋W3 67共114回归，compile/simulation均exit0；7项后置命令PASS，数学EXP1025/G2564、全65536S16窄化与独立整数参考及两向量/两TB重新生成逐字节一致；28份旧RTL/include/TB不变
登记：pending；management-hub PR5最终读回open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：unverified；远端config只有labels/status-mapping，无board.json且工具无Projects item读写；同步pending，处理人待指定，未证实权限拒绝
审查与状态：PR open/unmerged且clean/mergeable=true（2026-11-01 16:52:42 UTC读回），外部审查人待指定；Issue151 in_review，非done；代理互查不等于外部批准
下一步：继续L4完整F/A与真实shape/尺度/容量映射，TopK/多组/MEM/NUM/物理等独立门；L5–L8未开始；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1d722477564e14f7dc93e39ce8e28b8e2d150cb0/docs/handoffs/2026-11-02-issue-151-w4-n-f8.md

```

## 后续仿真执行约束（用户2026-11-02确认）

用户明确要求：接下来的仿真全部使用服务器，服务器使用Verilator，文件必须按项目规则放置。此约束取代“优先本地ModelSim”的历史安排，后续接续先读本节。

- 新RTL仿真及回归统一在服务器Verilator执行；不自行回退本地ModelSim。已有ModelSim回执保留其真实历史来源，不能改写成Verilator通过。Python参考/管理/静态检查与RTL仿真分别记录。
- 遵守docs/REMOTE_RULES.md：登录目标yuzelu@10.129.166.172，本人主要工作、源码快照、编译输出、日志、结果和必要波形均放/public/home/yuzelu/Melodydt/下，按项目/Issue/commit/独立run分目录；具体任务子目录在首次运行前记录并核验。本节未声称已创建目录或上传文件。
- 通过Slurm sbatch提交。作业名用本人姓名缩写-任务缩写，实际姓名缩写首次提交前核实，不借用他人前缀；节点/CPU/内存/时限按队列与REMOTE_RULES分配，累计用核不超实际分配。不修改/取消其他成员作业或使用其个人目录。
- 复用服务器已安装Verilator；首次执行先读回实际Verilator、C++编译器和配置版本，核验现有TB时序/故障注入兼容性，保留验证覆盖。只有实际完成服务器运行并核对数值、握手、完整CASE、退出码和PASS后，才记录Verilator通过。
- 每轮记录源commit/逐文件SHA、脚本/完整命令/工具与配置版本、输入版本/固定向量或seed、Job ID、退出状态、输出位置及SHA-256；失败尝试和旧版本保留。大体积编译库/波形保留获授权服务器目录，仓库留索引和小型文本证据。
- 独立SSH上次只读检查发现22端口可达但缺已核验主机密钥，登录未建立；本次没有重试登录、导出凭据或修改主机信任。下一次仿真先复核可信连接与认证；未就绪时记录具体阻塞，不冒称服务器已部署/运行，也不静默改用本地仿真。
- 当前未启动新仿真或服务器作业，未安装软件；已有PR152/W4结果及审查状态不变。继续技术工作仍按L4的A/F路径推进，本节不擅自启动下一条主线。

执行约束登记回执：
规则版本rayggxia-project-collab1.0.0；项目llm-hardware-design；Issue151/负责人Melodydt；复用PR152（head1d722477564e14f7dc93e39ce8e28b8e2d150cb0，open未合并）。本次仅更新Issue执行约束，无文件修改/新增commit/PR。验证：已读Skill、REMOTE_RULES，核验本人身份、Issue/PR/config及登记PR；python scripts/check_project.py管理PASS，不是RTL验证；未执行Verilator仿真。登记management-hub PR5读回open/unmerged→pending；config无board.json，工具无Projects item能力，看板unverified/同步pending，处理人待指定；未证实权限拒绝。Issue保持status:in_review，不done，不变更看板事实。核验时间2026-11-02 03:43:15 UTC。下一步：建立可信服务器连接、记录实际工具版本与任务目录，再按用户后续指示执行服务器Verilator任务。



## 继续主线四：有界 Attention QK–Softmax–PV（2026-11-02）

用户澄清本次继续L4的Attention计算链，不进入L5。负责人Melodydt，复用Issue151/PR152/task/151-six-connection-study，输入head1d722477564e14f7dc93e39ce8e28b8e2d150cb0，base task/143-seven-block-v2。独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/a8-1d72247/integrated；无本地GitHEAD/暂存，旧包/根管理副本和他人文件保留。

本轮范围：一query/head，8key、D8、8channel，M/N/S/T各1，固定地址/程序，输入12×128bit可变Q/K/V。Q/K/V S8Fin7，QK factor11585/left0、M RNE19至S16Fin10；N精确U16 EXP保存回放、概率Q14；PV A16×B8 RNE11至S16Fin10。M装载基址4word对齐；score460/exp461/prob464/pad465..467/output468。复用不变W4 Nctrl，不改七叶接口或op，无新bridge硬宏。

验收：独立整数参考和逐score/EXP/prob/output对照，输入ACK启动门、各级背压、正常S23(19W4R)/M10/N6/loader2/T1+RELEASE、两帧/错误/协调reset-abort/DONE保持；服务器Verilator实际执行和完整CASE/工具/JobID/逐文件SHA追溯。用户已给本人服务器作业前缀zenanyan，所有源码/编译/日志/结果放/public/home/yuzelu/Melodydt/并经sbatch。当前独立SSH缺可信hostkey，GUI暂未见Moba窗口，正在核对连接；不回退本地RTL仿真，未开始服务器作业。

此切片不包括QKV/output投影、preNorm/RoPE/GQA/mask/多head、真实模型shape容量映射、MEM/NUM/物理，不称完整A或完整L4通过。外存仍保留灵活性。当前in_progress；PR外部审查待指定，登记PR5 pending；无board.json/Projects item工具，看板unverified、同步pending、处理人待指定。此处Issue标签不是看板同步证据。


## 2026-11-02 主线四A8 Attention切片交付

新增M/N/S/T各1的8key/D8 QK–Softmax–PV内核与独立26CASE TB，复用不变Nctrl/helper/原生。QKV S8Fin7、score Fin10、概率Q14、PV Fin10；S464 loader对齐及真实写ACK门明确。本轮102文件已通过任务分支上传，源码/工具/输入/原始日志/失败尝试追溯完整；[八主线和进度](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/714cab4fda64c8e5cdd74c57ae8bc704e4902981/docs/COARSE_BLOCK_RESEARCH_PROGRESS.md)、[实现](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/714cab4fda64c8e5cdd74c57ae8bc704e4902981/docs/W4_A8_IMPLEMENTATION.md)、[服务器验证](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/714cab4fda64c8e5cdd74c57ae8bc704e4902981/docs/W4_A8_VERIFICATION.md)。

服务器Verilator5.042真实95116成功，N29/F825/A826共80项；32继承SV/SVH不变；98 warning全保留，功能通过非lint clean。仅有界内核，不把完整A/F/L4、真实模型质量/形状、MEM/物理标完成，不启动L5。外部审查待指定，不自合并、不done。现有独立SSH与Slurm已工作，不依赖Moba窗口；新仿真仍限服务器Verilator与本人目录。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id=llm-hardware-design；https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人/认证Melodydt；优先级待指定
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；commit 714cab4fda64c8e5cdd74c57ae8bc704e4902981（父1d722477564e14f7dc93e39ce8e28b8e2d150cb0）；本轮102文件逐Git blob读回和父子compare精确白名单一致（ahead1/behind0）；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/714cab4fda64c8e5cdd74c57ae8bc704e4902981/progress/Melodydt/STATUS.md
验证：服务器Slurm95116/c64/node1/8CPU/1m51/COMPLETED0:0，Verilator5.042，N29/F825/A826共80完整唯一CASE，3build/3sim均0；独立数学EXP1025、8vector与4生成文件逐字节复现、管理检查、184项源/日志/工具/CASE证据及242项独立复核PASS；32继承SV/SVH不变；当前head管理CI成功https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/41399265925，仅管理结构
登记：pending；management-hub PR5本轮读回open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：unverified；远端config只有labels/status-mapping、无board.json且当前无Projects item工具；同步pending，处理人待指定。Issue标签不是看板同步；未证实权限拒绝
审查与状态：PR open/unmerged且当前clean/mergeable=true；外部审查人待指定，Issue151 in_review，非done
下一步：负责人Melodydt继续L4模型实际Attention完整流程/数值布局与真实shape容量映射；完整A/F/L4、MEM/产品程序/物理未验收；L5–L8未开始。恢复入口https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/714cab4fda64c8e5cdd74c57ae8bc704e4902981/docs/handoffs/2026-11-02-issue-151-a8-attention.md
核验时间：2026-11-02 06:24:01 UTC
```


## 2026-11-02 三层互联边界归入八主线（计划修订开始）

用户要求把“母控—功能岛、岛间、岛内在M11/M12定制前如何连接”归入研究主线并安排实施。负责人Melodydt；复用Issue151/PR152/task/151-six-connection-study，输入714cab4fda64c8e5cdd74c57ae8bc704e4902981，base task/143-seven-block-v2。独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/control-boundary-714cab4/integrated（非Git checkout，无HEAD/暂存）；旧A8包/根管理副本/他人文件保留。

本轮仅更新计划、proposed决策和交接：L4前置W5-IF逻辑接口/ACK/资源边界合同；L5/W2实现拟定固定母控控制网和双岛存储确认，W6扩一般拓扑；L6/7复用并补状态/动态事件；L8/W11实际接收共同底座和M11/M12产品物理差分。主候选为固定母控控制网、模型相关数据网后定制，尚未冻结或实现。物理pin/扇出/中继/资源约束前置，不等待最终阶段才反馈。

验收：三层连接归属和交付/依赖/退出门清楚；合同/RTL/物理三类证据分开；现有8主线编号与历史A8证据不改写；计划、机器索引、本人进度/交接一致并经PR交付。无RTL变更、无新仿真/服务器操作，不以计划修订冒称L5实现开始。后续服务器继续独立SSH+Slurm+Verilator和本人目录，Moba不是执行依赖。当前本次计划编写in_progress；登记PR5 pending，config无board.json/Projects item工具，看板unverified/同步pending、处理人待指定。


## 2026-11-02 三层互联主线安排交付

已完成计划归类：L4/W5-IF先编接口/事件/ACK/资源/层边界合同；L5/W2-C母控固定控制网、W2-D双岛stored ACK及源释放，W6扩一般拓扑；L6/7补状态/动态事件；L8/W10真实MEM可并行起步，W11最终产品与物理验收。固定控制网仍proposed，具体接口合同未完成，不将计划提交视为L5 RTL开始。[实施安排](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f9a90c845504b198cc3265106e03c67902382ebb/docs/COARSE_BLOCK_INTERCONNECT_BOUNDARY_PLAN.md)、[八主线进度](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f9a90c845504b198cc3265106e03c67902382ebb/docs/COARSE_BLOCK_RESEARCH_PROGRESS.md)。本次不新增仿真/服务器操作，原A8证据不变。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id=llm-hardware-design；Issue151；负责人/认证Melodydt；优先级待指定
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；commit f9a90c845504b198cc3265106e03c67902382ebb（父714cab4fda64c8e5cdd74c57ae8bc704e4902981）；本轮13份MD/JSON逐Git blob读回且父子compare精确白名单一致、ahead1/behind0；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f9a90c845504b198cc3265106e03c67902382ebb/progress/Melodydt/STATUS.md
验证：根参考及独立包python scripts/check_project.py PASS；JSON语法、UTF8/LF/空白、新增相对链接、文档修改范围和旧索引保留检查PASS；计划交叉审阅后明确W10可并行起步及历史/A8输入区分；https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/41404030566为本head管理结构CI成功。未改RTL，未执行新RTL/SystemC/服务器/EDA，不转移历史A8资格
登记：pending；management-hub PR5最终读回open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：unverified；config只有labels/status-mapping，无board.json且工具无Projects item能力；同步pending，处理人待指定，未证实权限拒绝
审查与状态：PR open/unmerged、当前clean/mergeable=true；外部审查人待指定，Issue151 in_review，非done。计划已形成，具体接口合同/RTL/物理未完成
下一步：Melodydt继续L4先编W5-IF有界端口/事件/ACK/资源/层边界表；L5/W2_C_D/W6做主要RTL，L8/W10_W11真实系统与物理；L5 RTL未开始。https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f9a90c845504b198cc3265106e03c67902382ebb/docs/handoffs/2026-11-02-issue-151-interconnect-boundary.md
核验时间：2026-11-02 07:07:41 UTC
```


## 2026-11-02 继续L4：W5-IF接口合同开始

用户要求继续主线四；按f9a90c8计划先完成W5-IF三层端口/事件/ACK/资源合同，不启动L5RTL。负责人Melodydt；沿Issue151/PR152/task/151-six-connection-study，输入f9a90c845504b198cc3265106e03c67902382ebb。独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w5if-f9a90c8/integrated，无.git/HEAD/暂存；旧包/根参考及他人文件保留。

范围：真实MST/A8/F8端口与帧/数值/残差边界、母控粗任务与跨岛fragment/目的storedACK/source release/错误partial/复用、唯一owner与重复晚事件/协调reset、有限样本扩展与参数化逻辑bundle/物理pin预算。形成完整producer→consumer成功/背压/故障时序；current/proposed/gap分别标，不编造全产品固定总线或物理冻结。无RTL修改或新仿真，必要后续运行仍限服务器Verilator/Slurm/本人目录。当前in_progress，外部审查待指定；登记pending/看板unverified同步pending。


## 2026-11-02 W5-IF有界逻辑合同v0.1交付

已形成三层任务/数据/独立storedACK/源释放/复用/错误partial合同、真实native接口/适配审计与8样本6profile准入边界。B8一母控两岛一字16B仅待实现协议例；A8/F8不能裸接，完整A/F数值/容量/供参仍GAP。当前继续L4，L5RTL未开始。本轮未改RTL或运行新仿真/服务器。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design；https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人Melodydt，认证Melodydt
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；commit febc0428e9d47d9bb4d4c83446690ff2e0c7926d；task/151-six-connection-study → task/143-seven-block-v2；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/febc0428e9d47d9bb4d4c83446690ff2e0c7926d/docs/W5_IF_INTERFACE_CONTRACT.md；个人进度https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/febc0428e9d47d9bb4d4c83446690ff2e0c7926d/progress/Melodydt/STATUS.md
验证：python -B -X utf8 scripts/check_project.py PASS；python -B -X utf8 scripts/check_w5_if.py PASS465项静态文档/来源/字段/算术；包级JSON/LF/新增相对链接/白名单/历史索引检查PASS；33份输入Git blob对齐f9a90c8，parent...head精确25文件逐blob读回一致；head两项Project structure CI success（41411091689/41411082191），仅管理结构
未执行：新RTL仿真/服务器/EDA，因本轮未改RTL；协议安全/活性、完整模型质量和共同底座物理验收未验证。旧A8 job95116仅原源/原范围
登记：pending；management-hub PR5仍open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：实际状态unverified、同步pending；本轮config仅labels/status-mapping，无board.json；GitHub工具无Projects item/字段能力；处理人待指定，未证实权限拒绝。待有配置/能力者核条目并同步Project ID/Status/Priority后读回
审查与状态：PR open/unmerged，外部审查人待指定；内部交叉检查不是外部批准；Issue151本轮交付转in_review，非done，未合并main
下一步：Melodydt继续L4完整A/F数值/残差/layout与有界Norm/容量/参数供给；L5再实现端点/母控/跨岛storedACK，L8最终MEM与共同底座/M11-M12验证。https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/febc0428e9d47d9bb4d4c83446690ff2e0c7926d/docs/handoffs/2026-11-02-issue-151-w5-if-contract.md
核验时间：2026-11-02 08:11:39 UTC
```


## 2026-11-02 继续L4：F16有界数值/残差路径

负责人Melodydt；复用Issue151/PR152/task/151-six-connection-study，输入febc0428e9d47d9bb4d4c83446690ff2e0c7926d。独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/f16-febc042/integrated，无.git/HEAD/暂存；旧包与根参考、他人资料保留。先新增H8/I8 F16：X/原始残差S16Fin10、可变gammaS16Fin10、三权重S8Fin7；N结果保留S16进入M宽A；独立数学golden及服务器Verilator验证数值/背压/取消/错误/复用。旧F8/A8与native叶字节保留。同时给完整A/F数值/存储/供参及Attention缺项路线。此阶段不启动L5跨岛端点/母控，不声称完整样本模型质量/物理准入。验收为所选有界profile的RTL与独立期望逐阶段/最终结果相符、生命周期/真实ACK可核验，提交源commit/工具与日志SHA及结果索引。当前in_progress；外部审查待指定，登记pending/看板unverified同步pending。


## 2026-11-02 F16有界完整FFN交付

S16Fin10 hidden/原残差及可变gamma、宽A投影的新F16 H8/I8已通过服务器Verilator完整30CASE。仍L4，完整A/F/实际样本质量与规模/供参未验收；下一A16因果候选，L5未启动。首轮编译失败与后续单行修复、完整证据均保留。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design；https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人/认证Melodydt
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；交付commit f665230a392cbcf2422594167e1f163d5e5d1c80；通过源码b77d6b7bae17e265bf20509e9ea53c1cdc5c4c9d；task/151-six-connection-study → task/143-seven-block-v2；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f665230a392cbcf2422594167e1f163d5e5d1c80/docs/W4_F16_IMPLEMENTATION.md；个人进度https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f665230a392cbcf2422594167e1f163d5e5d1c80/progress/Melodydt/STATUS.md
验证：服务器Verilator5.042，job95209/node1/c64/8CPU，Slurm COMPLETED0:0；build/sim0；30预声明CASE各一次exactPASS。10独立数学向量逐阶段/最终结果；生成重现及Python数学检查通过。25输入SHA及23文本/下载archive SHA核对；旧34RTL/TB/include字节不变；新源10文件、单行fix1文件、最终49文档/证据逐blob远端读回。check_project及W5-IF静态check通过，包级JSON/LF/新增链接/来源/完整CASE/SHA/历史索引检查PASS；head两项Project structure CI success（41418763540/41418756953），仅管理检查
失败/限制：95206/63ce0f3d在lex compile失败，无sim，失败源/日志保留；b77d只补三目表达式空格。24warnings保留，仅-Wno-fatal，非lintclean；不构成完整A/F/样本模型数值质量、跨岛或物理验收。无本地RTL仿真，L5未开始
服务器：yuzelu@10.129.166.172；/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/f16-febc042-20261102/input-r02；结果runs/r02；日志slurm/zenanyan-f16-95209.out/.err；脚本/完整参数/Slurm账目与SHA见f16-rtl-evidence。作业已结束，无自动监测
登记：pending；management-hub PR5仍open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：实际状态unverified、同步pending；config无board.json，工具无Projects item/字段能力；Status映射In review已读，处理人待指定，未证实权限拒绝。待配置/能力者核条目并同步Project ID/Status/Priority后读回
审查与状态：PR open/unmerged，外部审查人待指定；内部独立复核不是外部批准；Issue151本轮转in_review，非done，未合并main
下一步：Melodydt继续L4有界A16 H8/Sq2/head1完整因果Attention（preNorm/QKV/RoPE/前缀Softmax/PV/Wo/原X残差），以及模型epsilon/质量/真实H/I容量与供参门；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f665230a392cbcf2422594167e1f163d5e5d1c80/docs/handoffs/2026-11-02-issue-151-f16.md
核验时间：2026-11-02 09:13:56 UTC
```


## 2026-11-02 继续L4：有界完整A16因果Attention开始

主要负责人Melodydt，复用Issue151/PR152/task/151-six-connection-study；输入f665230a392cbcf2422594167e1f163d5e5d1c80。独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/a16-f665230/integrated，无.git/HEAD/暂存，旧包/根参考/其他成员和ref-project不改。范围H8/Sq=Sk2/head1、无bias/cache：S16Fin10 hidden/可变gamma、QKV投影、pair-interleaved RoPE系数S16Fin14、因果N前缀count1/2、PV/Wo/原X残差；27输入帧/2输出。复用M/N/E/S/T，真实S矩阵布局转换与局部owner/FSM，不增L5网络。验收为独立数学golden逐阶段/最终两行值、因果前缀、真实ACK/背压/取消/故障/复用的服务器Verilator CASE与固定源码/工具/输入输出SHA证据。完整模型GQA/QKnorm/位置/epsilon/精度及物理/MEM/跨岛仍GAP。当前in_progress；外部审查待指定、登记pending/看板unverified同步pending。


## 2026-11-02 A16有界完整因果Attention交付

源a32e5f1a61d137e9e2338b7717b66d5c18085351、服务器95235/node1首次r01实际30CASE通过，补齐preNorm/QKV/RoPE/因果Softmax/PV/Wo/原S16残差。保留旧A8/F16；仍L4，真实样本量化/shape/供参、A/F真实端点和L5/物理未接收。所有源/证据范围、归档助手重试与未完成项见下回执。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design；https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人/认证Melodydt
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；交付commit cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6；实际通过源码a32e5f1a61d137e9e2338b7717b66d5c18085351；task/151-six-connection-study → task/143-seven-block-v2；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6/docs/W4_A16_IMPLEMENTATION.md；个人进度https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6/progress/Melodydt/STATUS.md
验证：服务器Verilator5.042，job95235/node1/c64/8CPU，Slurm COMPLETED0:0，build/sim0；30预声明CASE各一次exactPASS。独立10组数学golden逐阶段/双输出，Python1877断言及空目录重建一致；23输入SHA/12文本证据SHA/下载archive SHA核对；原36RTL/TB/include字节不变。10新源及最终38文档/证据逐blob远端读回一致；check_project及W5-IF静态check/包级JSON/LF/新增链接/来源/CASE/SHA/历史索引PASS。head两项Project structure CI success（41427396102/41427387551），仅管理检查
范围与限制：H8/Sq2/head1/无bias/cache，S16Fin10 hidden/原残差+S8Fin7权重+adjacentpair RoPE。真实H/GQA/QKnorm/布局/位置/epsilon/量化质量/供参、A16-F16真实端点/跨岛及物理未接收；仍L4，L5未开始。36warnings原文保留、仅-Wno-fatal，非lintclean，无本地RTL运行
服务器：yuzelu@10.129.166.172；/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a16-f665230-20261102/input-r01；结果runs/r01，日志slurm/zenanyan-a16-95235.out/.err，脚本/完整参数和Slurm账目已入证据。实际首轮r01通过；c01→c02仅修复归档助手Path拼接，仿真输入/结果未改。作业已结束，无自动监测
登记：pending；management-hub PR5仍open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：实际状态unverified、同步pending；任务分支config无board.json且工具无Projects item/字段能力；Status映射In review已读，处理人待指定，未证实权限拒绝。需有配置/能力者核条目后同步Project ID/Status/Priority并读回
审查与状态：PR open/unmerged，外部审查人待指定；内部独立复核不是外部批准。Issue151本轮转in_review，非done，未合并main
下一步：Melodydt继续L4真实样本数值/shape/存储/供参准入及A/F边界衔接；L5母控/端点/storedACK及共同底座物理独立推进。https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6/docs/handoffs/2026-11-02-issue-151-a16.md
核验时间：2026-11-02 10:17:13 UTC
```


## 2026-11-02 继续L4：样本准入与A/F纵向边界

主要负责人Melodydt，复用Issue151/PR152/task/151-six-connection-study；输入cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6。隔离API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/af16-cd8dfc9/integrated，无.git/HEAD/暂存，保留旧包/根参考/其他成员和ref-project。两项：基于8真实样本shape/算法/数值/容量/供参生成可执行offline准入表，未知/不满足明确拒绝，不缩H8假准入；新增固定AF16纵向验证顶层，将A16两行结果真实FF保存并分别组装F16帧（F权重/gamma独立bank两行复用），40输入/2输出，父终态覆盖子未启动或填帧取消。旧A/F/native不改。验收独立composition golden、边界bit保留/参数生命周期/真实ACK与子DONE释放、错误/背压/reset服务器Verilator与源码/日志/SHA；静态准入ALLOW只限synthetic有界profile，不构成模型质量/物理验收。此顶层不冻结AF新产品岛、不冒称L5通用母控/peerACK。当前in_progress；登记pending/看板unverified同步pending，外部审查待指定。


## 2026-11-02 固定AF纵向衔接与八模型准入交付

AF16 fixed verifier源码a37df8be480d6472627a11419777511042af6a60、服务器95242/node1首r01实际33CASE通过；A/F边界位保留、参数生存期、独立父终态和metadata/sat隔离已落实。8真实模型×3target静态结论保留原尺寸均GAP、数值质量UNKNOWN，不假准入；下一实际Qwen3 F H1024/I3072给出数值/N-long/完整归约/存储与9MiB供参实施门。仍L4，非L5通用网络/全模型/物理验收。

```text
规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design；https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人/认证Melodydt
成果：https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152；交付commit 75d99a5ba01adba1e978db3933a41e1d43c49c30；实际通过源码a37df8be480d6472627a11419777511042af6a60；task/151-six-connection-study → task/143-seven-block-v2；https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/75d99a5ba01adba1e978db3933a41e1d43c49c30/docs/W4_AF16_IMPLEMENTATION.md；个人进度https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/75d99a5ba01adba1e978db3933a41e1d43c49c30/progress/Melodydt/STATUS.md
验证：服务器Verilator5.042，job95242/node1/c64/8CPU首r01 COMPLETED0:0，build/sim0，33预声明CASE各一次exactPASS；独立10组composition golden/Python485断言及空目录重建一致。30运行输入SHA/12文本SHA/archive SHA核对；旧38RTL/TB/include字节不变。10新源及39最终文档/证据逐blob远端读回；check_project/W5-IF静态/包级JSON/LF/链接/来源/CASE/SHA/历史索引PASS。head两项Project structure CI success（41435958755/41435948498），仅管理结构
静态准入：formal checker exit0，22既有源+wrapperSHA、24literal正反例、八模型×A16/F16/AF16=24真实结论核对；仅synthetic有界ABI1项ALLOW，真实全部GAP、数值质量UNKNOWN保留。Qwen3 AF16实际原生exit2/GAP、H1024/I3072，正确拒绝；无缩形准入。静态判断不是RTL/模型质量/物理验收
范围限制：H8/Sq2/I8固定AF纵向验证，40输入/2输出，240Bholding/独立父终态；不新增AF产品岛冻结，不冒称L5通用母控/peerACK。实际H/I/GQA/Norm/RoPE/epsilon/质量/供参及共同底座物理未接收，仍L4，L5未开始。30warnings全留仅-Wno-fatal，非lintclean，无本地RTL运行
服务器：yuzelu@10.129.166.172；/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af16-cd8dfc9-20261102/input-r01；结果runs/r01，日志slurm/zenanyan-af16-95242.out/.err；完整脚本/参数/Slurm账目已归档。作业已结束，无自动监测
登记：pending；management-hub PR5仍open/unmerged，https://github.com/rayggxia-workspace/management-hub/pull/5
看板：实际状态unverified、同步pending；任务分支config无board.json，工具无Projects item/字段能力；Status映射In review已读；处理人待指定，未证实权限拒绝。需配置/能力者核条目并同步Project ID/Status/Priority后读回
审查与状态：PR open/unmerged，外部审查人待指定；内部独立复核不是外部批准。Issue151本轮转in_review，非done，未合并main
下一步：Melodydt实施Qwen3真实F行H1024/I3072的数值/epsilon接收、N-long、完整归约/14912B候选布局及9MiB版本化chunk provider；当前仅方案，未映射/质量/性能验收。https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/75d99a5ba01adba1e978db3933a41e1d43c49c30/docs/handoffs/2026-11-02-issue-151-af16-admission.md
核验时间：2026-11-02 11:21:15 UTC
```


### 2026-11-02 接续：L4 F1024真实维度整数候选

负责人Melodydt，复用Issue151/PR152/`task/151-six-connection-study`；输入`75d99a5ba01adba1e978db3933a41e1d43c49c30`。独立API包`work/Melodydt/151/f1024-75d99a5/integrated`（无Git HEAD/index），不修改根参考或其他会话目录。

范围：Qwen3 H1024/I3072单token FFN整数profile；N-long、单M跨chunk全归约、job/seq/version关联的9MiB供参。验收：固定源码commit后的服务器Verilator、1024项RMS/3072维mid、两条完整数值样例、独立golden/权重流SHA、故障取消回压与源码证据索引。训练checkpoint/校准质量、源epsilon1e-6到候选2^-20的质量影响、完整Attention/模型推理与物理层仍UNKNOWN，不放宽原模型准入。

当前实施中`status:in_progress`；仿真仅本人服务器目录，Slurm名`zenanyan-f1024`，实际job/commit待提交补录。登记沿management-hub PR5 pending；Projects缺可核验配置/条目工具，状态unverified、同步pending，处理人待指定。


F1024启动回执：服务器`yuzelu@10.129.166.172`，源码`6a7de2c8c3368f7e82005ac7f194071c6b6474bf`（30份输入Git blob/SHA-256已核），Slurm95245/zenanyan-f1024/c64/8CPU，提交时PENDING节点待分配。任务`/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/f1024-75d99a5-20261102`，工作/输入`input-r02`，命令`sbatch --parsable submit-r02.sbatch`，结果`runs/r02/results/run-receipt.json`，日志`slurm/zenanyan-f1024-95245.{out,err}`；实际运行终态/CASE/SHA待实收，不预写通过。43e9f48源码后、提交前仅修正runner的无序完整CASE集合判定；r01仅本地打包，未提交服务器，无job。


### 2026-11-02 F1024本轮交付回执（待外部审查）

rayggxia-project-collab1.0.0；project_id=llm-hardware-design；负责人/认证Melodydt。复用PR152及task/151-six-connection-study→task/143-seven-block-v2。实际源码`6a7de2c8c3368f7e82005ac7f194071c6b6474bf`，资料提交`71c819c2f87e5df8d46c373df0f062fba6cd0600`已推送并核验46文件Git blob；本地独立API包work/Melodydt/151/f1024-75d99a5/integrated，无Git HEAD/index，根参考与其他目录未覆盖。

新增N-long/F1024各1RTL/1TB，H1024/I3072完整1024统计/3072mid/全K归约与9MiB有序参数流；旧40RTL/TB/include不变。服务器95245/zenanyan-f1024/node1/c64/8CPU自然COMPLETED0:0/2:11，Verilator5.042：N38+F26共64CASE，2完整fixture分别9MiB accepted流与canonical长度/SHA一致，30输入/18文本/归档及4大流导出重核SHA。原始大数据/构建留本人服务器任务目录。管理/W5IF静态PASS，独立Python112717数学/静态断言；旧回归未执行，100条编译警告保留，非lint clean。

[实施报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/71c819c2f87e5df8d46c373df0f062fba6cd0600/docs/W4_F1024_IMPLEMENTATION.md)、[来源质量门](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/71c819c2f87e5df8d46c373df0f062fba6cd0600/docs/F1024_SOURCE_QUALITY_REVIEW.md)、[接续入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/71c819c2f87e5df8d46c373df0f062fba6cd0600/docs/handoffs/2026-11-02-issue-151-f1024.md)。个人进度已更新，原24真实target仍GAP/模型质量UNKNOWN；新整数尺寸资格不升级旧目标。dense合成压力样例明显饱和，selected epsilon2^-20≠源1e-6，无trained质量接受。未实现真实MEM/实际A/L5/全模型/永久金属绑定/物理。

下一步先闭合获授权tensor/F真实输入/FP32参考/cal-eval误差门与scale/epsilon，再推进Qwen3真实A的Q16/KV8/D128、Q宽2048/QK RMS容量和程序；当前仍L4。hardreset-provider/partial前缀边界见报告，未泛化所有late返回/故障覆盖。

登记pending：management-hub PR5 open/unmerged，默认登记表无本project_id；看板unverified/同步pending：config无board.json且当前无Projects条目工具，确认看板/受众及同步条目字段处理人待指定，不是已证实权限拒绝。待指定外部审查人，Issue保持open/status:in_review，PR未合并，不done；优先级待指定。Refs #151部分交付。


### 2026-11-02 接续实施：L4真实参数数值门与Qwen3 A资源程序

用户授权继续；负责人/认证Melodydt，复用Issue151/PR152与task/151-six-connection-study，输入71c819c2f87e5df8d46c373df0f062fba6cd0600。隔离API包work/Melodydt/151/qwen-numeric-71c819c/integrated，无Git HEAD/index，不修改原根参考/其他目录。

本轮先固定真实训练tensor来源与数值评估工具，尝试从官方Qwen/Qwen3-0.6B公开、非gated的固定revision c1899de289a04d12100db370d81485cdf75e47ca取得layer0所需tensor，禁止借用其他成员目录。记录完整文件未下载/部分范围及tensor各自SHA的区别。真实layer0 Attention产生F切口输入，比较旧固定profile与有限尺度候选；小提示诊断不等同完整模型质量。并行形成真实A的head/GQA/QK RMS/RoPE/存储/供参/本地控制容量程序检查。取得数据/环境后在本人服务器Slurm执行，RTL仿真仍只用服务器Verilator；不放宽旧24GAP，不提前宣称L4/L5或PPA通过。验收以固定源码、真实输入版本、实际评估/静态检查与证据回执为准；数据不达时记录具体阻塞并交付可独立完成部分。

状态in_progress；登记pending/Projects状态unverified、同步pending沿既有可执行交接，未新建Issue/PR。


本轮实际数据/数值作业回执：提取源码929895827c84861aa68b59a4690b3fbf35084b0d，官方c1899de289a04d12100db370d81485cdf75e47ca所需11tensor+14embedding行已按206 Range取回；58文件转移SHA核验，原始数据只在本人服务器`.../issue151/qwen-numeric-71c819c-20261102/data01`，整model文件未下载/完整SHA未实算。数值源码d0c40f5772466b4c3907bc7a2273c6adfd24ef6c，实际`sbatch --parsable submit-n01.sbatch`受理95247/zenanyan-qnum/c64/8CPU，已RUNNING/node1；登录yuzelu@10.129.166.172，工作input-n01，日志slurm/zenanyan-qnum-95247.out/err，结果runs/n01/job-receipt.json和results/numeric-summary.json。小token前缀工程诊断，非RTL/完整模型精度通过；终态/数据结果待实收。


### 2026-11-02 真实Qwen层数值/RTL本轮待审交付

rayggxia-project-collab1.0.0；Melodydt；llm-hardware-design；Refs #151，原PR152/task151分支→task143基分支。最终资料`ad407ef6d051dbe3f43285b7d3ff8368ff112b2e`已推69文件Git blob核验；数值源d0c40f57、实际RTL源f7fc7614。API独立包qwen-numeric-71c819c/integrated无Git HEAD/index，原根与44旧RTL/TB/include未改。

官方固定c1899de2所需11tensor+14embed行已取，58文件转移SHA；完整model SHA未实算。95247/node1/c64/8CPU/COMPLETED0:0/1:02，4个固定piece前缀的独立FP32 layer0→F小诊断；95248同配置/COMPLETED0:0/1:49，baseline/selected各cal+eval共4完整H1024/I3072行×7检查=28标记（不是28层），4×9MiBactual SHA一致。独立8fixture N/G/E、18874368 MLP权重码与192sampled fullK dot通过。30源输入（含重复）/39文本/归档及全部数值输出、actual流导出重核。

W9 eval相对L2 2.6522%较基线5.8247%小，但max0.3611较0.0969大、82权重clip；无clip W8仅数值结果。无阈值/代表性数据/官方框架对照，质量未接受。原24GAP/CLI默认0和Qwen3AF16正确2保留；新静态top不等于金属/ROM绑定实现。真实A Sq2单S/T只静态候选/11负例，当前L4，A控制、L5/MEM/全模型/物理待完成。

[实施报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ad407ef6d051dbe3f43285b7d3ff8368ff112b2e/docs/QWEN_LAYER0_NUMERIC_RTL_REPORT.md)、[实际A方案](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ad407ef6d051dbe3f43285b7d3ff8368ff112b2e/docs/QWEN3_SQ2_ATTENTION_PLAN.md)、[交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ad407ef6d051dbe3f43285b7d3ff8368ff112b2e/docs/handoffs/2026-11-02-issue-151-qwen-real-data.md)与个人进度已更新。本地12页交流PDF单独交付，不上传Git/对外发送。下一步质量/框架/W8与实际A控制，再L5。编译警告保留，旧回归/新故障全矩阵未执行。

登记PR5未合pending；看板配置/条目工具不足，状态unverified/同步pending，处理人待指定，非证实权限拒绝。待外部审查人/优先级指定，Issue open/status:in_review，PR未合并/非done。


## 2026-11-02 main同步与八主线重整交付

用户明确要求将main最新七宏版本同步至当前研究分支、修复差异并重整主线。本轮复用Issue151/PR152，Melodydt，隔离API目录work/Melodydt/151/main-sync-ad407ef/integrated（无Git HEAD/index），旧包/根参考/本地PDF保留。

双父merge `7aba36a030bc94014eef64b03a8b145ab68ec7fb` 已推送task/151-six-connection-study：父ad407ef6+main4b1df2c7，祖先a103da35；PR基分支仍task/143-seven-block-v2。179项增量Git blob核验：20项解决/整理资料+159上游新增；RTL/TB改动0。main PR161已合并，交付M/N/E/G/S/T六叶，R未完成。14锁=11合格依赖+1未合格R共同12源相同+2main未交付legacy保留，46runtime原字节保持，不制造ABI改动。

[完整同步/八主线报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7aba36a030bc94014eef64b03a8b145ab68ec7fb/docs/MAIN_SYNC_AND_RESEARCH_ROADMAP.md)、[当前进度](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7aba36a030bc94014eef64b03a8b145ab68ec7fb/docs/COARSE_BLOCK_RESEARCH_PROGRESS.md)、[实际检查](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7aba36a030bc94014eef64b03a8b145ab68ec7fb/work/Melodydt/151/main-sync/verification.json)、[交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7aba36a030bc94014eef64b03a8b145ab68ec7fb/docs/handoffs/2026-11-02-issue-151-main-sync.md)。原历史锁/实跑receipt不改，新main-sync/roadmap.json为当前入口。仍主攻L4：T256字残差/S真实ACK/RELEASE→一KV两Q D128→16Q完整context/Wo→真实A→F；质量/框架/W8并行。后续L5母控/双岛storedACK、L6 D/H、L7 X、L8 MEM/产品物理分别验收。

本轮6命令通过：管理、release420仓库项/0local大型成员、W5静态465/22锁、准入静态24GAP、Qwen AF16正确exit2/H1024、Range工具自检；14新资料/23链接、46runtime与6历史索引字节核对。head两管理CI41466434904/41466421570 success。无新RTL仿真/服务器job/推理/EDA，旧95247/95248仍绑定各自源码，不称merge实跑；R/模型质量/L4整线/通用L5和M11产品物理未验收。

rayggxia-project-collab1.0.0回执见PR152；本人进度/正式交接已推。登记PR5 open未合pending，默认登记表缺project_id；看板缺board.json/Projects工具，状态unverified、同步pending，处理人待指定，非证实权限拒绝。PR待外部审查人/优先级指定、未合并；Issue回status:in_review，非done。下一由Melodydt实施L4-A-TSP并继续独立质量门。


### 2026-11-02 接续L4-A-TSP

用户授权继续下一步。Melodydt复用Issue151/PR152/task151，输入7aba36a0，隔离API包work/Melodydt/151/atsp-7aba36a/integrated。实施H1024/Sq2的4096B原残差真实T spool→capture128/S写ACK/E残差→实际释放再输出事务，含背压/错误/取消/复用，源冻结后仅本人服务器Verilator。Wo采用明确的外部计算结果切口，不冒称完整Attention。当前in_progress；质量/L5/物理未完成，登记/看板交接保持。


### ATSP服务器实收交付（2026-11-03 Asia/Shanghai）

Melodydt；rayggxia-project-collab1.0.0。源码`d1efc16b654d0d11f7a833cc92f57ac00ae31740`，最终资料`a0610aff8aa6effc09e807b671151bcb9aeb75aa`已推原task151/PR152，37文件累计Git blob核验。新增1RTL/1TB，原46源不变；真实H1024/Sq2的S→T保存、T→S258真实ACK→E残差及同T实际释放后输出复用，X/Wo身份/字序及接单后独立终态已实现。

95277/zenanyan-atsp/node1/c64/8CPU首r01自然COMPLETED0:0/57秒，Verilator5.042：30严格CASE、三合成fixture×X/Wo/输出共9×4096B actual SHA通过，13源码/14文本/归档重核。任务/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/atsp-7aba36a-20261102，input-r01/runs/r01；无在跑本任务作业。Wo仍外部切口，无完整A/质量/物理；37warnings保留、无本地RTL，旧回归未跑，24GAP保持。

[报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a0610aff8aa6effc09e807b671151bcb9aeb75aa/docs/W4_ATSP_IMPLEMENTATION.md)、[交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a0610aff8aa6effc09e807b671151bcb9aeb75aa/docs/handoffs/2026-11-02-issue-151-atsp.md)及本人进度已更新。5静态命令按预期退出（QwenAF16正确exit2），两head管理CI41477474635/41477459028 success。下一L4-A-H2保持H1024/D128一KV两Q，质量/框架/W8独立待验，仍L4/L5未开。登记PR5未合pending；看板缺board配置/条目工具，unverified/同步pending，处理人待指定。待外部审查人/优先级指定，PR未合并，Issue回in_review/非done，完整回执见PR152。
