# 两级控制当前接续入口

Issue179 / Draft PR180；Melodydt；2026-11-08 Asia/Shanghai；task/179-local-block-continuation。

## 当前进度：main64实现合入，统一前端适配待完成（2026-11-08，Asia/Shanghai）

main c4d7b960 的188份母控、五类原生RTL、生成器及验收索引已逐字节同步到PR180，源码提交 f046a8c9。采用有范围的文件同步，同路径内容以main为准；只继承原PR180提交，不宣称整个main历史已合并。当前运行选择v2/64位，128位共享源及历史验收保留。另补37份main物理脚本依赖，原样独立锁定于physical-dependencies.json；仅检查来源和导入依赖，本轮未重跑物理流程。PR176重新核验仍为08f2ea20。

新增权威入口project/control_main64_v1：不使用旧frontend的native_lc()替换main P/U局控；保留main U的独立TX保持槽和三源E运算。母控核心、端口、取指、PM四份共享源与本分支相同；C/F/J的247份锁定依赖逐项检查，三份历史辅助文件在隔离快照中恢复，不改当前冻结表或伪造旧验收。

服务器100362十个子作业均COMPLETED/0:0；同版64位RTL123/123：母控54、五类基础27、C往返15、CF双向9、U双向9、U三源FMA双向9。实际母控PM和Block私有S采用SRAM模型；局控PM仍为行为夹具。本地软件1359/1359通过。输入542文件、镜像、日志和结果SHA均核验。旧1690/1690及九配置综合验收是历史证据，本轮不重计。不是统一boot/编译器/三端真实PM或新增组合时序验收。

审查结论：不能把main64原生路径与旧统一前端当成同一已验收配置。还需完成：1）五类局控/服务能力与身份绑定；2）母控内部PM加两端局控PM、统一装载/CRC/部署顶层；3）新传输语义下的取消排空/恢复；4）编译器及独立核对器对齐，包括U三源；5）统一系统同版回归、覆盖及综合包重冻结。完整LLM图导入仍是独立后续目标。执行ISA64位、单时钟和3.333333333 ns目标不变。

源码及完整审查见project/control_main64_v1/README.md和docs/local-blocks/CONTROL_RESEARCH_HANDOFF.md；实际回执见work/Melodydt/179/control-main64-validation.json。PR180仍Draft未合并，任务in_progress；独立审查待指定，登记pending、看板unverified/同步pending。

## main64合入范围与来源

| 对象 | 当前权威路径及关系 |
| --- | --- |
| 母控 | project/rtl/mother_control_v1；mother_control_64内含自己的16KiB、四bank PM。共享MC/端口/取指/PM与PR180逐字相同。 |
| P、U | project/rtl/pu_leaf_base + project/experiments/pu_leaf_base/controlled.py、control_replay.py；保留main生成的局控。 |
| C、F、J | project/rtl/block_cfj_v1 + project/experiments/cfj_leaf_base；controller64显式选择、锁定247份#180历史源。 |
| SRAM及基础宏 | project/rtl/{s_sram,block_v2,block_v1,block_library_v1,r_local_state,...}；行为bank只用于功能仿真，真实物理视图从已有验收包绑定。 |
| 来源和验证 | [main source lock](../../project/control_main64_v1/main-lock.json)、[核验及服务器入口](../../project/control_main64_v1/README.md)、[本轮结果](../../work/Melodydt/179/control-main64-validation.json)。 |

本次复制188份main已有文件，未改写其RTL或产生器。新增入口及隔离CFJ依赖共7份；195路径blob已读回核验。main保留两种指令格式的共享实现；本分支本轮只选64位，无需删除共享128位逻辑。不同目录的旧研究适配器继续保留为历史配置，不能声称自动继承main的新服务资格。所有输入和结果以commit、锁表及SHA为准。

## 审查：前端还差什么

这里的前端指受限任务→三端程序→统一装载→母控/局控执行与恢复，不能只看指令长度。

### P1-1 统一生产接入顶层尚缺

`five_control_top.sv:156`仍直接实例化MC；`:256/:326`仍实例化本分支native_control_endpoint。`five_boot_top.sv:228`另建三个PM。main母控已自带一个PM，因此直接叠加会重复母控存储器；应通过母控cfg接口接统一装载器，为两个main局控各接一个可综合PM，再连接同域复位、任务和返回通道。需要重新确认ID、ABI、topology、capacity和部署顺序，而不是将“64位相同”视为可互换。验收：每配置1MC/2LC/3PM、12程序bank，无重复/旁路存储；三个镜像均真实装载读回CRC后执行。

### P1-2 服务能力与编译器不一致

