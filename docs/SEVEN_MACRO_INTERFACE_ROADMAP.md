> 当前进展更新（2026-11-01）：用户明确要求同步PR144最新RTL并进入P2。P2采用固定7078786的14核心源，原P1源锁与回执保留为历史；本轮新增RTL及实际验证见[第二步报告](PHASE2_MST_IMPLEMENTATION.md)。P1独立审查尚待完成；P2仅有限原型，P3–P7未开始。下列“P1当前”叙述记录原路线制定时的阶段，不代表本轮仍停在P1。

# 七宏接口同步的七阶段正式研究路线

任务仍为Issue151 / PR152，输入研究版本343f4d4775ffab61b2ed2df13de243cc659c157a。用户已授权采用七步骤路线并开始第1步；本文件为本任务正式路线；实际检查、上传及审查状态见[第1步报告](PHASE1_INTERFACE_BASELINE.md)。

**当前只准备P1研究规格待审查；P2—P7未开始。**第1步不运行RTL/SystemC/EDA或服务器。管理检查通过只代表管理结构；源码/静态参考/SystemC/RTL/网表功能/LEC/数值质量/物理接收分别出证据。

## 1. 版本锁与不变边界

七宏源码暂锁PR144的643c6012a11cbf461146ac40fbf61485223fe946；已对开始时观察到的最新adb819c4d49516008e971a201a7d52c0248df8f9完成14路径比较，仅R内部源变化、七顶层声明相同；本轮选择沿用643，不自动采用新源。升级必须记录完整SHA、逐文件接口/数值/状态/复位差异和受影响测试/资格，不把旧通过回执重标为新源通过。

范围仍为已有八样本/十层型，六算法是回归集，全部合法角色连接目录目标保留。role/type/scale/layout可静态证明的部分放离线编译证据或永久ROM，不强迫每包运行通用类型系统。真实MUX、holding、算术、握手计数、错误和阶段锁不能因此省略。

模型A/B必须使用相同M1–M10、有源宏/控制/MUX/中继和PG/CTS，只通过M11/M12被动图形永久选程序/参数/合法路线。不能每产品重综合FSM、删除不用宏或插buffer后称同底座，不使用启动加载控制程序。系统确有外存，本阶段暂不研究接口与带宽；P0的9216B计算区等片上准入缺口不等于模型永久不支持，也不能假定外存已经无成本闭合。

Issue151既有负责人Melodydt保持；阶段实施负责人/独立审查人待指定，不擅派其他成员，不编造截止日期。独立R最终资格继续依赖原实施任务，本路线不接管其作业。

## 2. 七步骤、依赖和验收出口

| 阶段 | 输入与主要产物 | 可验证的退出条件 |
|---|---|---|
| **P1 版本/接口合同** | 343研究、643源码、八样本→版本锁、七宏字段/数值/phase/reset表、最小MST fixture、需求到阶段/证据矩阵 | 源码/字段可追溯；未知数值和升级差异明确；MST测试契约闭合；所有七宏关键合同有未来执行归属；以研究规格接受，不称RTL通过 |
| **P2 S服务＋最小MST顶层，并行母控ROM骨架** | P1合同→S_CTRL、loader/M桥、T基本生命周期、S→M→S→T及read sink RTL；同时开始母控SERVICE/loop/ROM和模板capture | 数值与握手/反压/复位/错误/重用的真实RTL及独立参考通过；S响应无等待环、loader done不冒充计算完成；母控等待不阻止S helper；形成首轮实际寄存/ROM/pin/路线反馈 |
| **P3 E/G与FFN8** | P2服务＋原生E/G→操作数收集、按目的拆拼、G配对/流水计数、FFN8 | 每阶段和最终整数输出匹配；M结果/scale不串任务；E12/13不同格式、G fn/gated/tail/反压已测；不把不必要转换强加硬件 |
| **P4 N与Softmax257** | P2 S/控制骨架＋N→目标长度与phase锁、raw/EXP/gamma回放、257实例及Norm/TopK字段处理 | 全部257输入/EXP/回放及33输出字守恒；末项新max、tail1、早FINALIZE、错lineage、组保持/RESUME、epsilon/gamma和65535边界明确 |
| **P5 通用拓扑/同S同T/loader导出/fork-join** | P2/P3/P4原语＋合法目录→copy/layout/gather、自重入、capture/spool、fork/join/反馈 | 同S不死锁、同T释放后才新BEGIN、loader全部A/B义务完成；独立反压分支/版本/条件SKIP正确；非六模板图覆盖，不以49冒烟例代替profile覆盖 |
| **P6 R＋所需NUM/多tile状态** | 前述阶段＋R guard矩阵/真实数值缺口→R阶段控制、转换/系数/偏置/宽累加、有限多tile版本原型 | 候选先保存、等COPY响应再读新active、SSM有效位/因子重装与失败history处理正确；NUM有真实RTL/范围与参考；有限多tile提交/导出/失败恢复机制通过，未借原R旧资格 |
| **P7 完整八程序＋同底座产品/外存/物理** | P2起演进的编译/ROM、全部原语和实际MEM平台→完整产品程序/表、实际规模/质量与物理接收 | 程序/表实际编译且装入真实资源；完整模型数据/状态/MEM闭合；每产品功能/质量/活性/性能通过；同一有源底座及限定制层差异、最终STA/PG/DRC等证据通过独立审查 |

