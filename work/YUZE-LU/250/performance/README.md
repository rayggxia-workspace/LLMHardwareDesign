# Issue250：共享 X、原 S 内 X 与三 P 联合时序

Refs #250，数值/模型底座为 PR249 `85fe7989b11a95725c9b1bc6daee085f74a500b8`。
本目录由独立 worktree `task/250-shared-x-evaluation` 维护，没有修改旧实验目录。

## 比较条件

- Qwen2.5-3B，GPTQ W8/A16，36 层，B1、context512 decode，一个输出 token。
- 3P、新 M K16×N8，每 P 权重读 128B/cycle、A 32B/cycle；保留四个有限完整权重 record bank。
- 持久状态 S32/Q16，Mid S32，`NV_EXTRA=1`，总 DDR 51.2GB/s、300MHz。
- 原程序、trace、W8 record/scales、M 命令及全部算术保持不变；本实验只改变 FFN X 的本地驻留与供数服务。
- 精确恢复原执行源而非从更新过的编译器重新生成；基线必须复现 **9.21564723269 token/s** 及相同 `end_subcycles`。
- 未执行新整模型数值 RTL，也未取得 3P 共享池、K16 tag 桥、新 S feeder 的物理资格。继承的 PR249 数值证据边界不扩大。

## 两种候选

**共享 X：** 32KiB、8×4KiB 1RW SRAM，读端全局最多 64B/cycle，不是每 P 64B/cycle；无广播。
每 P 一个 4×64B FIFO，credit 同时计算在途和已到达数据，最后 64B 内两次 32B 真正消费后才释放 credit。
每个 FFN 只 BEGIN/FILL 一次 4KiB X，写 ACK 完成再 SEAL。SEAL 后只读，不能顺便把 Mid 写进池。
Mid 和 down A 保留原来的有限 256B 临时交接通路，私有 S、四个权重 bank 不加 LVT，也不扩容。
RELEASE 等所有 LOAD 最后消费、额外退役拍、FIFO、命令元数据全部排空。

**S 内 X：** 在现有每 P 16KiB S 放 4KiB X，移除独立 4KiB X feeder。
`main c4d7b9605` 的 `local_s_p.sv` 外部普通请求及 A feeder 均为 128b；内部四 bank 同 row 的 512b 读不等于外部 A32 已实现。
因此原生 16B A 和需新 RTL 的 32B A feeder 分开计时；X 写入始终按 128b 客户端，并与其他 S 访问共用日历。
32B 候选需要新的配对、valid、尾部和握手电路，不能仅改计时宽度便算完成。

### 原 S 内地址窗候选

下面是容量/银行可审计的候选，尚未声称地址分配 RTL 已实现。普通 16B word 的 `addr[1:0]` 选 bank、`addr[9:2]` 选 row。

| 字节地址（闭区间） | 大小 | 用途 |
| --- | ---: | --- |
| `0x0000–0x0abf` | 2752B | 原 S32 Down 累加状态保守窗 |
| `0x0ac0–0x13bf` | 2304B | 原模型双 record 保守预算；四个真实权重 bank 另计，不在此凭空取消 |
| `0x13c0–0x15bf` | 512B | 历史 double-A 容量预算；最终 A slot 外置后从 S 逻辑活跃量剥离，此区不再凭空存第二份 A |
| `0x15c0–0x19bf` | 1024B | 128 点 gate/up 区 |
| `0x19c0–0x1dbf` | 1024B | 原 Mid/交接保守区，S32 Mid 的 512B 实际对象在其中 |
| `0x1dc0–0x1fbf` | 512B | 原控制/交接保守区 |
| `0x1fc0–0x1fff` | 64B | 对齐空隙 |
| `0x2000–0x2fff` | 4096B | X，每个 bank 1024B，对应各 bank row128–191 |
| `0x3000–0x3fff` | 4096B | 余量 |

原 FFN 保守 8128B + X4096B = 12224B。最终将 A slot 外置，S 活跃量再减 512B，成为 **11712B/P**；保留上述保守地址窗时最高地址仍为 12288B，均小于 16384B。
这只说明容量不增加，接口/银行的时序仍须通过真实 RTL 验证。

## K8/A32 到新 K16 的合同变化