`control_task_compiler_v1/compiler.py:94`限定最多两个源；`control_native_v1/ucf_native_service.sv:94`同样拒绝三个源。main `controlled.py:264`仅为U的E lane0开放三源；main compact64.py还明确采用限定的可无损压缩opcode集合。因而现有编译器的软件通过不等于可以编译main全部原生能力。需要建立逐类型/版本的能力表，联动compiler、独立audit、描述符/原生操作及目标身份，保留N两源限制；不支持的组合明确拒绝。验收：U两源/三源FMA和不合法N三源、非法类型/拓扑/长度均从任务JSON经过实际装载回放，检查结果数值与字节计数。

### P1-3 新传输与旧恢复合同尚未统一

main `controlled.py:56-75`使用独立128位TX槽：S读响应进入槽后立即释放S响应端，槽的数据及所有权保留到远端真实写ACK，解除双U同时SEND的互锁。旧统一路径不是该服务封装；`native_control_endpoint.sv:262`仍绑定旧adapter，`:276/:280`关闭N/E直接通路。不要把main双U通过移植为旧top已通过，也不能因新增槽而提前释放源所有权。需要将新槽、接收提交、J片段/lease、epoch身份与监督层pending/drain条件一致绑定。验收：双向同时发送、背压、丢失/错误ACK、取消中有保持槽、排空超时隔离及整组复位重装，确认没有伪造提交、丢数或提前释放。

### P2-1 同一套统一系统的证据未闭环

本轮123例使用main母控RTL+真实PM、main生成的局控和实际Block/私有S；局控PM是原夹具行为模型，测试绕过旧统一boot manager及任务编译器。母控54例使用有限对端，另外69例使用真实局控/Block。main已有物理网表一致性及独立STA仍可参考各自原回执，本轮没有重跑物理门。需要新统一top的完整链路回归：任务→独立字节核对→真实三端装载/CRC→部署→执行→目的提交ACK→结果→恢复，并补非法镜像、身份、容量和顺序负例。验收须覆盖选定配置的有界矩阵、断言和未覆盖清单；本轮没有宣称新的覆盖率。

### P2-2 新顶层的综合前交付需要重冻结

`control_presynth_v1/freeze.json`仍绑定旧顶层和67份控制源，旧9/9综合及54项保护只证明那套配置。main64源锁增加了可追溯性，不会自动产生新顶层的清单/边界/SDC/资格。待前四项稳定后，生成包含main母控及各类局控/服务的同版清单，绑定真实SRAM/叶宏端口，核对时钟/复位、lint、层次/综合、无多驱动/锁存及SDC对象；周期继续3.333333333ns。新增组合映射STA、等价、CTS/布线等后端资格独立完成，不以独立Block正裕量代替组合验收。

## 本轮验证与限制

| 检查 | 实测结果 | 含义 |
| --- | --- | --- |
| 管理结构 | PASS | 不替代硬件、权限或在线审查。 |
| main源/历史源/U硬件锁 | 188 / 247 / 31逐项一致 | 另有4份母控共享源逐字一致。 |
| 服务器64位回放 | 123/123，10作业退出0:0 | 母控54；P3、U15、C3、F3、J3、C往返15、CF9、双U9、三源双U9。 |
| 软件 | 1218+141=1359/1359 | 既有受限编译器及矩阵；未扩大模型或main服务支持。 |
| 同版统一系统/三端真实PM | 未执行 | 尚缺生产绑定，不能从夹具推断。 |
| 新组合STA/物理/新覆盖 | 未执行 | main原独立资格和旧研究资格分别保留。 |

所有本轮作业结束，源输入542文件、镜像和日志SHA已核验。复现命令见control_main64_v1；历史1690/1690、81.04%源码行覆盖、九配置综合不计入本轮新统计。[详细报告](CONTROL_RESEARCH_AND_ISA_QUICK_REFERENCE.pdf)原位更新；完整原方案含内部历史，仅本地维护。

## 建议接续顺序与协作状态

1. 固定main五类局控和服务的能力表、外部端口及身份合同，明确本轮支持哪些有界配置。
2. 建立main母控+两端main局控+三端PM的统一boot顶层，完成装载/CRC/部署。
3. 对齐编译器/独立核对器和新的传输/恢复监督，包括U三源及双向同时SEND。
4. 在同一源码版本运行完整系统回归、负例和覆盖，记录原始输入/输出SHA。
5. 重新形成综合前冻结交付，再进入组合时序和物理验收。完整LLM图、动态形状和任意规模路由另列目标。

本轮是自查，不替代独立PR审查。Issue179仍in_progress，Draft PR180未合并；审查人待指定。管理中心登记PR5仍pending；当前仓库无board.json且无Projects工具，看板状态unverified、同步pending，待具备权限管理员核验。没有聊天外自动监控。
