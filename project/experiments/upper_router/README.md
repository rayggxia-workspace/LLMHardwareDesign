# 通用 M10 接入与 M11/M12 布线

Issue #228，叠加 #227 的逐位接口合同。输入只有连接、端点几何和研究规则；
算法不读模型名称、算子语义或 P/U/C/F/J 名称。不把 Qwen3.5 路线写入代码。

## 算法

1. 从每个真实 M10 矩形枚举网格内接入候选，要求 via10 的 cut＋M10 包围完整落入
   导体，M11 落地金属及切孔满足已有障碍/占用。不是使用 pin 中心当任意接点。
2. 将全部合法起点和终点放进同一多源 A* 搜索。M11 水平、M12 垂直，via11 换层；
   移动时检查实际线宽、落地金属、切孔的矩形占用和间距。多接收端从现有树继续生长。
3. 一轮逐网布线，失败的临时树全部撤销。根据记录的阻塞网尝试局部重布，保留无关铜线；
   局部重布仍有失败时，回到全局重排。历史阻塞点增加搜索代价。
4. `check.py` 不导入搜索代码，从输出矩形/通孔重新检查网络覆盖、端点包围、障碍、
   金属/切孔间距、层方向及实际导体连通；移除via、漏pin、伪造完整率等负例拒绝。

单网 A* 代价为线长 DBU＋显式 via11 penalty＋非负历史拥塞价格，启发式为到最近
目标的 Manhattan 距离。它只在本次有限网格、当前障碍和给定接入候选下搜索；多网
重排及逐接收端生长不保证全局最优。没有给总线位序或模型边赋予额外合法性。

默认采用粗网格。配置 `access_pitch` 和 `access_radius` 后，在 M10 端点附近的窗口
内用同一套 M11/M12 层走短线和换层，细轨道间距由实际矩形、切孔和已有导体检查。
超出窗口后回到粗网格。线束提示影响出口容量排序，随后逐位搜索和占用。
当前约束包含优选方向及保守矩形间距。工艺 EOL、min-area 和 antenna 须交独立物理工具。
失败码只说明所声明网格、规则与搜索预算内的结果。

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

`geometry_complete` 表示全部需求通过声明的研究几何规则。
导出 `upper.def` 后可通过 OpenDB 和 KLayout 生成 GDS，核对真实 M10 覆盖和原生几何。
路由回执保留 `physical_qualified=false`，需单独取得组合电气及时序证据。

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
可从带源指纹的原生切口清单生成同一套 `route-contract/1` 文件。下列命令使用已有
接口目录和需求使用者，保留夹具范围及原生视图 SHA-256。

```powershell
python -B project/experiments/upper_router/native_inventory.py inventory catalog.json users.json output --manifest-sha256 <trusted-manifest-sha256> --role <fixture-role> --rules rules.json
```

输出为 `base.json`、`requirements.json` 和可选的 `router-input.json`。目录须包含原始
清单导出和哈希清单。适配器核对实际 ODB、DEF、GDS、网表和 SPEF 字节，以及选中
切口的方向、M10 所有权和提取连通。已有完整 M10 BTerm 两侧的切口可进入夹具几何
验证。独立叶块 ITerm 须先补充原生导通和落点证据。输出底座状态为 `candidate`，
夹具标签保留到路由上下文。

## 与新版 Algorithm 1 集成

```powershell
python -B project/experiments/upper_router/run.py handoff/algorithm2-input.json routes.json --handoff handoff --native-gds native.gds --emit-def overlay --via-resistance-ohm 0.08
```

`--handoff` 核对程序、连接需求、已绑定网表、静态位成员和底座指纹。
产品范围的 DEF 导出要求 `--frozen-base base.json` 和匹配的 `--native-gds`，由已核对的冻结视图重新绑定端点和固定网。
示例过孔电阻沿用研究场景，工程运行由当前工艺规则提供。用 `ingest.tcl` 导入研究 LEF 和 DEF，
再用 `physical_readback.py` 从 OpenDB 几何生成并回读 GDS。后端回执的范围是上层几何
和 M1–M10 原生图形一致性。下游需要按 `bindings.json` 将上层分段关联到实际网表做寄生和 STA。
默认 GDS 层号采用项目研究工艺，可在 `technology.gds_layer_map` 提供唯一的层号／datatype 对。

`--repeaters inventory.json` 接收独立的 `upper-repeaters/1` 清单，可带真实或虚拟实例。
实例提供 M10 两端、占地、供电声明、可选电气参数和物理视图散列。实际使用的中继按
静态网独占，支持多级和多接收端分支。几何与中继分配一起验证，使用虚拟中继的结果
会被物理导出拒绝。以 `--max-repeaters 0` 在同一清单上跑直连对照。

`--previous routes.json --measurements violations.json` 读取绑定旧路线散列的
`upper-route-feedback/1`。每条违规含分段、指标、实测、阈值及可选关联分段。
修复保留未受影响的路线，新的候选必须重新提取。回读、提取和 STA 的复跑由调用方触发。
运行范围、对抗用例和真实回执见 [验证记录](../../../work/YUZE-LU/228/fixed-base-validation.md)。

## 复跑

```powershell
python -B project/experiments/upper_router/run.py project/experiments/upper_router/examples/ripup.json routes.json --rounds 4
python -B project/experiments/upper_router/run.py project/experiments/upper_router/examples/ripup.json check.json --check routes.json
# 在upper_router目录执行
python -B -m unittest discover -v
```

一轮存在失败时退出码2，仍输出合法部分路线和诊断；输入错误抛异常，拒绝布线。
搜索预算是每网每轮节点上限，接入候选枚举与几何校验另计，不是总内存/运行时间上限。
本地测试包含 512 条数据线及一条独立返回线、随机命名、任意障碍和一驱多收。
30个小网格与独立Dijkstra最小代价对照；此对照不证明多网全局最优。
`examples/ripup.json`中先布a会封住b的接点；第二轮优先b，a换路径，两网通过。

传统详细布线已有pin access、track assignment及search/repair（见
[OpenROAD官方说明](https://openroad.readthedocs.io/en/latest/main/src/drt/README.html)）；
本交付是项目受限上层互联的可复查基线，不宣称这些基础方法本身是论文创新。
#194 的实体中继作为独立实验夹具。通用搜索从清单读取中继、端点和规则。
