# Block v1 宏边界独立核验（#127）

本目录服务 [Issue #127](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/127)，独立消费 #121 / PR #122 导出的文件，不导入、不修改主线 exporter/receiver。Python 部分只需要 Python 3.10+ 标准库；原生测量另需指定 OpenSTA/OpenROAD。第二批已实现原生 STA 对照、实际 SPEF 图清单、精确矩形并集 OBS 检查和最终功能证明的来源绑定。真实候选与控制实验的实际结果见 `work/YUZE-LU/127/`；仍不签发正式宏边界资格。

`passed: true` 只表示本次已执行的来源/接口/可选数值合同检查通过。缺少对照时 `comparison.status` 明确为 pending；无论 synthetic/native、是否包含对照，`flat_abstract_boundary_qualified` 与 `qualified_hard_macro` 都固定为 false。本工具不会签发物理、功能、十二层或冻结资格。

## 1. 本批核验范围

| 范围 | 已实现 | 尚不能证明 |
| --- | --- | --- |
| 来源 | source/physical/view/prepare 四份收据的成功状态、提交与工具哈希；产物原始路径及 producer 输出哈希；完整 final ODB/V/SDC/SPEF/DEF、GDS、Lib/LEF 和读回文件的关联；exporter 输入中的 budget/pipeline/脚本哈希；拒绝额外失败的物理门禁 | 收据作者的真实性、流水线执行完整性、物理报告本身的科学正确性；收据不是数字签名 |
| 接口 | 全部信号身份/方向、精确 scoped Liberty 查询结果、typed bus 成员/方向、M10 pin 矩形、完整 footprint、PG 类型/方向及 source PG 几何 | 重新运行 EDA 工具后的独立原生读回；当前消费既有读回 TSV |
| OBS | 原生 M1–M10 必须都有 OBS；禁止 M11/M12 或越界/空矩形；报告层清单 | 图形是否完整、保守地覆盖底层几何；少量小矩形也可能通过清单检查，所以 coverage 永不置真 |
| 时序/电气 | 同源 SDC 与收据、同预算 clock/transition/uncertainty/IO/driver/load、指定测量集合、固定单位、有限数值、逐项绝对误差 | 指定集合是否覆盖所有真实端点/弧/transition/corner；measurement 是否来自实际 STA；比较相等不等于 setup/hold 本身达标 |
| 边界寄生 | 明确 input wire resistance；逐组件/segment 清单相同；每段恰有 macro 或 parent 一个 owner；R/C 数值及单位比较 | segment 与 SPEF/提取器的物理对应关系、原生提取完整性、耦合模型和输入线阻对延迟的实际作用 |

不同 producer/receiver/exporter 阶段可以来自不同源码提交。核验的是明确的依赖、路径与摘要，不能用“所有 commit 必须相等”拒绝合法的独立接收。

Nangate45 当前合同固定使用 2000 DBU/µm：块内 M1–M10/via1–9，信号接点在 M10；定制互联 M11/M12/via10–11 属于后续父底座工作，不在本接收器内推导。先完成叶块交付，不扩展阵列数量或预连拓扑。

## 2. 先运行控制用例

在仓库根目录执行：

```powershell
python -B -m unittest discover -s project/experiments/block_v1/macro_boundary_qa -v
python -B scripts/check_project.py
```

测试全部使用临时目录内明确标记的 synthetic 数据。反例覆盖改文件、只改 index 哈希、混收据/源路径、budget 与 exporter 不一致、缺失及新失败门禁、重复 JSON key、NaN/Inf、接口/PG/OBS/总线错误、缺端点、不同环境/单位、事后改 spec、微小超差、输入线阻缺失、寄生漏计/双计、不同 segment 和数值错误。合成正例通过仍不具有真实物理资格。

## 3. 主线交接原生产物后打包

`pack_native.py` 在原生产物所在 Linux 环境执行；从 view report 获取 source/physical 原始目录，不修改这些目录。输出必须是新的、位于所有输入目录之外的目录；失败保留部分输出。CLI 不启动 EDA 或调度任何作业，执行所占 I/O/节点仍由主线统一安排。

```bash
python3 -B project/experiments/block_v1/macro_boundary_qa/pack_native.py \
  --views /scratch/RUN/tasks/native-views-shared109-a \
  --prepare /scratch/PREP/tasks/native-prepare \
  --budget /scratch/SOURCE/project/experiments/block_v1/physical-budget.json \
  --pipeline /scratch/SOURCE/project/experiments/block_v1/native_pipeline_const_protected.json \
  --output /scratch/qa127/bundle-c8-a > /scratch/qa127/c8-a-pack-report.json
```

这些路径是用法示例，不能当作已经存在或合格的运行证据。必须使用对应 view receipt 中实际使用的 budget/pipeline 文件。源文件在复制前后及整个核验后重算 SHA256；ODB/SPEF/GDS 按块流式哈希，避免把大文件全部装入内存。

bundle 可复制到本地，只要保持 index 的相对路径和原始 `origin`。复验：

```powershell
python -B project/experiments/block_v1/macro_boundary_qa/audit.py D:/qa127/bundle-c8-a/index.json
```

成功返回 0，合同失败返回 1 并输出 JSON；输出默认发往 stdout，避免覆盖输入证据。

`index.json` 采用 `block-v1-macro-qa-bundle/1`，字段：

```json
{
  "schema": "block-v1-macro-qa-bundle/1",
  "evidence_kind": "native",
  "top": "shared109",
  "policy": "A",
  "files": {
    "source_receipt": {
      "path": "source_receipt",
      "origin": "/scratch/SOURCE/tasks/native-run-shared109-a/receipt.json",
      "sha256": "用真实文件的64位小写SHA256替换"
    }
  }
}
```

上面的 files 仅展示单条结构，完整必需角色由 `pack_native.native_paths()` 定义：四份收据、physical/view report、pins、budget、pipeline、五份 final 文件、GDS、Lib/LEF、LEF/Lib/bus/source-PG TSV。原始 `origin` 必须保持 POSIX 绝对规范路径；本地 `path` 必须位于 bundle 内。拒绝重复路径、重复原始身份、目录穿越和哈希错配。

当前 receipt schema 仍由主线维护；若 schema/字段改变导致拒收，应保留失败，审查适配，不能删除核验项以制造通过。继承的 native physical 门禁仅为前置要求，不是支线重跑物理验收。

## 4. 对照格式：先约定，再测量

完整最小合成例见 `test_audit.py::comparison_fixture()`。真实接收前，主线与支线需审查并提交不可变的 spec，写明测量身份、全部适用 endpoints/arcs、rise/fall/min/max/corner 覆盖及每项容差依据。**首批工具不提供真实候选的默认合格容差**；测试中的容差仅验证接收器逻辑。

可在 bundle 增加三个角色：`comparison_spec`、`flat_measurements`、`abstract_measurements`，每项仍带 path/origin/sha256。只提供其中一部分会拒收。

spec schema 是 `block-v1-boundary-comparison-spec/1`：

- `context`：同源 `source_receipt_sha256`、`final_sdc_sha256`，非空 `corner`，以及 budget 中的 `clock_ns`、`clock_transition_ns`、`uncertainty_ns`、四项 input/output min/max delay、`input_driver`（cell/pin）和 `output_load_pf`。
- `measurements`：唯一且非空的测量 ID 列表。ID 应包含足够的 startpoint/endpoint/arc/transition/scenario 信息；接收器只核验 exact set，尚不能自己推导其覆盖完整性。
- `units`、`absolute_tolerance`：精确覆盖 `setup_slack_ns`、`hold_slack_ns`、`max_delay_ns`、`min_delay_ns`、`cap_pf`、`slew_ns`；单位分别为 ns、ns、ns、ns、pF、ns。容差是有限非负数，直接比较，不把微小失败四舍五入为零。
- `parasitic_components`：按稳定物理身份命名的对象，每项包含 `kind`、`unit`、`absolute_tolerance`。kind 支持 input_wire_resistance、wire_resistance、ground_capacitance、coupling_capacitance；R 单位 ohm、C 单位 pF，必须有 input_wire_resistance。

两份 measurement schema 为 `block-v1-boundary-measurements/1`：

- `view` 分别是 flat/abstract；`spec_sha256` 绑定原始 spec 文件字节；`context` 必须完全相同。
- `measurements` 对每个 spec ID 给出上述六个数值，不允许缺项、额外项或 NaN/Inf。
- `parasitics` 与 spec 组件 exact set 对应。每项有非负 `value`、唯一非空 `segments` 列表，以及 `owners`：每个 segment 映射到只有一个元素的列表 `["macro"]` 或 `["parent"]`。允许抽象前后改变所有权，但不能漏段、双计或替换物理 segment。

匹配 spec hash 只能发现报表与 spec 不一致，**不能证明 spec 在运行前发布**；发布时间需通过已审查 commit/运行收据的外部证据保证。三份对照文件当前只受 bundle index 约束，没有原生 STA producer 的收据绑定，因此数值比较通过仍是诊断结果。下一批需补原生测量适配与日志/命令/工具/输入哈希的绑定，不能直接将此 JSON 包装成正式资格。

## 5. 下一批正式接收的入口

主线发布 C8/T6K、A/C 的明确候选身份及同源 artifact 目录/收据，在同一来源完成完整物理/功能接收，并提供 final 原生 DRC 的证据。支线先运行本接收器，逐个候选保留成功/失败。

然后共同冻结场景与容差，在同一个环境运行 flat 和 macro-wrapper 原生 STA，独立提取完整端点/弧/电气测量与边界寄生归属，验证输入线阻没有消失。若现有 Liberty 抽象无法表达同等效应，应报告失败并反馈主线；不私自改导出器，也不以 scalar setup/hold 或 readback 成功替代对照。

本节是首批完整资格的验收要求。第二批增加的原生诊断如下；诊断覆盖仍不等于上面的全部资格要求。#127 保持开放，主线控制综合/P&R、物理修复、功能接收、正式资格、冻结与全任务节点预算。

## 6. 第二批原生对照与源码绑定

`native_control.py` 使用一个真实 DFF、显式分布 SPEF，先提取 timing model，再在两个输入电阻和两个驱动条件下用独立进程比较。`--export-drive matched-transition` 另在新进程捕获原驱动下的端口 slew，生成固定 transition 的诊断导出场景；它不修改主线导出器。每个电阻场景另做 exact-flat-reread 正控制，不能把该控制称为抽象等价通过。

```bash
python3 -B project/experiments/block_v1/macro_boundary_qa/native_control.py \
  --executable /approved/tools/sta --library /approved/libs/NangateOpenCellLibrary_typical.lib \
  --output /approved/qa127/NEW-control --parallel 2 --export-drive matched-transition
```

`native_pair.py` 的两个进程读入同一封存 SDC，每进程一线程，`--parallel 1|2` 控制同时进程数。记录命令、输入/工具/采集脚本哈希、日志、原始 TSV、SDC 读回和寄生 annotation 报告。`native_pair.verify(folder, request)` 根据绑定的原始 TSV 与实际 SPEF 重算；不信任保存的结果 JSON 自报成功。

覆盖：完整原生端点身份及四项 slack 清单；每个非 clk 输入和每个输出的 rise/fall × max/min 最差路径聚合；端口四项 slew；clock 与电气限制/违例统计。端点名在宏折叠后不同，因此分别保存两侧清单，不做虚假的同名匹配。**这不是所有 pin-to-pin 弧、例外、corner 或电气约束等价证明。** 端点表与 slew 目前通过原生 `get_property` 输出，有六位小数格式化；边界 slack/arrival/required 通过 PathEnd 数值接口获取，不使用该字符串格式化。`NO_PATH`、缺覆盖和非有限边界值拒收；非有限端点值另行明确标记。

`spef_inventory.py` 直接解析 explicit distributed SPEF，换算单位，保存实际 R/C ID、节点和源行号，检查全部输入端口的电阻图、sink 与悬空部分。大候选只保留输入边界网络的详细记录，其余网络仍逐条解析、计数并检查重复名，避免一次保留数百万 Python 对象。R 求和只是清单值，不是等效电阻；耦合记录也不声称跨网络去重或等效延迟。

真实候选先执行来源审计，再生成诊断请求：

```bash
python3 -B project/experiments/block_v1/macro_boundary_qa/candidate_request.py \
  /approved/bundle/index.json /approved/libs/NangateOpenCellLibrary_typical.lib /approved/NEW-request
python3 -B project/experiments/block_v1/macro_boundary_qa/native_pair.py \
  /approved/NEW-request/request.json --output /approved/NEW-measurement \
  --executable /approved/tools/sta --parallel 1
```

生成器仅支持 write_verilog 的简单非 ANSI 声明，逐位检查源网表、pins 与 Liberty 的**有序**总线映射。两侧共享的诊断 SDC 只把一条 `current_design <原顶层>` 换成无参查询，使不同 parent 顶层名能读入完全相同的其余时序命令；保留原 SDC 哈希和变换声明。若 timing model 有普通 VDD/VSS 输入，诊断 parent 明确接常量，并报告其表示缺口；这不撤销 `audit.py` 的 PG 接口失败，也不修复候选 Lib。

默认 1 ps 仅用于本批问题定位，预先写入请求；不是经审查的项目合格容差，不因测量失败而放宽。原生工具打印 Warning/Error 即使 exit=0 也必须检查，尤其 SPEF instance/net not found：有数值输出不能证明完整 annotation。

## 7. OBS 精确覆盖诊断

`native_occupancy.py` 用指定 OpenROAD 只读 final ODB，`source_occupancy.tcl` 使用固定哈希的项目 `odb_geometry.tcl` 导出几何，再附加每个 instance 变换后的 master OBS 及真实 NET→PORT 归属。这里复用几何生产器，**不复用主线验收器**。

`obstruction_coverage.py` 对每个源金属矩形做整数坐标的矩形并集覆盖检查；仅同 net、同层实际端口窗口可豁免。面积相等、矩形相交或层清单齐全都不能代替覆盖。via cut 只计数，由相邻金属 keepout 提供正常 route/via 限制；隐藏 transistor/GDS 几何与原生 DRC 不在该诊断的资格范围内。必须实际运行 ODB 导出并保存收据后，才能报告候选覆盖结果。

## 8. 原生模型弧清点与验收建议

`native_lib_inventory.py INDEX NEW_OUTPUT --executable /approved/tools/sta` 在新进程只读候选模型，枚举原生 scalar pin 方向/is_power_ground、所有 timing arc group、条件与 transition arc。`verify(index, folder, executable)` 根据绑定的原始 TSV 重新解析，检查模型/工具/采集代码与来源收据。实际 T6K A/C 各有 606 组、1,250 条 transition arc；供电普通输入无弧，不代表 PG 合同自动通过。

两个原生无 from-port 的 clock-tree 特殊组完整保留。当前接口不能安全给出其 role 名称，明确标 unresolved、native_role_metadata_complete=false；不跳过，也不调用会解引用空指针的原生 full_name。模型弧清单不是 flat 对应关系或数值安全性证明。

`native_pair.signed_slack_diagnostic(flat, abstract, threshold_ns)` 区分 abstract-minus-flat 的正向（乐观）和负向（悲观）slack 差，仍不签发资格。待审查的建议见 `work/YUZE-LU/127/宏边界验收口径建议.md`：声明有限工作域，审查安全包络及误差方向，不将全数值相等当作唯一合同，也不把全部组合图/预连研究提前放入本轮。