P3与P4可在P2后并行；P5组合它们的拓扑；P6补状态和所需数值能力。母控、程序编译骨架与ROM量级从P2并行开始，早期物理路线/扇出/存储成本随每个原型反馈，不等P7才第一次估算。P7收最终完整程序、MEM、真实大规模和共同底座产品证据。

P6/P7的存储依赖要如实说明：可在P6用小而可驻留的多tile验证旧/新版本、连续ACK、localcommit、恢复/部分发布机制；完整GDN2MiB/SSM4MiB每层state及真实128/4096后处理不能被小原型替代。它们在P7接入真实MEM平台后再做实际规模闭合。P6仅完成小原型时，完整样本义务继续保持未完成。

## 3. 第1步到底要冻结什么

1. 七个宏的实际顶层/局部依赖和固定源指纹，原生命令/数据/状态字段及数值单位，尤其响应的数据/ACK分类。
2. 同一context阶段续作与新context重入，busy/ready与phase锁、compute/data-ready/commit/publish/release的区别。
3. 静态编译可以消除的metadata与必须存在的runtime动作；既有op可承担时优先复用，不把类型标签当数据转换。
4. 一个足够小的MST fixture、独立整数期望、握手/错误/复位/反压/重用契约，以及未来运行证据格式。
5. 七宏所有关键要求到P2—P7的测试归属；不能只冻结MST后让N/E/G/R/T后续无标准可验。

本轮选择保留643，后续源升级未实施。P1产物可准备审查，不意味着P2 RTL已写或整个项目done。独立审查、合并和验收状态由任务实际回执记录。

## 4. 最小MST fixture：无需E/G/N/R就能验证第一条完整交接

首个smoke锁定[整数参考](PHASE1_MST_REFERENCE.md)的 `P2_S8_DOT8_RAW64`：1行、K8、N8、一个tile，A/B均S8。A为raw `[1,-2,3,-4,5,-6,7,-8]`（F=0），B第n个输出列的八元素都为n+1，按n-major `8*n+k` 存储。协调reset后op6 CLEAR_ALL并取ACK，再op4 index0/data1设置factor1/left0并取ACK；loader A8/B8、bank0、rows1/tiles1、reuse_b0。M EXEC op10/index0/data0x9884，八个S64结果应为 `[-4,-8,-12,-16,-20,-24,-28,-32]`。

S使用P0计算区内对齐地址：A组448..451（448低64bit有效、高64bit和449..451填零）、B组452..455、结果456..459，共12字192B计算区。op3 index0/1/2/3每次取两S64，先写结果S456..459并取ACK，再从S读出填T四个128bit字；T owner0/generation1/BEGIN4，commit后read4并比对sink，末字take后release。四个字的十六进制及S初值由 `work/Melodydt/151/phase1-mst-vectors.json` 的minimal_mst_profile固定。首个smoke不引入E/G、量化或强制合8；op5 S16/shift0等作为P2后续独立读出格式测试。

