# 母控与局控前端集成验证

本轮以 PR #180 的 `de58b0d04446ea80134b8c541b08c209e1edaf52` 和 PR #176 的 `08f2ea20a11dfdd09892a67599163e32b7237edb` 为基线。控制器保留现有镜像和默认配置入口，新增显式启用的原生组配置，用当前 64 bit 取指和执行逻辑连接 P/U/C/F/J 候选。

## 固定来源

| 输入 | 固定版本 | 用途 |
| --- | --- | --- |
| PR #213 | `1bb43127e9e59a1bf72b2ae7e821e207343dcfc1` | 紧凑 C/F/J、C/F 独立发送保持槽和双向交换用例 |
| PR #214 | `33821f73c601ddec81a53264b8c62008fc665aff` | 独立叶宏 P/U、操作数计数修复和 257 组旧 E 核对照 |
| PR #195 封存控制包 | SHA-256 `3387aa6f05f5fdd658e0ce326fce70fd694200c1882a4a5941c4fa6ddafea281` | 使用其固定适配器和输入夹具，再覆盖为本分支的控制 RTL 与镜像工具 |
| SRAM bank 模型 | SHA-256 `6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7` | 真实 SRAM 行为模型 |

[源码锁定清单](upstream-lock.json)核对 46 份指定文件的 Git blob。准备两个上游版本的源码目录和封存控制包目录，Python 3.12 运行阶段生成四套独立试验目录。该过程校验输入后生成当前控制接线和 v2 镜像，原始上游输入保留。

```bash
python3.12 project/control_frontend_v1/stage.py DEP213 DEP214 QUALIFIED staged
CAMPAIGN=p SRAM_BANK=BANK VERILATOR=verilator bash project/control_frontend_v1/run.sh staged results/p
CAMPAIGN=u SRAM_BANK=BANK VERILATOR=verilator bash project/control_frontend_v1/run.sh staged results/u
CAMPAIGN=cfj SRAM_BANK=BANK VERILATOR=verilator bash project/control_frontend_v1/run.sh staged results/cfj
CAMPAIGN=duplex SRAM_BANK=BANK VERILATOR=verilator bash project/control_frontend_v1/run.sh staged results/duplex
```

## 原生组的局控配置

`ENABLE_NATIVE=1` 使用 ABI `0x01930001`。组类型号按该 ABI 为 U=0、F=1、C=2、P=3、J=4，拓扑由 `NATIVE_TOPOLOGY` 固定。镜像使用版本 2，资源位 0 表示原生适配器入口，执行表允许 1 至 32 条记录，对象和传输表为空。L_EXEC 读取对应记录，L_WAIT 等待服务身份匹配的完成。原生操作和地址参数交给适配器检查。P16 的既有独立配置仍按自己的 ABI 和 1 至 8 条执行记录运行。

母控、局控和各适配器继续采用有界并发。新增配置验证了错误 ABI、拓扑、容量、资源掩码、版本、记录数、保留位、填充、任务类型、执行字段和原生命令。拒绝发生时核对宏请求数，防止错误输入产生副作用。1 和 32 条记录分别通过配置边界检查。

## 可综合的母控—双局控连接

[`two_local_link.sv`](../control_rtl_min_v0_1/two_local_link.sv) 为母控提供两个固定任务目标和一个返回通道。任务按目标 0/1 路由，目标 2 不握手。返回通道带一个 512 bit 寄存槽，槽内消息在母控背压期间保持，只有被接收后才可替换。两端同时请求时先选 LC0，LC1 保持请求。当前有界任务协议足以排空；本模块不承诺无界 LC0 流量下的公平仲裁。

返回增加一个时钟周期的寄存延迟，目标周期仍为 3.333333333 ns。同步低有效复位清除返回槽，并禁止复位期间的有效输出。单时钟模块不承担生产 CDC 或实际 M11/M12 串化。当前原生双局控和既有 P16 试验均已接入该模块。`router_check.py` 覆盖路由、背压下另一端晚到、同时返回、带消息复位及复位后恢复，并执行零警告 lint 和结构综合。

```bash
python3 -B project/control_frontend_v1/router_check.py --verilator verilator --yosys yosys --out results/router
```

## 实际完成的检查