PR243 原 A32 是两个各含 8 个 S16 的 128b 容器，不是天然一个 K16 同 row 数据。原顺序为 tile-major、row 先递增。
本实验仅 B1/row1，两个连续容器才确实属于同 row 的连续 K16；独立整数 transport oracle 检查配对、尾 mask 与有符号 dot 不变，并拒绝把双 row 容器直接拼成单 row K16。

第二轮提出一个明确的新接口：单个 LOAD 覆盖 K128/A256B，即 16 个原生 128b 容器，包含 8 次 32B M 接受。
原 `tiles<=4` 需要扩展到 16，3P reader、容器配对 tag、描述符模板/循环服务需要新 RTL。此处输出一律 `RTL_qualified=false`。
每 P 最多一个 accepted LOAD，active+prepared 总槽为 1 或 2；其余至多四个权重 bank 任务记录不是 accepted pool descriptor。
每 P 的描述符准备串行占该 P 的有限控制日历，但不应占据其他 P 的全局 SRAM 读端口。
准备 1/2/4 拍、1/2 槽、SRAM response2/4 拍分别测量；最后 32B 接受后另计 1 拍 LOAD 退役。

## 执行、失败与回收

所有 C++/SystemC 和整数 transport 回放均在授权服务器 Slurm 分配节点运行，没有在登录节点或本机执行。
文件中的 `20261110` 是本任务申请的独占根前缀，任务跨日继续沿用该前缀，不改他人目录或任务。

| 包 | Slurm | 配置 | 结果 |
| --- | --- | --- | --- |
| 01 | 102055 | c64 6×10 | SHA 清单 CRLF 导致准备门失败，未执行模型；修正后用新目录 02 |
| 02 | 102056 | c64 6×10 | 第一轮六配置完成；保留保守串行描述符反例与未获原生资格 S64 对照 |
| 03 | 102057 | c96 8×12 | 消费退役代码位置错误导致编译失败，未执行模型；修正后用新目录 04 |
| 04 | 102058 | c96 8×12 | 八配置全部完成，等工作量/对象/FIFO 独立检查通过 |
| 05 | 102064 | c96 8×12 | 描述符更高开销压力、有限双 A 预取及 S phase 成本对照，结果见后续回执 |
| 06 | 102068 | c96 8×12 | 相邻同对象/同 kk 的只读 tile lease，A16/A32、phase2/4/8 全完成 |
| 07 | 102071 | c96 8×12 | 有限 early-copy、A1/A2、phase2/4/8、copy ACK 敏感性全完成 |
| 08 | 102074 | c96 8×12 | 最终准备2/8/16拍、phase4/8、state/copy ACK1/2全部完成 |
| 09 | 102075 | c64 6×10 | 六 seed 的整数配对/尾部、多消费者重放及八项协议负例全通过 |

第一轮 02 的完整时序结果：

| 配置 | token/s | 解释 |
| --- | ---: | --- |
| 原 4KiB X feeder | 9.21564723269 | 原基线精确复现 |
| 共享池、每 64B 描述符 0 拍 | 9.22603374894 | 理想下界，不能直接冻结 |
| 共享池、每 64B 描述符 1 拍串行占全局端口 | 8.73426674695 | 保守反例：错误耦合控制与全部 P 数据端口 |
| 同上 2 拍 | 7.45448329771 | 保守反例，不隐去失败 |
| 同上 1 拍、SRAM latency4 | 8.73267415616 | 延迟敏感性 |
| S 内 X、沿用共同基线 S64 模型 | 9.21760439292 | 只证明时序模型可略高于基线；外口 A32/S64 尚无原生资格 |

第二轮 04 的完整结果见 [`summary-04.json`](summary-04.json)：

| 配置 | token/s | 相对基线 |
| --- | ---: | ---: |
| 原 4KiB X feeder | 9.21564723269 | 0 |
| 共享池，active+prepared2 槽，准备1/2/4 拍 | 9.22603374894 | +0.112705% |
| 共享池，总1 槽，准备2 拍 | 9.22603374894 | +0.112705% |
| 共享池，2 槽、准备2 拍、SRAM response4 拍 | 9.22601332026 | +0.112484% |
| S 内 X，原生 A16 顺序供数、ACK1 拍 | 8.58292567011 | −6.865731% |
| S 内 X，新 A32 顺序供数、ACK1 拍 | 9.16580471439 | −0.540847% |

