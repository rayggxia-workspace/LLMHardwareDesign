# Issue104：Qwen3.5 双头完整 GDN 状态电路验证

日期：2026-10-25。负责人 Liangruizhi；[Issue104](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/104)，分支 `task/104-gdn-state`，基线 [PR103](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/103) `8c51f5df74ff5658ee159ee463f13dea6f691237`。成果待主会话推送/PR/独立审查；未合并，非 done。

## 本轮完成了什么

实现了两个完整 K128×V128 head 的 GDN 状态更新 RTL，真实执行连续 decay→全 K prediction→aligned value/residual→beta correction→完整 outer/state guard→全 K readout。仅使用一个 16KiB/128bit/1RW scratch 和一个共享 signed32×signed32→signed64 服务。两个 head 的状态、单位、numeric epoch、独立 position/version 和输出统一发布，不能拆成两个独立 head 提交。

native32 与 portable12 各在 quiet、背压/peer 竞争两种条件下通过独立 Python 任意精度接收。后者从原本非零 checkpoint 继续，真实两次只重标 head1，但每次完整重算两头、group epoch 只增加一次；最终 position7950/version14/units[-27,-31]/epoch2。原 68 portable 轨迹及原 66 native 完整33个状态/32个输出均逐位相等。不是新整模型量化质量测量，也没有运行完整256步。

## 数值合同与宽实现

状态码域为 `[-2147483648, 2147418112]`，不是普通 S32 最大值；`0x7fff0001..0x7fffffff` 是非法导入，STEP 全量 clone 时直接 E_STATE，不能通过重标掩盖。Q/K/V 对称 S16；beta U16Q15、decay U32Q31 含精确1。I8单位含-128。prediction、aligned/residual、correction、proposal、Y 保留必要 I64；成功路径无 clipping，归约完成后才 RNE。

原始32/12真实子集含33位中间值，另补完整双head合成34位 aligned/residual/correction 再重标用例。`wide104` 以绝对值 radix2^31 分成31/31/1位，依次使用同一个 S32 服务做3次乘法；每个移位项、非负累加均在 I64_MAX 内检查，完整精确乘积恢复符号后才一次 RNE15。I64_MIN按合同拒绝，无免费128位乘法或部分乘积各自舍入。lowerer自身数据寄存器208bit（含64bit partial）加控制8bit，优化后的实际寄存/复用成本由综合计入。decay=2^31 使用显式 identity 分支，其余采用正常 signed32 服务。

原68保守 `maxabs(A)*maxabs(B)`、`maxabs(A)+maxabs(B)` 和完整 K reduction guard 没有被逐元素结果代替。当前固定域的格式上界可证明：`s=eS-eV>=-32` 时这些全局保守边界全部安全；RTL先做该格式准入，再执行对应运算，**没有另添免费全局最大值扫描器**。下界不满足时按原合同两头重标重试；准入后 s>62 是明确 E_FORMAT 拒绝。独立参考仍逐项计算原保守边界；合成格式/耗尽负例覆盖该准入。最多8次重标/9次尝试，单位/epoch/position/version耗尽均拒绝无回绕。

完整协议和逐位地址定义见 [PROTOCOL](../../project/experiments/gdn_state/PROTOCOL.md)。

## 连续 RTL 证据

stall=0 为 quiet，1 为确定性背压且共享 S32 的另一响应槽接受 peer 竞争；是目标候选周期，不是服务器耗时或 GPU PPA。

| 数据 | stall | 命令 / 提交步数 | 重标 wave | 完整命令总周期 | 外部事务 | S32 实际请求 | 独立阶段 pair |
|---|---:|---:|---:|---:|---:|---:|---:|
| native32 | 0 | 37 / 32 | 0 | 73,441,693 | 2,891,001 | 6,316,032 | 540,672 |
| native32 | 1 | 37 / 32 | 0 | 87,399,518 | 2,891,001 | 6,316,032 | 540,672 |
| portable12 | 0 | 14 / 12 | 2 | 30,763,438 | 1,166,046 | 2,697,728 | 236,288 |
| portable12 | 1 | 14 / 12 | 2 | 36,490,030 | 1,166,046 | 2,697,728 | 236,288 |

总周期含 RESTORE，未包括离线初始外部镜像放置、调试 canary 和调用者导出 Y 的时间。每步无重标的实际 S32 请求为197376；真实重标额外运算、完整 clone、I64 proposal、shadow/state/Y、元数据及 root ACK 全计入。stage pair 检查含 prediction/residual/correction/proposal/output，两路均比较全部32768状态码和256个I64输出。不是只选 kernel 或少数坐标。

## 恢复和负例

