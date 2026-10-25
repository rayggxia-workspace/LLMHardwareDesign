# Issue99：完整 head 的 R 状态单元 RTL 与原子发布

日期：2026-10-25；负责人：Liangruizhi；[Issue99](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99)；任务分支 `task/99-r-state`。仅本人授权服务器 `issue99-r-state-20261025` / `lrz-i99-*`，无模型下载、无 GPU/其它机器作业、无 Phi 解封。基于93 final `f660e3538be9c07ff4ee1f105db0cfee5f0bfcab`；未改93/97/98目录。

## 结论与验收范围

已实现并接收 Falcon 既有整数合同中的一个完整 head：D128×N256，32768个S32状态码，72连续步。全head范围检查、统一RNE重标、完整N readout、有限外部old/trial/proposal/shadow、消费者接受后原子发布均是真实RTL。quiet与背压/共享S32争用两路，逐码对独立Python bigint及原72的该head输出、单位轨迹和最终状态一致。真正的重标在position27→28，local numeric epoch从0到1；原32head共同epoch最终25，二者没有混同。

实际Nangate45映射网表又通过了position0→1和position27→28两真实检查点、各quiet/背压的4次完整head运算；与4次同driver RTL逐码及周期/IO一致。72连续证据仍然是RTL；不能把两检查点门级资格写成72步门级连续验证，更不能借用98物理结果。

本次没有实现完整R Block：conv/SiLU/dt/alpha LUT生产链、其它31head、完整4096维消费者、与M/V/A/S/D总库集成及物理签核仍未完成。`consumer_accept`是Block接口切口；测试环境接受候选，不执行4096norm或其Y读取DMA。

## 真实计算、状态和接口

精度/合法布局/逐bit descriptor详见[冻结协议](../../project/experiments/r_state/PROTOCOL.md)与[机器合同](../../project/experiments/r_state/contracts.py)。主RTL：[r99.sv](../../project/rtl/r_state/r99.sv)。

- 输入X/B/C为I32Q12，dt/skip为I32Q20，alpha为U32Q31且允许精确1。状态为S32码加每head I16幂二单位，范围[-127,127]；不改写旧BF16/FP32证据。
- dtB先 `RNE12(dt*B)` 并严格I32检查，再计算 `RNE(32+unit)(X*dtB)`。不能合并为一次舍入。alpha<2^31进入实际signed32乘法器；alpha=2^31走已映射比较器/恒等旁路，不解释成负数。
- 全head采用 `maxabs(decay)+maxabs(injection)<=I64_MAX` 保守guard，再检查S32范围。需要重标时，完整32768码trial统一RNE1、unit+1、local_epoch+1，最多8次；不能仅重标一个tile。任一数值失败不发布新state/Y。
- readout完整归约N256；检查完整head每个S32×C32产品的maxabs×256界限，按unit对齐、加入skip并检查I32。该候选在I64 guard内成立，不宣称任意32位码域的256项和都只需64位。
- 只有一个共享signed32×32→64服务；peer另一端有独立holder。peer_valid可跨R offer/reject/RESTORE持续背压，R不会误吞，验证归还恰一次。hard reset是共同服务reset，必须先协调peer排空与fabric屏障。
- INIT由调用者明确授权丢弃旧context；不能用INIT中途abort证明旧context保护。STEP有显式ready/accept，配置pending优先，参数锁存；position只允许0..72，STEP拒绝72与溢出端点。
- offer直接给unit/epoch；position+1、!bank从稳定的已发布镜像派生；head由调用者锁存的5bit context提供，DUT没有不存在的candidate_head端口。消费方这至少5bit存储未计入DUT面积。
- consumer accept后进入不可撤销COMMIT0，立即拒绝abort，随后发单128bit descriptor写；只有ACK后响应committed。外部原子写及“ACK保证写已生效且不会再次生效”是fabric合同，并非已证明目标宏性质。

共享S只有16KiB、128bit、单1RW。采用Dtile1：片内实际对象8224B，后续V预留512B、其余7648B；未使用范围用canary检查。完整状态128KiB无法驻留在16KiB内，实际使用固定1MiB外部窗口：双state各128KiB、trial128KiB、I64 proposal256KiB、双Y各512B、descriptor16B、72步coeff186624B。有效mutable容量656400B，连coeff有效843024B，剩余地址也计入1MiB库存。旧published bank本身充当不可变old，没有免费多复制一份old。

