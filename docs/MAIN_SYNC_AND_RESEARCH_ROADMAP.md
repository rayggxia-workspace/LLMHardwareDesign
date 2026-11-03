# main六宏交付同步与功能岛主线重整

Issue151 / PR152，负责人Melodydt，时区Asia/Shanghai。本轮把main固定提交 `4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609` 同步到研究 `ad407ef6d051dbe3f43285b7d3ff8368ff112b2e`，按共同祖先 `a103da352b7e431cedc69f54b9f71c05371be1b3` 做真正的三方Git树整合；不是覆盖研究目录或只复制七个顶层文件。最终双父提交见PR152回执。

## 1. 核对结论及本次改动

main的[PR161](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/161)已于2026-11-01 12:46:48 UTC合并，交付 **M/N/E/G/S/T六类合格叶宏；R仅保留研究源码、未合格**。当前七类接口研究可以继续，但不能把七类源码可见写成七类物理均完成。

| 比较对象 | 实际结果 | 本次处理 |
|---|---|---|
| M/N/E/G/S/T的11份选定RTL/include/子模块 | Git blob及SHA-256与研究包完全相同，且匹配main交付索引 | 原字节保留，不改op/端口/数值/握手 |
| R研究RTL | 同字节；main索引qualified=false、selected=false | 保留研究代码，不继承六宏资格 |
| `block_feed_m.sv`、`shared121.sv` | 研究14源锁中的2份legacy，main未交付这些路径 | 留在研究分支，当前v2岛不依赖它们；不误报main14/14相同 |
| 现有宏适配及顶层/TB/include | 46份文件与ad407ef6全部相同 | S helper、E/G/N/N-long、MST及各A/F/AF/qnum无需ABI迁移 |
| main交付材料 | 新handoff、check_release、release-six整树、release-validation | 完整同步源绑定索引/轻量证据/检查器 |
| 共享文件 | `.gitattributes`、README、ARCHITECTURE、STATUS、BLOCK_V2两文档及两项上游记录共8处双方变动 | 原生合同/结果采用main；架构三方文本合并；保留研究历史及上游负责人原文，明确历史时点 |

S仍由S16k存储和loader组成；当前v2 M为自含实现。没有新增“bridge硬宏”，也未把适配塞入已验收叶子。连接所需capture/gather、拆拼/尺度、S普通口owner、本地op/phase/ACK/释放协调仍是岛内待预制的外部逻辑。

完整合并差异由分层树比较得出；GitHub compare首300文件存在截断，不能作为完整分母。无RTL改动。`ref-project/`作为不透明原子子树保留，没有展开、逐项审查或哈希检查。任务隔离包为 `work/Melodydt/151/main-sync-ad407ef/integrated`，不是完整Git checkout，无本地HEAD/index/暂存。

## 2. 新的状态入口与证据边界

当前八主线以[本报告](MAIN_SYNC_AND_RESEARCH_ROADMAP.md)、[进度入口](COARSE_BLOCK_RESEARCH_PROGRESS.md)和[机器索引](../work/Melodydt/151/main-sync/roadmap.json)为准。旧seven-stage-roadmap/island-sync-plan、各source-lock和运行receipt保留原字节、提交与日期，作为当时快照，不回写成新main实跑结果。叶宏源的来源身份可同时属于main和旧锁；物理资格只属于索引明确的六叶和精确字节。

四条验收轴分别记录：叶宏来源/物理资格、岛内整数RTL正确性、真实模型数值质量、跨岛/共同底座物理。任何一轴通过都不自动接收其他轴。F1024有真实尺寸整数实现和4个真实F行的有限证据；真实A Sq2目前仅静态容量/程序候选；旧八样本×三目标24项保持GAP。四行不是28层或完整模型推理，W9平均误差较小也不抵消尾误差和82次权重clip。

## 3. 八主线重整：保留编号，重新明确退出门

| 主线/工作包 | 内容 | 已有证据 | 尚缺内容 |
|---|---|---|---|
| L1 / W0 | 原生合同与来源 | 合同/角色与版本审计已有；本轮接收main六叶交付，12共同源相同 | 独立审查；完整底座能力并集/预算未冻结 |
| L2 / W1 | 输入/输出岛壳 | 固定DOT8可变输入、真实S写ACK、holding/DONE/错误已有有限RTL证据 | 通用hidden/参数端点、完整排空/复用与资源合同未实现 |
| L3 / W3 | E/G适配和FFN核 | E三输入收集、G拆拼配对及有限FFN8已有 | 六配置需要的全部op/尾字/宽数值能力未全验收 |
| L4 / W4/W5 | 完整A/F与真实样本纵向实现 | A16/F16/AF16有界RTL；N-long/F1024与4真实F行整数RTL；真实A仅静态方案 | 正在推进；真实Qwen3 A、真实A→F、代表性质量与全部样本变体未闭合 |
| L5 / W2/W6 | 母控与跨岛连接 | W5-IF逻辑合同和三层互联安排已有；通用端点RTL尚未开始 | 固定控制网/双岛stored ACK、fork/join/反馈与安全回收未实现 |
| L6 / W7/W8 | NUM/R及D/H配置 | BOM/算法/角色合同为候选；无完整D/H岛RTL | R叶最终资格未完成；宽算术、state/history版本与多tile原子发布缺失 |
| L7 / W9 | MoE X配置 | router/TopK/专家/归并需求已分析；完整X RTL尚未开始 | ID与score映射、动态专家调度、宽加权合并/容量未闭合 |
| L8 / W10/W11 | 真实MEM/产品/共同底座物理 | 六叶已有上游典型角资格；系统MEM/产品/共同底座尚未实现 | 真实外存接入、完整程序/ROM预算、预连/定制层几何及系统时序缺失 |

