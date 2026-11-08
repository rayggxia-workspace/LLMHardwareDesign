# 通用 M10 接入与 M11/M12 布线基线

Issue #228，叠加 #227 的逐位接口合同。输入只有连接、端点几何和研究规则；
算法不读模型名称、算子语义或 P/U/C/F/J 名称。不把 Qwen3.5 路线写入代码。

Issue #230 已新增[实际后端写出、读回与产品输入审计](BACKEND.md)：
通用路线可生成实际 DEF/ODB/GDS 互联视图，五类真实晚接接口用于物理回归。
资源库、几何与端点是工具输入；控制/PM及外存实现的系统资格独立记账，
不能用局部接口回归代替 #220 整网产品通过。原始 #228 合成几何证据与下文算法边界继续保留。

## 算法

1. 从每个真实 M10 矩形枚举网格内接入候选，要求 via10 的 cut＋M10 包围完整落入
   导体，M11 落地金属及切孔满足已有障碍/占用。不是使用 pin 中心当任意接点。
2. 将全部合法起点和终点放进同一多源 A* 搜索。M11 水平、M12 垂直，via11 换层；
   移动时检查实际线宽、落地金属、切孔的矩形占用和间距。多接收端从现有树继续生长。
3. 一轮逐网布线，失败的临时树全部撤销。下一轮拆除所有上轮路线，失败网络先布，
   其余按固定种子重排；历史阻塞点增加搜索代价。保存合法布通网数最多的结果。
4. `check.py` 不导入搜索代码，从输出矩形/通孔重新检查网络覆盖、端点包围、障碍、
   金属/切孔间距、层方向及实际导体连通；移除via、漏pin、伪造完整率等负例拒绝。

单网 A* 代价为线长 DBU＋显式 via11 penalty＋非负历史拥塞价格，启发式为到最近
目标的 Manhattan 距离。它只在本次有限网格、当前障碍和给定接入候选下搜索；多网
重排及逐接收端生长不保证全局最优。没有给总线位序或模型边赋予额外合法性。

第一版是**粗网格基线**：轨距需不小于 cut＋cut spacing，以及线宽＋spacing。
因此同网不同网格位置的切孔天然满足间距，点状态无需携带整条历史的通孔禁区。
不支持细轨距/大通孔阵列、多层非优选方向、离网局部stub或任意工艺规则。
没有网格落点时返回 `grid_access_not_found`，不能解释为真实物理上绝对无法接入。
矩形间距采用保守 L-infinity 规则，尚未实现foundry EOL/min-area/antenna等规则。

## 输入输出

独立输入 `schema_version:upper-router/1`、`units:dbu`，包含：

- `technology`：`bounds:[x0,y0,x1,y1]`、`origin:[x,y]`、整数`pitch/width/spacing`；
  via10/via11各有`cut/lower_enclosure/upper_enclosure/spacing`，width/cut须为正偶数DBU；
  可选`via_cost/history_weight`（非负搜索代价）。via10的lower指M10、upper指M11；
  via11的lower指M11、upper指M12。
- `pins`：实际端点ID到全局坐标M10矩形列表。原生M1–M10有效性由输入导出和底座资格保证；
  本工具不修改或重验原生金属，不以宏外框作为障碍替代真实上层保留区。
- `nets`：`{id,driver,sinks}`，已经完成逐位与协议展开；不允许一个pin归属不同电气网络。
- `obstacles`：可选`{layer,rect}`，层为M11/M12/V10/V11，包括上层固定线、PG/时钟预留等。
  不会从宏外框猜测这些障碍；未提供的障碍不会凭空推导。
- `context`：可选原生底座/需求版本；整个输入的语义SHA绑定结果。

结果 `routes[net]` 包含实际DBU `segments`、带pin归属的`via10`、`via11`，
`failed` 区分grid_access_not_found、search_not_found、search_budget_exhausted。
保存各轮顺序、节点展开数和布通数；几何检查独立重算线长与通孔数。

`geometry_complete` 仅表示全部需求通过**声明的研究几何规则**；
始终 `physical_qualified=false`，electrical/timing_status=not_evaluated。
它不是实际芯片、foundry DRC或300MHz资格。#230 的写出器和独立物理回归见上方链接；
当前没有完整九组产品耦合RC/STA闭环。

## 与 #227 集成

```powershell
python -B project/experiments/upper_router/run.py request.json routes.json --base base.json --technology rules.json
```

`rules.json` 为 `{technology:上述规则,obstacles:[]}`。base视图先做字节哈希核对；
请求须endpoint_binding_complete且无unresolved，版本须匹配base。根据实际odb_term
恢复pin几何，已有native固定sink不重复布线；其余驱动fanout作为同一电气网络。
附加的失败反馈绑定需求/base/规则输入指纹，全部为非硬剪枝观测。数据、ACK、预约、
控制均按传入逐位网表处理，不由路由器根据模型补猜。