## 实际执行结果

正式冻结实验源码：`af2f7fb171ad04158ed861c72c87133dfc5454d4`（phase7）；RTL与map04的`5eccf820d29a8a2e7af9353843a55ab08817de63`逐字节相同。RTL SHA-256：`5c8481c1db635ed3fb22335b605a211be7646726ff4d8c81c3c49fc111aa9113`。归档/门级严格行接收工具：`b32136000cb4aab0690374866767f307151b567b`（phase8）。

|验收对象|quiet/背压各自记录数|实际结论|
|---|---:|---|
|real005/real105|82|INIT+72完整步+9实际RESTORE；各比较2,686,976状态码、10,496输出码；原72逐位相同|
|protocol005/protocol105|31|11阶段soft_abort、同拍ACK、迟到private write、不可取消commit、两种硬reset写恢复、cfg pending、stale tag、peer holder及终止epoch|
|boundary005/boundary105|36|19项固定合成码域；6项通过、13项按合同拒绝，另有全head重标阶段abort/恢复|
|4 rawgate + 4同driver RTL|每次2记录|真实position0/27检查点RESTORE+STEP；完整状态/Y、公共metadata、cycle与IO完全相等|
|negative02|3实际文件负例|改state码、unit镜像、commit恢复记录后重新计算artifact SHA；完整receiver因独立语义拒绝，而非hash失败|

原72本批tokens/attempts无跨head wide_guard事件。因为原32head代码在wide_guard时可能整体重标，不能未经检查就将所有单head轨迹视作等价；输入工具对此显式拒绝未解释事件。原72 B/C是共享[72,256]，X为[72,32,128]；未凭模型名称推测形状。

边界覆盖alpha=0/1/0.5、正负ties和INT32极值、合法负shift/左移越界、全head末元素引起统一重标、dtB溢出、8次retry耗尽、unit/epoch耗尽、完整N readout guard、输出I32 guard、非法alpha/header/owner/profile/unit/position。所有合成输入都是声明码域，不属于模型质量测量。

硬reset测试让private或descriptor写真实生效、但ACK尚未交给核心；屏障排空后RESTORE读取真实descriptor。private场景恢复position0，commit场景恢复position1。静态审阅还发现并修复abort与有效响应同拍时的排空边界、reset的peer假握手、generation耗尽idle同tag迟到响应。终止epoch是声明的RTL寄存器注入；门级没有Qpoke，也未对该终止态进行门级证明。

## 同精度真实成本

|实测对象|quiet周期|背压/peer争用周期|外部事务|S32乘法次数|
|---|---:|---:|---:|---:|
|72连续+INIT+9RESTORE|148,909,146|175,736,069|5,371,650|7,171,328|
|首步STEP，同driver RTL/rawgate|2,047,764|2,416,604|73,923|98,688|
|position27重标STEP，同driver RTL/rawgate|3,419,094|4,025,216|114,883|164,480|

每笔read/write都是实际5个128bit beat：四header加一个payload。因此72连续总payload85,946,400B，本协议计费线字节429,732,000B；32bit请求generation与32bit响应generation sideband另列，未伪装进这5拍。首步S读147,968次、写33,026次；重标步S读230,272次、写57,666次。数据和宽proposal反复取存是本候选主要成本，不能只报告S32乘法次数。

上述active FSM cycles包含实际INIT/RESTORE/offer停顿，未把debug canary读写或host预放外部输入的时间算成计算性能。背压相位与测试条件固定；不换算CPU/GPU速度、目标GHz或端到端模型时延。完整消费者Y读取至少还需要512B/head/token（若走同外部RAM），本轮没有执行，不能省略后称端到端闭环。

复位前已花成本单列在cost02：quiet private-write reset前2,447周期、163读/1写；commit-write reset前2,047,751周期、41,122读/32,801写。它们不会因reset清零而被记为零，不与完整事务sum混写。