MST各个“完成”有独立条件：S初始化及结果存储都必须收写应答；loader done/error要take；M EXEC状态先检查，再发结果读命令；T须完整写满SEALED后commit；四字read sink按真实take比对，不能仅req握手就完成整个系统任务；最后释放租约且无在途响应，才允许下次重用。同T回路及T→S大spool在对应后续测试中另验，不偷偷增加首个smoke的必需范围。

这个数值fixture和命令编码是待执行的RTL测试规格；P1运行了受限Python整数参考，没有运行对应RTL。新增M/S/T外侧控制、保持、路线和小顶层也没有因定义fixture而出现。

## 5. 测试范围与证据归属

机器文件 `phase1-verification-plan.json` 列每项requirement ID、未来执行阶段、期望与证据。目前所有RTL测试均not_executed。

- **M/S/T基础，P2**：数值正负/缩放/多K追加、M行级失败与旧结果、S每请求一应答、loader A/B独立反压及bank/fmt/half、T错误/粘性状态与重复使用，复位/取消/长有限停顿覆盖每条边界。
- **E/G，P3**：所有op与输出格式、FMA第三输入单位、RoPE、E12八S8/E13四S16、目的要求下拆拼；G两lane输入角色、gated Sigmoid Q10、四级流水冻结/退休/tail；FFN8逐阶段与端到端。
- **N，P4**：257末项新max/尾包、目标计数/错回放、Norm epsilon/gamma/factor错误、TopK只返回ID及stats结构、阶段RESUME和65535原生限制。未知GDN L2 epsilon不能借RMS参数填入。
- **拓扑，P5**：同S响应等待环与重叠copy、同T spool/释放、loader导出全事务、fork/join不同延迟、SKIP/merge及有初值反馈；缺硬件作为gap保留。
- **R/NUM，P6**：op0/6/7身份、所有pending合法性、先保存op12、等COPY再op11/14、REVOKE不回滚active、SSM op5 param_valid/op15消耗与预载、后续失败留下history、partial commit/根发布；宽转换/系数/Falcon bias32/宽归并有真实算术参考，禁止E16冒充S32。
- **完整系统，P7**：动态MoE ID/rank/概率/专家地址/scale、全八程序和实际存储、MEM可变延迟/故障/排空、真正共同底座产品及最终物理。

有意义的独立参考应定义数学整数、RNE、范围/错误和字段位置，再同实际RTL比较；不能只复制RTL实现“自证”。静态probe和SystemC可以补辅助证据，但不能满足P2起的RTL门，也不替代网表LEC/物理接收。

未来每次实际运行须记录source commit、脚本SHA、工具/约束配置版本、输入/seed及SHA、准确命令、日志/结果位置和SHA、退出码、失败与coverage、审查处置。上游单宏通过只能作为所选源的依赖，不等于新系统路径已通过。

## 6. 本规格的实际回执

已读取统一协作Skill及343f研究、当前执行合同，运行管理结构检查PASS。没有运行RTL/SystemC/EDA，没有提交服务器作业，未改任何叶宏或其他任务文件。路线及验证矩阵完成JSON语法、七阶段依赖无环、需求ID唯一/各阶段归属，以及canonical MST命令、结果和S64打包一致性核对；这仅为规格检查。独立准备阶段未操作远端，正式整合及远端交付以phase1-checks和PR152回执为准。后续阶段状态保持not_started；P1材料准备完毕待独立审查，不表示已经验收或合并。

当前源锁、七宏合同、软件参考和实际回执见[第1步报告](PHASE1_INTERFACE_BASELINE.md)、[原生合同](PHASE1_NATIVE_INTERFACE_CONTRACT.md)、[MST参考说明](PHASE1_MST_REFERENCE.md)及work/Melodydt/151/phase1-index.json。P1的规格准备不等于独立审查或验收完成。