两路各35命令覆盖14次各阶段中止（含 lowerer 请求/等待、private write 已落地未 ACK 和同拍 ACK）、一次消费者拒绝、持有 peer 响应跨 offer/reject/RESTORE、配置 pending 竞争、旧 tag 排空、private/root 写实际落地后硬复位与真正 root 恢复，以及 consumer accept 之后不可撤销的 commit-drain。主实验每8步重新 RESTORE 当前已发布 checkpoint。

14个完整双head合成边界各运行两路，覆盖34位值/双头同 wave、格式重试、I8=-128、非法状态上界空隙、Q=-32768、beta/decay越界、shift域、retry/unit/epoch/position/version终止。独立 lowerer 4177个固定/随机乘积、9个取消位置通过；12种非法 root/metadata 和 transport max 终止另有实际 RTL 测试。transport终止使用公开 RTL 输出寄存器注入，明确不是门级注入证明。

6个实际文件级语义负例复制已执行输出，修改 state/Y/stage/metadata/schema/contract 并重写全部 artifact SHA 后再调用完整接收器；均因数值/语义拒绝，没有用 hash 失败充当独立正确性验证。首次 build01 因 `small` 为 Verilog 保留字失败，新目录 build02 修复；原日志保留。

## 实际网表重放

从 map01 的真实 Yosys mapped.json 导出门级 Verilog，加载同一 Nangate45 Liberty 布尔单元，仅 scratch 保留原 `store82` 行为模型；未用 cut wrapper 或顶层输出强行赋值替代内部 FF。普通步及实际发生重标的 portable 第2步，均从已逐位接收的真实前序状态和描述符恢复，再跑 quiet/背压。首步 pilot 64秒完成，最长重标背压127秒，均在预登记单步1200秒上限内。

| 实际 checkpoint | stall | STEP周期 | 重标 wave | 与同驱动 RTL |
|---|---:|---:|---:|---|
| first | 0 | 2,295,044 | 0 | 全部 row、state、Y、stage、周期相等 |
| first | 1 | 2,727,573 | 0 | 全部 row、state、Y、stage、周期相等 |
| rescale | 0 | 3,906,442 | 1 | 全部 row、state、Y、stage、周期相等 |
| rescale | 1 | 4,565,862 | 1 | 全部 row、state、Y、stage、周期相等 |

连续32/12步证据来自 RTL；门级资格只覆盖上述两处完整两头 checkpoint，各2种条件。没有暗示门级重放全部连续轨迹或物理签核。

## 所有存储和端口成本

| 资源 | 实际合同 / 成本 |
|---|---|
| S scratch | 单16KiB、128bit、1RW；coeff1568B；decay pair实际2048B，仅1024B有效数；另留512B未来frame，余12256B未使用 |
| 发布状态 | 两个完整两头 S32 bank，共262144B |
| 私有 trial / proposal | 131072B / 262144B（I64，不靠 clipping 降宽） |
| Y / metadata / root | 两Y bank4096B、两metadata bank128B、原子root16B |
| 输入系数 | 32槽×1568B=50176B；并非256槽 |
| 外部窗口 | 整1MiB；active709776B，含mutable659600B；余338800B保留 |
| 外部端口 | 单 outstanding；每事务5×128bit物理拍；payload16B、wire80B，generation请求/响应另8B |
| 发布协议 | 至少4×16B metadata+16B root=80B写payload，全部逐项ACK |
| 消费者未执行费用 | 后续读完整两头Y至少2048B；本轮仅外部consumer accept cut，没有隐含完整 gated norm |

Vpair2反复读取四码外部行，proposal物化、两头 retry 和 shadow copy 都有实测事务；不能把这些状态放置数字直接当高吞吐最优方案。外部 request 至少193bit payload/address/tag/write、response至少160bit payload/tag的 fabric 缓冲是外部实现义务，未算进本地门面积。两代 bank 只在单owner、busy期间无外部并发读写、DONE导出完成后ACK释放旧引用的约束下安全；不是无限期 immutable snapshot。

实际 generic 库存为一个动态32×32→64乘法器，另一个5×常数49是 `slot*1568` 地址生成（再左移5），明确计价；没有 S8 bank/SFU/LUT。实际研究库映射35008cells、4359 DFF_X1，generic寄存4604bit（含store包装寄存）、一131072bit存储；逻辑面积 **53065.404µm²**，包含控制器、宽分解、仲裁、元数据与观测寄存。SRAM宏、外部fabric、共享106新增mux/ownership、consumer和布线未包括，不能称总面积或PPA。

## 对 Block 设计的影响及仍需完成

现在 R 候选有两种实际数学的电路证据：99覆盖Falcon/Mamba形式，104覆盖Qwen3.5的GDN，不再用前者替代后者。可以固定完整 reduction/RNE、较宽 residual/correction、范围检查及私有trial→两头原子发布等数值与状态边界。S32宽服务可复用的可行性已有真实RTL与门级证据，但代价很高：完整状态复制、有限容量物化和数据重读需要保留在调度/互联账本。