六配置继续是A_plain、A_gate、F、D、H、X，并不等于六个完整物理岛已制作。串行条件BOM保留：A_plain=M/N/E/S/T各1；A_gate/F/X各再配G1；D/H再配R1。本地CTRL及格式/布局/供参/NUM/MEM、clock/reset、ROM及中继另计；相同宏数不证明可直接共用同一岛。覆盖域仍是仓库八样本十层型，不增加未知模型的支持承诺。

## 4. 下一执行切片：先闭合真实A的T残差路径

当前继续L4，不退回重新实现已相同的七叶。实现顺序细分如下，每个切片独立冻结源和预声明CASE后仅在本人服务器Verilator验证：

1. **L4-A-TSP：真实4096B残差spool和T→S→E闭环。** 两行H1024、S16各2048B，由实际S读取写入T的256个128bit字：T[2g]=X0[g]、T[2g+1]=X1[g]。COMMIT后整个head阶段READ_HOLD且不take；不能占用剩余2KiB再开事务。回放每字先capture128、实际写S258并收到ACK，再让E做对应Wo组残差；最后E写回ACK后实际RELEASE，才能BEGIN第二个256字最终输出事务。验证完整顺序/数据关联、S覆写后原残差仍正确、随机回压、重复BEGIN拒绝、abort/reset/error、部分已消费输出和下一任务复用。此切片尚未实现。
2. **L4-A-H2：一个KV头服务两个Q头。** 按真实D128、q_head=2kv_head/2kv_head+1，包含Q/K逐头RMS、split-half64 RoPE真实gather、因果count1/2 Softmax、V不变轴和PV通道顺序。逐阶段对独立golden，不能沿用旧D8系数/相邻原轴RoPE或把未来score0算入分母。
3. **L4-A-FULL：扩至KV8/Q16、Q宽2048。** 512个context字共8192B全部产生后才Wo；Wo完整K2048归约结束才窄化，S峰16KiB及Norm/work/context生存期逐项验证。实际6MiB投影权重流、参数身份/计数、epsilon/尺度必须落到真实CTRL/端点，不能靠换weights_version改变指令常量。
4. **L4-AF-REAL：真实A→真实F纵向闭环。** 先用双方已明确的Fin10基线；Fin12候选必须有显式转换或匹配的新profile，不能只凭S16位宽裸接。将A的H1024格式/顺序传入F，分别管理gamma/权重版本、两行持有与子DONE/错误；证明残差采用正确子层原X。现AF16是固定有界验证顶层，holding不能按尺寸免费放大，也不代替通用岛间协议。
5. **L4变体扩展与退出。** 在对应数值质量门接收后逐模型验证Q/K Norm、partial/local/global RoPE、输出门、GELU/postNorm及增益等差异；真实容量不足保留映射/MEM缺口，不能缩形到8维或只接受Qwen就宣布八样本全L4完成。

数值轨并行推进：官方框架切口对照、明确cal/eval数据与误差/clip阈值、W8无clip方案和W9尾误差取舍。先形成可复现评估门，不能由工程人员凭一次平均改善宣告模型质量接受。真实A结构验证可采用明确整数profile推进；产品数值常量和物理冻结仍受质量门约束。

## 5. 三层连接与控制的实施归属

| 层次 | 方案 | 实施/验收归属 |
|---|---|---|
| 岛内宏—宏 | 固定数据路由与适配；通常经S物化/真实ACK，保留S loader→M快路；并非所有数据必须绕S，也非49种专线 | L2–L4、L6/L7逐岛落RTL并覆盖实际op/格式/phase |
| 母控—本地CTRL | 主候选固定预连控制网；母控发粗任务/依赖/停止，本地调op/计数/缓冲/ACK/退休 | L4前置W5-IF合同，L5/W2实现固定网与事件闭环 |
| 岛—岛 | M11/M12选择数据路线及对应确认；源holding/CLOSE/release和目的stored ACK分开 | L5/W2双小壳，再W6同岛复用/fork/join/合法反馈；当前无通用RTL |
| 共同底座—定制金属 | 同一有源底座预制所有CTRL/ROM/选择/缓冲/中继/CDC/CTS及必要MEM能力，永久绑定有限产品 | 引脚/扇出/资源预算现在前置，L8/W10–W11做真实系统与物理差分验收 |

因此预制完成时岛内必须已有必要连接，母控固定网是待实现候选，岛间模型路线和配套确认再由M11/M12定制；当前逻辑方案不等于已完成物理预连。产品不依赖启动装载控制程序。外存实际存在，接口/容量/带宽后续实现，当前片上切片的缺口不能等同架构永远禁外存。

L5的两个小壳可以不等待全部八模型/全L4质量结论而单独验证协议；但把L4真实A/F接入L5前必须匹配shape/数值/供参/容量合同。L6仍依赖R独立资格，L7不必等待R。L8预算前置反馈，最终物理不提前宣称。

## 6. 本轮实际验证与交付

实际检查及输出SHA见[verification.json](../work/Melodydt/151/main-sync/verification.json)。新main check_release通过，repository_files_checked=420、local_members_checked=0；未下载/重哈希上游249个大型物理成员，未重跑EDA。W5静态465项/22旧源锁、准入静态及Qwen真实AF16 exit2/GAP、管理检查和新资料检查分别记录。46份runtime源保持原字节，旧仿真仍绑定各自源提交；本轮没有新RTL仿真、服务器作业或新的系统物理资格。

main只作为本轮来源父提交；继续原task/151分支和PR152，暂保留PR基分支task/143-seven-block-v2以免将尚未合main的PR144大批研究过程混作新增岛改动。本轮不修改PR144、不向main直接提交、不自合并。PR152/Issue151交付后待独立审查，不done；登记PR5 pending，看板配置/工具缺口见交接。
