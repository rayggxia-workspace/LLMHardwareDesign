# 九组共同底座实施清单

对应 [#184](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/184)、[PR #185](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/185) 与 [#250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250)，合同版本为 `five-block-v1/2026-11-13`。[宏和控制资源 JSON](product-base-v1-inventory.json) 是候选库存。联合 ODB、全局 pin 坐标、原生网和最终 base_id 由实际布局导出。

## 每类一种实现

| 分组 | 选定功能叶宏 | 已有证据及联合缺口 |
| --- | --- | --- |
| P0–P2 | M60、G32、16 KiB S_P | M60/G32/S_P 各有独立物理包。原 P2545 的 S_base 窄口限定夹具通过。正式 P 改绑 S_P，需重新核对父层功能、负载、时钟和接入 |
| U0–U1 | N32、紧凑 E、16 KiB S_base | U39-v02 原版完整 DRC 为零，TT setup/hold +17.840/+0.566 ps，理想上层连接的组合门级 15 项通过 |
| C0 | R256、紧凑 G、紧凑 E、E32、16 KiB S_base | C V3 原版完整 DRC 为零，TT setup/hold +272.389/+6.445 ps。E32 是独立增量，保留紧凑 E 的服务 |
| F0 | 紧凑 G、紧凑 E、E32、16 KiB S_base | F19 原版完整 DRC 为零，TT setup/hold +462.551/+26.886 ps。E32 和紧凑 E 各占一个实际宏位置 |
| J0–J1 | E32、16 KiB S_base、T 6 KiB | J03 原版完整 DRC 为零，TT setup/hold +128.308/+18.263 ps。分拍、保持、饱和和写确认跟随实际 E32 服务 |
| 母控 | MC06，16 KiB 实体程序 SRAM | 独立原生 TT 300 MHz 通过，105 个门级场景。九组真实程序取指和整体控制连接另验 |

P/U/C/F/J 有 30 个功能叶实例。私有 S 共 144 KiB，T 共 12 KiB。U/C/F/J 的对应夹具各另有 4 KiB 局控程序 SRAM。P 现有局控使用 1 KiB 寄存器程序存储，联合布局按真实内容容量、端口和取指语义绑定。局控取指、母控镜像格式、128 位控制传输拍和 512 位 DDR 数据拍分别登记。C/F 的 E32 及 J 的 E32 分别源于 [C/F 集成](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/97d251d3e)和 [J 集成](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/f8e1a99e4)，U 的 N32 源于 [U 集成](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/5c8f9ea89)。每类同一实现复用于该类各实例，实例身份在父层分配。布局直接摆叶宏、局控、必要适配和实际 PM。逻辑组聚拢程度由物理试排决定。

## P 的供数与外存

正式候选复用独立验收的 `local_s_p`，使用普通 S128 口接当前 P 客户端。父层用两个按字节顺序排列的 128 位字组装 M60 的一个 256 位 A beat，保留真实的 session、beat 和 ready/valid。测试包括三个 P 的相同数据、写响应归属、背压、取消/重启和同工作量周期。原 S_base 作为窄口对照。RTL 105610 与 S_P 最终映射网表 105627 各六组通过，普通口握手、1,444 个 K 窗口、192 次程序调用及每组 1,123,200 次真实 64 B DDR 请求和返回逐周期一致。两份 comparison.json 的 SHA-256 相同，见候选库存。完整版图以 S_P 的实际 LEF/GDS/Liberty 和当前 RTL/SDC 重新提取。

S_P 原生 feeder 仍存在，A128 需有限的拼拍、身份翻译和保持后才能接 M60。启用 feeder 需另测普通读写互斥、阶段退出、完成确认和真实吞吐。S_P 的 B512 是本地 SRAM feeder 输出。M60 的 W512 接收端属于带 tag、分配、代际和关闭顺序的 DDR 返回合同。映射登记真实 64 B DDR 传输与内部 S128 的不同吞吐。S_P feeder 的可选服务在 RTL、实测周期和真实接点具备后才注册。相同容量的四 bank 宽读写也需要实际外露协议和验收回执。

## 端点和预连

- **叶宏原生端口** 从各选定交付的 DEF/LEF/ODB 读出。宏局部坐标在联合 ODB 随实例的位置和方向变换。pin 的位序、方向、真实网归属、形状及可接入窗口以该 ODB 为准。每个 driver 及 sink 要有真实端口和电气模型。原生接口的变更通过新叶版本交付。
- **局控与适配端口** 追到父层实际标准单元的 ITERM 和信号连通分量。短 M5/M6 线在本地逃到 M10。母控、交换器与九组局控之间的信号由 M11/M12 接通。固定逻辑控制关系、共享驱动的多接收端、返回选择、启动、复位和 drain 均按位核对。真实时钟、复位和供电由共同底座落实。
- **M1–M10 预连** 逐条给出真实 driver、sink 和用途。宏内部电路与已经选定的局控服务控制保持原样。P 的普通 SRAM 访问和 A 拼拍是正式候选的固定服务实现，联合下层是否预连至 M 的原生 A 端点由该路径的实际拥塞、时序和复用证据决定。任何锁定数据预连均登记完整位宽、协议、视图与固定网。
- **M11/M12 产品边** 按全部程序静态需求并集汇总同组与跨组连接。P M/G、U N/E、C/F G/E、C 的 R/E、J E/T 等每项逐路登记数据、地址、valid/ready 及 ACK。只有明确适配、物理端点和实际断点都存在的路径进入可部署候选。含同一驱动的多个接收端按同一电气网处理。多源需预制选择器，不能由金属实现。
- **夹具接点** 作为来源证据逐位映射到实际叶端口或父层单元。P 的 5,482 点诊断包括真实 FENCE 接点和内部切口/扇出别名。只有被实际服务引用且能证明接收、方向和连通归属的端点才进入正式清单。U/C/F/J 的独立下层通过范围随原包保留。U 有 770 个分属 656 条逻辑网的夹具切口。C/F 各有 34 条 G→E 分割网（32 位数据、valid、反向 take）。J 有 130 条 E→S 分割网（128 位数据、valid、反向 take）。这些实测切口进入接入复核，按实际 ITERM/原生网绑定。

逐位记录至少包含需求 ID、服务/程序关联、端点角色、实例路径、pin 名和位、ODB terminal、原生网、M10 导体矩形、规则及视图摘要。路径状态区分已有实证的 `fixed`、有真实断点的 `candidate`、尚需端点或能力的 `unsupported`、产品已物理实现的 `realized`。联合 ODB 导出前，宏局部 pin 表和端口名仅为候选设计输入。

MC–LC 夹具已盘点 2,613 条有向终端边，对应 1,631 条物理网。联合布局重新核对位映射及低/基准/高 RC。中继通过独立 `upper-repeaters/1` 输入，其位置由实际空闲行、障碍、PG 和原生接点复核。虚拟中继只用于探索，实体中继的 footprint、输入电容、输出负载和级联时序纳入组合验收。若插入实体中继需要改变冻结底座的下层几何或有源库存，按新版本验收。

## 联合布局和产品验证

1. 从九组库存生成父层实例清单和可放置区域，用两份同资源布局分别试排。先核对各宏原生端口与时钟、PG、尺寸、布线阻挡，再比较占地、空白、接入冲突和真实最差电气。所选方案需列出各局控、PM、适配、CTS、实体中继与填充的面积。
2. 用选定的候选 ODB 导出真实 pin 和固定网，试布至少两个产品需求。覆盖母控控制链、关键 512 位存储网、每类至少一条组内实际后制数据边。冻结共同底座前记录原生层指纹和可用中继资源。
3. [Algo1 #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 消费算子图、模型范围和硬件能力，以同一次映射生成指令镜像和静态逐位需求。借 [#227 合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/227) 绑定实际 ODB。用 [Algo2 #259](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/259) 完成 M11/M12 几何，实际回读、寄生提取和 STA 提供端点/负载/时序反馈。
4. 真实 64 B DMA 以原约束完成 DRC、连通、电气和 300 MHz setup/hold，并用实际 DDR 计数、有限 S、程序和整数参考验证产品。独立、联合和完整模型结果分别归档。吞吐与算法收益在相同硬件、权重、B1/ctx512、300 MHz 和外存预算下对照。