104仍是独立核心。下一步共享106整合时要抽出 store/link/mul 接口，统一transport generation，外部窗口显式搬迁（当前040..041），每STEP重装coeff/decay scratch；不能把99/104/97/102各一份预算相加叫共享。需继续整合真实V/A/M消费者、宏/STA/RC与完整模型质量。当前不能冻结物理合宏、金属定制拓扑或声明六Block全部正确完成。Phi未解封，无新模型下载、无其他机器任务或工具安装。

## 可复查交付

实际 RTL 字节：gdn104.sv `06defa55ef52d84b519a3c32ded94f204bbd38ba3fe81ad622682a50e5e43d47`；wide104.sv `c623eb27ec992af1ae4411261ed75fccf886100fc294cf280f6a00c15905c890`。编译源 d1297fe，连续/映射 b8d5166 同RTL字节；最终严格receiver 2b5bba4，审计8c82337，归档5891d47。精确argv/Slurm/source绑定见 [工作记录](../../work/Liangruizhi/104/README.md) 与 execution.json。

全部数字/真实张量/bigint/RTL/map/gate仅本人服务器 `/public/home/yuzelu/RuizhiLiang/issue104-gdn-state-20261025`。完整包 `delivery01/full.zip`：59168676B，SHA-256 `dfcd406c50153fbc5e3fcee2575b3dd68d95b915c9ea91ccad21c2dede6f0c87`；精选入仓 `selected.zip`：1337983B，SHA-256 `0c3294def7285a88da14e166c884a906ab384e9c357734245c89de082d420c25`。

完整818成员/348嵌套artifact/8阶段134原Git源码字节已在服务器独立核验；精选147成员/25源码字节在本机独立核验。见[索引](../../project/experiments/gdn_state/results/issue-104/index.json)、[成本](../../project/experiments/gdn_state/results/issue-104/cost.json)及[交接](../handoffs/2026-10-25-issue-104-gdn-state.md)。下载/字节核验与数学/门级接收分列。远端Issue仍in_progress；本分支未push/未开PR，由主会话最终交付，登记/看板限制继承原项目实际状态，不写成已同步。

## 发布前补充：两头交叉非法域优先级

主包归档后独立审阅发现：RTL 在每个 ATTEMPT 先统一检查任一head的 `eS-eV>62`，但旧独立参考先逐head计算保守 fmt；当一头>62、另一头<-32时，旧参考可能先做一次两头 WIDTH 重标，再抛格式错误。这是独立参考对**新合同非法域优先级**的缺口；真实 native32/portable12 的全部单位范围远离该域，既有真实轨迹、RTL、映射与门级结果不受影响。主归档保持原字节，未改写旧结果。

提交5539590将独立参考改为每次attempt开始先检查两头任一shift>62，立即 E_FORMAT，再进入其他保守 WIDTH 判断。补充使用非零32768状态码及非零256个I64旧输出，两头shift分别[63,-33]与[-33,63]，quiet/背压共4次真实完整RESTORE→STEP；复用同build02/driver，RTL无修改。

| 交叉边界 | stall | shift两头 | 实际status | retry | STEP周期 |
|---|---:|---|---:|---:|---:|
| mixed_shift_high_low | 0 | [63, -33] | 12 | 0 | 189,887 |
| mixed_shift_low_high | 0 | [-33, 63] | 12 | 0 | 189,887 |
| mixed_shift_high_low | 1 | [63, -33] | 12 | 0 | 260,030 |
| mixed_shift_low_high | 1 | [-33, 63] | 12 | 0 | 260,030 |

全部 E_FORMAT=12、retry=0、mul=0、wide_calls=0、offer=0、stage流为空；独立reference Refusal(12,attempts=[])。每例实际root+metadata+完整state+完整Y共133200B在拒绝前后逐字节不变，不以零状态掩盖误清空。STEP已完整clone/验证state，但未发布或重标。

补充e664827独立保存于服务器 `priority-delivery01/full.zip`：628816B，SHA `64abc061bf3615fbde4c02d730e5d9d9f1239f0aec2d5131ed35e077dcac92ae`；精选105816B，SHA `5b7f98481e3713b18b8ce9b7f65cdc4962ba9bb59fe07651ca25a4a38f419a5a`。完整80/精选63成员、27原Git源码字节通过，完整另核28嵌套artifact；[补充索引](../../project/experiments/gdn_state/results/issue-104/priority-supplement/index.json)、[数值回执](../../project/experiments/gdn_state/results/issue-104/priority-supplement/receipt.json)与双byte回执在仓库。既有门级不重跑；后续复用应使用补丁后的reference并同时接收主包与补充。