未绑定需求在入口明确拒绝；这不妨碍使用标注清楚的合成几何开发/评估算法。
实际底座pin导出、长线负载与RC/STA验收保持独立。

## 复跑

```powershell
python -B project/experiments/upper_router/run.py project/experiments/upper_router/examples/ripup.json routes.json --rounds 4
python -B project/experiments/upper_router/run.py project/experiments/upper_router/examples/ripup.json check.json --check routes.json
# 在upper_router目录执行
python -B -m unittest test_router -v
```

一轮存在失败时退出码2，仍输出合法部分路线和诊断；输入错误抛异常，拒绝布线。
搜索预算是每网每轮节点上限，接入候选枚举与几何校验另计，不是总内存/运行时间上限。
所有示例和21项测试几何均为合成，包含128位、随机命名、任意障碍和一驱多收。
30个小网格与独立Dijkstra最小代价对照；此对照不证明多网全局最优。
`examples/ripup.json`中先布a会封住b的接点；第二轮优先b，a换路径，两网通过。

传统详细布线已有pin access、track assignment及search/repair（见
[OpenROAD官方说明](https://openroad.readthedocs.io/en/latest/main/src/drt/README.html)）；
本交付是项目受限上层互联的可复查基线，不宣称这些基础方法本身是论文创新。
#194的coupon实验用作历史失败背景，本目录没有继承其专用网名、常数或物理资格。

## 实际后端闭合

`flow.py`消费已校验的#220计划和资源库：实例模板按能力匹配，接口模板作为资源输入，
`place_search.py`按真实端点通信估价搜索放置，`search.py`同时搜索M10接入与M11/M12路线。
资源patch的包围框仅用于保持已有预连不互撞，不变成组合硬宏；导出的flat ODB保留独立叶宏和全部局控标准单元。

接口可分别声明逐位新连线、`native_service`或`external_boundary`。后两者引用同一实际资源ODB/网表/GDS与独立叶宏，
外部边界还保留真实原生层的pin形状；不能将M5等边界伪造为M10接点，也不要求EDA工具先实现外存gateway。
`resource_library.py --services`载入显式、inventory SHA绑定的资源合同，既有预连不重复产生上层布线。
`work/YUZE-LU/230/resource-services.json`是当前五类资源的附件声明，不构成#220完整算子数值或局控程序等价证明。
因此#220计划的服务绑定记录与690条真实待接通路的物理算法回归分别记录，不把两者冒称同一芯片功能验收。

实际后端由独立检查收口：

- `def_assembly.py`/`flat_backend.py`把原生DEF与真实上层路线组成平坦ODB/网表；
  `odb_lef.py`可从实际ODB导出master视图，避免误用随包的旧LEF。电气Liberty值不修改。
- `physical_equivalence.py`逐实例、逐网对照原生ODB和新ODB；全部信号/PG导体及pin union要求XOR为0。
  `physical_readback.py`另做实际上层ODB→GDS读回、规则、M10覆盖和原生层不变性检查。
  原生层不变性通过全部native cell-layer XOR及所有层级实例/变换相等证明，不抽样。
- `native_topology.py`提取完整原生连通性；`field_context.py`保留叶宏内部导体，将真实新路线加入共同场景。
  `field/native_field.cpp`基于#225场求解器接口，保留其区间合并修复，并按上层R节点分箱；
  `rc_graph.py`产生真实分支R图，`field_solve.py`/`refine_field.py`保存精度不足记录并只重算不足行。
  分片收集必须覆盖全部新网、场景/求解器/控制实验SHA一致；不能把五个单独电容值复制成九组共同电容。
- `stitch_rc.py`保留原生RC，加入新路由R和完整原生上下文中的上层origin电荷投影。
  `assembly_sta.py`只namespace原约束并移除已内化端口的I/O约束；原周期、负载、false path、Liberty限值保留。
  `timing_receipt.py`要求全部新网驱动寄生完整、无失配约束，且节点投影×Miller共9档setup/hold/cap/slew/fanout均无违规。
- `qualify.py`只有在平坦ODB、共同GDS、完整原版DRC、新网连通、共同场提取和9档STA全部绑定相同输入产物后，
  才给声明输入网表出具资格，并可复制DEF/ODB/Verilog/GDS/SPEF/SDC六文件交付。粗布线成功不会得到此资格。

M11/M12参数沿用项目研究栈：线宽/厚度2µm、介质间隔0.8µm、eps=3.9、Rs=.0102Ω/□；
via电阻.08Ω是显式研究假设，不是工厂标定。新增C使用共同原生导体场景，原生内部RC保留其已提取视图；
这仍是上层origin增量投影，Miller与节点敏感性不等于完整动态SI或PVT签核。
每个资源库/模型的映射、RTL和物理资格分别记账；资源库690网验收不自动证明任一完整模型/母控程序通过。
