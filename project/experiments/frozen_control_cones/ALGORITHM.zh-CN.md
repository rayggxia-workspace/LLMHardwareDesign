# 方法、输入和验证边界

本实现是已有方法的工程组合：同层矩形扫描线接触检测、并查集求连通分量、冻结约束比较、组合电路拓扑求值和有限输入穷举。没有声称提出新优化算法或找到了最优 Block。

## A：生成并冻结底座（当前案例人工适配）

1. 选择功能切点，确定两种表达式和可信原 RTL 来源。
2. 人工选择共享 INV/AND 单元，给定位置、方向、供电和 M1–M10 引出；所有引脚提前引到 M10 落点。
3. 保存单元、几何、原通孔、障碍和技术定义。冻结后不增加逻辑或移动单元。
4. 两种接线只在 M11/M12 上生成。M10→M11 接入通孔的 M10 围边必须完全落在已有 M10 导体内部。

上述 1–3 和显式 DEF 生成保留为案例专用、人工决定的部分。原始已运行脚本及 SHA 位于 evidence.json 的 server_artifacts。本 PR 没有重新实现自动布局、资源选择或 router；新增低层单元必须建立新底座版本并重新验证所有目标。

## B：冻结底座上的检查算法（已实现并用实际导出验证）

输入：
- 同一冻结基线的 native TSV + OpenROAD ODB 重新导出 DEF。
- 某案例同格式的实际导出。
- 层/通孔白名单、单元型号与组合真值表、端口顺序、期望结果、制造网格及预算配置。

输出：
- 每案例 PASS_SCOPED_REPLAY 或 REJECTED；
- 冻结约束、矩形单元重叠、穷举输出和有限几何检查；
- 明确失败码和细节。不能用这一状态代替原生 EDA 或完整物理签核。

```text
for each target:
    decode actual routes -> rectangles + via links + transformed terminals
    compare all instances/placements, fixed pin geometry, PG, obstacles, technology
    require every old lower-layer shape remains
    permit extra lower shape only if it is a via enclosure inside frozen landing metal
    require immutable via names/coordinates unchanged
    require all variable conductors/vias belong to allowed layer stack
    union same-layer physical contacts and real via metal endpoints globally
    reject different-net contacts, unresolved terminals, multiple drivers, floating inputs
    derive cell connections from component IDs, independently of signal net labels
    for each binary input vector in configured port order:
        topologically evaluate every configured combinational primitive
        reject cycles, unknown cells or resource budget overflow
    compare resulting truth table against case reference
    check rectangular cell non-overlap, manufacturing grid and scalar metal spacing
```

逻辑来自导体与真实通孔，信号网名只用于额外短路/间距检查，不用作功能接线依据。PG 网名与引脚归属必须保持；不能按信号网合并规则更改电源。

接触约定：同层有正面积或正长度共边才连接，角点接触不算功能连通；不同网的角点接触仍保守地视为短路。缺失 cut 或不被两金属包围的通孔拒绝。没有通孔时，即便两个不同层矩形重叠也不能连接。

冻结比较是保守的原矩形保留检查，允许接入 via 在旧导体内新增冗余围边；不等于比较整个 ODB 字节，也不支持任意重分割低层几何。PG、外部端口和单元不变仍单独比较。

停止/失败条件：第一个不满足的冻结、接口、几何或功能条件即报告该案例拒绝。案例间继续独立检查。多周期/有环/未知单元不猜测结果。输入预算默认为 12，上限 16；大输入应接入已验证 SAT 后端，不能把超限当通过。

接触图使用按层 x 扫描线与并查集；最坏情况下矩形接触和有限规则比较仍为 O(S²)，拓扑重复扫描求值最坏 O(2^I G²)。这是少量单元实验实现，不是大规模性能优化；资源不足应失败或转交专用后端。

## 可替换的 example.json

| 字段 | 意思及要求 |
| --- | --- |
| fixed_layers / custom_layers | 冻结层与允许定制层，不得相交；案例为原十层加新两层 |
| landing_layer / custom_vias | 固定落点层、允许新增通孔及其两个导电层；必须有实际 native via 几何 |
| manufacturing_grid_dbu | 原生整数 DBU 中的制造网格；本例 10 DBU = 5 nm |
| cells | 按 master 名配置输入、单输出、真值表和尺寸；表以输入顺序按二进制索引排列 |
| power_nets | 电源/地名称，只用于冻结电源几何，不能当可变信号 |
| input_ports / output_ports | 实际导出 terminal ID 与顺序；本版仅支持标量二值组合接口 |
| cases[].prefix / expected | 导出前缀与该端口顺序下的可信期望真值表；不由待测电路自己生成 |
| cases[].source | 原 RTL 切点、表达式和行号，作为溯源；程序不解释任意 RTL 全文 |
| maximum_exhaustive_inputs | 防止无界枚举的预算，1–16；本例只有两个输入 |

当前只有 R0 方向、矩形单元尺寸；其他方向要增加几何适配并验证。单元尺寸与真值表由本例 Nangate45 的 LEF/Liberty 得出，原实验 Yosys Liberty SAT 是模型正确性的案例证据；对新工艺/新单元须提供相应证据，不能随意填写表就声称实现通过。

算法不硬编码实例名、绝对位置、案例数量或端口名字；测试包含实例/端口改名、端口顺序改变与整套 native 坐标平移。实际配置仍是两门专用模型，不代表任意硬件模型都已验证。

## 物理/功能证据层次

1. 原生证据：读取原始技术和单元库、生成 ODB 并重新导出。原实验还做了原生 PG 检查和保存 ODB 的独立读回。
2. 几何逻辑证据：从全局接触图重建门连接，实际 Liberty 模型下对源表达式 SAT；几何网表再与读回 ODB 网表 SAT。两个案例均四种二值输入穷举。
3. 本 PR 程序证据：校验已归档材料哈希，再用参数化程序对实际导出重放；原生故障样本与人为变异必须被拒绝。
4. 未证明：完整 RTL 时序/握手、FIFO 状态、X/Z、延迟、电气负载、完整 DRC/LVS、RC/STA、IR/EM、制造可行性。

本程序的 scalar spacing 与 grid 结果，只是有限几何规则结果。原生 cut/OBS/track/PG 的更宽子集检查仍以原证据为准，不能宣称本程序已经重新执行。M11/M12 和通孔是派生研究参数，而非 foundry 新层。

## 下一轮最小扩展

先评审本方法与证据；再选一个包含寄存器/握手的小功能，明确状态初始化、时钟/复位、周期对照与单元资源。新增资源必须生成新底座候选，两案例始终使用同一候选，旧成功和失败归档保留。

正式 Block 接入还需原语/数值语义、容量/端口/延迟/协议、尺寸/方向/引脚几何/可接入层/OBS、资源数与允许调整范围，以及真实新增层/via/RC/DRC。完整 LLM 还需算子、张量和执行依赖前端，本次不开发完整编译器。