全部八组逻辑读 **3,365,952,512B**、写 **8,191,232B**、M 命令 **3,028,352** 不变，bus 字节、DMA 描述符、G/向量/算术工作也守恒。
共享池每组 36 个对象、fill147456B、实际读405798912B、1585152 个 K128 描述符；每 P 预约峰值均 256B，issue/arrive/consume 严格一致。
准备开销由各 P 独立承担且有限槽预备，1/2/4 拍在本范围被权重等待隐藏；这不是把控制服务费用改成 0。
这轮仅通过条件时序 gate，正余量约 0.11%，不足以跳过真实 descriptor、端点、RC 或新 RTL 对照。

第三轮同时检查不增加共享池的备选：将原预算 512B double-A 分成两个 K128/A256B 槽，各带 slot generation、对象 epoch 和 K 索引。
通过有限加载线程在独立 W bank 填充期间先从 S128 取 X；M 必须 JOIN 真正 A ACK 和 W_READY，最后 operand 消费后才释放 A 槽。
同一 S 日历包含普通访问、feeder 读、SRAM 响应和 phase 切换；Down/state 的普通读写 ACK 也按 128b 口另收费用。
这是新的有限 A 加载/联锁候选，不是旧局控已经支持的功能；若最终采用，32KiB 共享池及其 FIFO/端点必须从底座删除，而非保留闲置硬件。

## 最终候选与进一步迭代

推荐首版选 **NoPool、原 S128/A16、两个外置 A256B 重放槽、只读 tile lease、有限 early-copy**。这是经过多轮失败后得到的条件时序候选，尚待实际 RTL/面积/时序验收。

| 阶段 / 配置 | token/s | 相对原基线 | 结论 |
| --- | ---: | ---: | --- |
| 只提前取 A16，2 槽、phase2 | 9.08029867935 | −1.468682% | 仅预取未过门 |
| A16 + 同 tile 多消费者 lease，无 early-copy | 9.20817282797 | −0.081106% | A16/A32 同速；本地 A 带宽已被隐藏 |
| A16 + 2 槽 lease + early-copy | **9.2237871361** | **+0.088327%** | 无需增加共享或私有 SRAM |
| 同上只有 1 个 A256B 槽 | 9.1985173609 | −0.185878% | 1 槽不足，保留反例 |
| 最终方案、准备8拍、phase8 | 9.2237871361 | +0.088327% | 有限控制费用被隐藏 |
| 最终方案、准备16拍、phase8 | 9.22152273898 | +0.063756% | 控制更慢仍过门 |
| 准备16、phase8、state ACK2 | 9.22015759536 | +0.048942% | 普通状态 ACK 敏感性 |
| 准备16、phase8、copy ACK2 | 9.21879897487 | +0.034200% | 源/目的 copy ACK 敏感性 |
| 准备16、phase8、state/copy ACK均2 | **9.21743463751** | **+0.019395%** | 最坏已测联合压力仍不低于原基线 |
| 32KiB 共享池、2 槽、准备8、response4 | 9.22601332026 | +0.112484% | 作为对照保留，吞吐差约0.0022，不据此增加32KiB池 |

完整失败/通过配置分别保存在 `summary-04.json` 至 `summary-08.json`，没有删除慢配置。
共享池的准备16拍、response8 或不充分准备槽也会跌过基线，说明控制/返回延迟确有边界，不是随便写一个恒定成本就能通过。

最终方案是一般的只读 tile 驻留：一个 `(object epoch, K128 index)` 只加载一次到有限 A slot，再按原8次32B/M命令重放；真实计划声明本 tile 的消费者数量。
生产者看到下一个 tile 时关闭当前 tile 的新引用，只有 `closed && completed==planned` 且最后 operand 真正接受后才 free，暂时 busy=0 不能释放。
两个 slot 最多预取一个下一 tile，不保存整行4KiB X；每 M 的 W record/use sequence 仍独立，不能复用旧权重。
因此每 token 的 S X 实读从 **405798912B 降到38043648B**（减少90.625%），其中1436544个M任务重放已驻留tile；原DDR字节、算术和M命令数全部不变。