实际map04及原Liberty逐cell独立面积求和：**41,708.534µm² logic-only、28,221 mapped cells、3,084 DFF_X1、3,285 generic register bits**；精确一个32×32→64 signed multiplier、一个16KiB128bit1RW wrapper，无M8、无隐藏native除法。与97整合时不能把这个独立R的16KiB和现M/V的16KiB免费相加。

面积不含SRAM宏、外部fabric、消费方控制。外部单credit模型至少194bit pending字段（data128+addr32+generation32+wr/valid2），另外65bit applied/delay是测试环境；单1MiB RAM另计。rawgate理想时钟/零延迟库功能检查不是RC、时序、电气、功耗或目标工艺签核。门级4次墙钟44.21/52.16/73.94/87.56秒；按预登记1200秒单步上限，先独立接受首步pilot再启动其它三条件，没有无限重试。

## 对Block划分的可用结论

1. **R拥有完整head的数值和提交域。** Dtile可以细分，但不能给每个tile私自改unit并发布。全head guard、统一重编码、完整N归约、unit/epoch与state/Y指针提交应该保持同一逻辑责任方。
2. **状态容量不是普通M/V帧可以免费吸收的附属数据。** 单head就有128KiB published状态；当前保守事务保留trial/proposal/shadow后外部库存显著。物理R/S边界必须规定bank归属、spill/重读、端口与ACK，而不能只以算子图画一条“状态边”。
3. **宽算术是已实现且有费用的候选。** 共享S32、RNE移位/guard/max/地址/打包控制都进入真实网表。alpha端点旁路已验证；没有把8位M阵列当免费32位乘法器。
4. **当前结果支持一个可接续的R状态单元，不冻结最终物理边界。** 下一步优先比较相同精度/容量/端口下减少重复S行读取与外部proposal/clone流量，再接入已冻结M/V消费者资源仲裁。Dtile1不是最优吞吐，不能用本结果宣称最终Block设计完成。

## 数据与交付

完整大包：`/public/home/yuzelu/RuizhiLiang/issue99-r-state-20261025/delivery01/full.zip`，125,298,753B；SHA-256 `f5cb47e12c4b15320b5e26f30ee165d0b03e9bcf48f7a6b3cc8829b0b8b833bd`。675成员、291嵌套artifact、8phase101原Git源码全部由服务器独立字节接收通过。

[精选索引](../../project/experiments/r_state/results/issue-99/index.json)：selected.zip为1,183,475B、226成员；SHA-256 `e325e0a83099c203f547987867ff5a79d7476f2904959c2e9a3f2ced064297d7`，服务器和PC字节接收均通过（精选含40份源文件，其余原源在全包）。index的生产者状态保留ARCHIVED_AWAITING_INDEPENDENT_BYTES；随后两份server byte receipts和local receipt是独立验收，不篡改原index。精选只含适量结构化证据；全部实际输入/每步raw state/Y、maps、build binary、source、命令、日志、错误和负例在全包。

[实际执行命令](../../work/Liangruizhi/99/execution.json)、[工具说明](../../project/experiments/r_state/README.md)、[交接](../handoffs/2026-10-25-issue-99-r-state.md)。inputs01共享B/C形状读取错误、inputs03旧JSON键名错误、build01/map01语法错误和六个仅本人DependencyNeverSatisfied取消记录均保留；没有改写失败为通过。常规结构检查和本机字节接收完成，全部实际数值/RTL/map/gate在服务器。

本地结果已整理；远端任务分支、PR与看板由主会话统一交付，本子任务没有push、开PR、自合并或将Issue标done。登记PR5 pending与Projects权限限制仍须按主会话最新回执处理。不得把本地完成写成远端合并/正式验收。


发布回执（2026-10-25）：[PR103](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/103)已上传；Issue99为in_review，待独立审查合并，未done。远端读回798739afbe1a738c64043e85b741229a748409f5报告/索引/cost02/严格门级行回执与原Git blob逐字节一致，见work99/remote-readback.json。已合父93最新发布回执，实验RTL/原源绑定不改。登记PR5 pending；board配置/read:project缺项，状态unverified/同步pending，管理员及审查人待指定。后续Q35 GDN和共享服务仍缺，不把本有界任务完成写成Block库全部完成。
