# 通用 M10 接入与 M11/M12 布线基线

Issue #228，叠加 #227 的逐位接口合同。输入只有连接、端点几何和研究规则；
算法不读模型名称、算子语义或 P/U/C/F/J 名称。不把 Qwen3.5 路线写入代码。

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
它不是实际芯片、foundry DRC或300MHz资格。当前没有ODB/DEF/GDS写出器或RC提取。

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