early-copy 从归一化器每个 K128 输出的真实 S 写 ACK 启动，只读已经有效的块。
三条原16B/cycle unicast 各只有一个16B保持寄存器；源 U S128 请求统一仲裁且一次只有一个读在途，目的 S128 写 ACK 完成后才能发该路下一字。
每 FFN 三个有限 copy FSM，等待三个目的全部4096B ACK后才开始投影；没有广播和隐藏的返回 FIFO。
每 token 源/目的各实搬442368B，三个目的的写入量与原三次整行搬运相同，收益来自和下一片归一化重叠。

### 资源与面积账单

| 资源 | 最终 NoPool 首版 |
| --- | --- |
| 每 P 私有 S | 原16KiB、原四 bank 1RW，不加 LVT，不扩容；X占其中4KiB |
| 四个 W record bank | 保留，与 S/A slot 独立，容量/端口仍按共同基线计 |
| 每 P 4KiB X 寄存器 | **删除** |
| 每 P A slot | **新增外部2×256B=512B寄存器**，每拍32B读给新raw M，S128写入/拼接，generation及consumer控制另计 |
| 每 P copy holding | **新增16B寄存器和有限copy FSM**，另计控制/端口/时序 |
| 全局32KiB共享池 | **首版不实例化** |
| 每 P 4×64B pool FIFO | **首版不实例化**；不能与A slot同时免费保留 |
| S 中历史double-A512B预算 | 从最终S活跃量剥离，不能再重复认定其已实现为新A寄存器 |

每 P 外置 A/copy 数据寄存器共528B，三 P 共1584B；新 raw M 本身不含 A RAM，这些寄存器不是旧宏的免费功能。
删掉的三份4KiB整行寄存器共12288B。不能仅将字节差换算成芯片面积：新增前端FSM、MUX、valid/tag、S端口联锁、供电及300MHz物理资格都要实际综合验收。

新 G 四寄存阶段中的最终 RNE 已直接产生 S32/Q16 Mid，替代旧 G 三阶段67拍加外部 `NV_MID=1` 的1拍。
128有效值、两lane时两者完整帧均按 **68拍**收费；Mid→Down A16组max/RNE的66拍及 S 写ACK仍独立。
因此这里没有靠把新 G 延迟或小表成本减掉来满足性能门。

## 证据范围

累计46次完整36层 decode 时序回放，历史基线逐次精确复现，全部通过DDR/bus字节、M命令、算术/向量/G工作量守恒。
九个实际源/日志包含两个未进入模型的失败包；离线审计 `shared_x_audit.py` 逐成员SHA并核对各轮结果。
独立整数oracle的六seed共66个配对/尾部用例、216个有符号K128多消费者重放用例，以及48项协议负例检查：partial-prefix、错generation、重复response、错W use、未来消费者、迟到最后接受、重复完成、复用后旧generation迟到。

这些证据不等价于完整原生模型RTL、真实母控/局控程序执行、能耗估算或P&R。最小正裕量很小，下一步必须用实际A前端/LC/FSM/MC端点和G握手trace校准，并继续按同资源门迭代；原16KiB S叶宏的资格也不能自动覆盖新增逻辑。

`run-*.tar.gz.b64` 含各轮实际源、源 SHA、job/工具/分配回执、日志和结果；`recovery-*.json` 列每个成员的 SHA-256。
失败包同样回收，不能仅保留通过包。

## 复现

本机只恢复文本和校验 SHA：

```powershell
python project/experiments/stream_quant_synthesis/shared_x_prepare.py work/YUZE-LU/250/performance/prepared-NEW
python project/experiments/stream_quant_synthesis/shared_x_deploy.py work/YUZE-LU/250/performance/prepared-NEW NEW --receipt work/YUZE-LU/250/performance/submission-NEW.json
python project/experiments/stream_quant_synthesis/shared_x_collect.py NEW --out work/YUZE-LU/250/performance
python project/experiments/stream_quant_synthesis/shared_x_analyze.py work/YUZE-LU/250/performance/recovered-NEW --out work/YUZE-LU/250/performance/summary-NEW.json
```

`NEW` 必须是新的数字标签，脚本拒绝复用已有服务器根。提交前需遵循当前远程规则和授权。