| 检查 | 通过结果 |
| --- | --- |
| 当前 64 bit 控制器连接新版 P/U/C/F/J | 17/17，包含直连与回放、双向 C/F 程序、背压、原生故障和复位 |
| 原生 P/U、E、P 存储与 feeder | 4 个测试台各 3 种 SRAM 初态，共 12 次。E 每次完成 257 组旧核对照并检查读数次数 |
| C/F 原生交换 | 12/12，覆盖 C↔C、C↔F、F↔F 的单向、同时发送、写入／ACK 背压和复位 |
| 原生配置与执行准入 | 16/16，包括 14 个非法输入和 1／32 条合法记录边界 |
| 既有 P16 ACK、紧凑取指、旧镜像网络 | 分别 13/13、9/9、10/10 |
| 协调复位与旧响应清理 | 6/6 实际集成，11/11 协调器边界，包含既有 DMA 与 CDC FIFO |
| 既有 U/J/C 紧凑交接 | 分别 5/5、5/5、6/6 |
| 编码及镜像工具 | 42/42，两套 R6 输入各生成并独立验证三端紧凑镜像 |
| 母控—双局控返回缓冲 | 5/5 场景，零警告 lint，结构综合通过；接入后重跑原生 17/17、P16 ACK 13/13、准入 16/16 |
| 综合结构与 lint | 默认、P16 和五类原生配置 7/7。未见锁存、多驱动、组合环或缺失连接。最终 lint 的 13 条未使用信号诊断保留 |
| 回归敏感性 | 旧 U 在两源 FMA 得到 11 而参考为 6。旧 C/F 在同时发送时被检出无前进。两项均按预期失败 |

`native.sh` 运行原生基准，`exchange.sh` 运行 C/F 交换。`admission.py` 运行准入检查，`synth_check.py` 生成结构综合结果，`lint.sh` 检查控制 RTL。`legacy_mutant.py` 校验旧版输入后生成负例。旧 U 只增添用于连接测试台的未使用输入，保留旧的操作数读取行为。源码与报告散列见[验证摘要](../../work/Melodydt/179/frontend-validation.json)。

## 验收范围与剩余依赖

| 项目 | 状态 |
| --- | --- |
| 有界控制设计、原生组接入、程序装载和独立前端验证 | 本轮完成以上列明的场景 |
| A1 的正式双 P 顶层与七项部署绑定 | 待实现端确认，现有端口一致性证据保留 |
| 产品级数据与反向 ACK、实际串化格式 | 待正式端点接入后验证连续任务、身份匹配和释放 |
| 生产复位证书、实际跨时钟域接口 | 按正式拓扑迁移并复验 |
| 300 MHz 组合时序与完整物理验收 | 待同版顶层、宏视图、约束和寄生，周期固定为 3.333333333 ns |
| 九实例产品组网 | 外部集成任务单独验收 |

本轮综合是控制 RTL 的结构检查。时序、完整算法编译及模型数值质量分别保留其实际证据入口。早期准入夹具的结束流程、镜像头检查和填充地址匹配错误已修正，首次旧 U 负例因缺少新输入而停在编译，修正接口兼容后检出了预期数值差异。各次失败保留在获授权执行环境的回执中。

上游收尾复核：PR176 与 PR214 保持上述版本。PR213 更新了双向发送同步夹具和发送槽持有检查，选定 RTL blob 未变。最新两份脚本已按锁定清单同步，受影响程序 3/3 和原生交换 12/12 的最终结果见验证摘要。

## 最新输入同步及三初态回归

PR176保持08f2ea20；最终同步PR213至46c7c9db、PR214至709cfcd7。选定硬件未变，PR214更新回放脚本并加入三种初态与两源FMA检查；当前64 bit控制相关回归33/33通过。 输入锁保留逐文件Git blob。可选两源E/FMA回放按以下方式追加生成，再运行三组初态。SRAM_BANK、VERILATOR及BUILD_JOBS沿用上述约定；仿真在获授权服务器执行。

```bash
python project/control_frontend_v1/stage.py PR213_CHECKOUT PR214_CHECKOUT ACCEPTANCE02 staged --e-count-replay
for campaign in p u ue; do
  CAMPAIGN=$campaign THREE_INITIAL_STATES=1 bash project/control_frontend_v1/run.sh staged results/$campaign
done
```

两源U程序取两个指定源并将空第三源地址保持为非零毒值，检查不会误读第三源。P为1场景×3初态、U普通和两源各5场景×3初态。结果与源码散列见[native-control-and-top-validation.json](../../work/Melodydt/179/native-control-and-top-validation.json)。
