# 综合到布线接口 v1

Issue #226，叠加 PR #220 `f23a6d934`。合同版本 `route-contract/1`。

## 工作流与边界

`full_plan.py` 对 plan 做独立资源/调度检查之后，自动输出同名前缀的
`*-route-requirements.json`，包括九组等预算对照。不改变 DP、缓存或数值原语。
可用 `--route-catalog catalog.json --route-base base.json` 绑定接口与底座。
未给目录时完整保留逻辑需求和使用者，状态为 unbound，不猜位宽或 pin。
固定但未被任务引用的逻辑网络也进入需求闭包。

不需先实现完整 MC/LC 二进制。物理接口未就绪的需求可以继续用于算法探索，
但不得冒充实际端点。五类分组使用同一目录格式，不引入组合硬 Block 边界。

本版实现需求提取、协议展开、清单绑定和分级反馈。**不是路由器**：不运行
M10 via access、几何 DRC、ODB/GDS 连通、RC 或 STA；所有输出
`physical_qualified=false`。`endpoint_binding_complete` 仅表示目录声明完整。
重构检查器共享展开实现，不声称是独立物理验证器；原 schedule checker 仍独立于搜索。

## 三份工件

所有 JSON 使用 UTF-8；哈希为排序键/紧凑 JSON 的 SHA-256（canonical semantic hash），
不是输入文件原始字节哈希。base.views 中的 sha256 才是实际文件字节哈希。

### base.json

必需 `schema_version/base_id/state`；state 为 candidate 或 frozen，仅记录调用方
冻结声明，不授予资格。`views` 为 ODB/netlist/GDS/SPEF/SDC/LEF/Liberty/规则等
实际文件 `{path,sha256}` 索引，路径相对 base.json。CLI 与 full_plan 对提供的每份
视图流式检查字节哈希；不解析其物理内容。

`endpoints` 以语义端点名为键。每项含 `odb_term`（最终实例/terminal 稳定标识）、
`native_net`（全局唯一原生电气连通分量）、`role:driver|sink`、
`m10_shapes:[{layer:"M10",object:"数据库对象索引",rect_dbu:[x0,y0,x1,y1]}]`。
有绑定时必须给 `dbu_per_micron` 和三份 ODB/netlist/GDS 视图。
导出者须正确处理实例坐标变换及综合改名；这里不复制完整几何数据库。

`fixed_native_nets` 为 `{全局分量:{driver:实际odb_term}}`，包括当前产品没调用的
固定驱动，避免新网络把其短接。导出者必须完整枚举相关已有驱动，不能把缺项当作
浮空许可。独立验证夹具的 BTerm 不能自动当共同底座实例端点。
规则、RC 模型、电气限值、时序约束及资格报告作为 base 的版本化元数据/视图存入；
其变化进入整体 base 哈希，使旧反馈失效。当前校验器不执行这些电气限值。

### catalog.json 与 route-requirements.json

接口目录 `{schema_version,demands:{逻辑束:{requires:[],signals:[]}}}`。
每 signal 为 `{name,width,driver,sinks}`，driver/sinks 是端点键格式串，
多位接口必须使用 `{bit}`。不允许把两个不同位广播绑定到同一模板端点。
`requires` 做闭包展开；未知模板/依赖保留在 unresolved，而不是丢掉。

示例模板（这只是语义角色，尚未假定物理 pin）：

```json
{"name":"data","width":128,"driver":"U0.outgoing_data[{bit}]",
 "sinks":["U1.incoming_data[{bit}]"]}
```

从 `(task_id,binding_id)` 恢复每束的全部使用者。缓存命中和历史任务完成不会删除
静态连接。`members` 逐位保留语义端点；`nets` 按实际 driver 合并 fanout，禁止
不同驱动接入同一原生连通分量。已有 driver/sink 同分量的 sink 标为 fixed_sinks，
其他 sink 等待上层布线；不把整束 fixed 标记当成实际导线证明。

源 IR/plan、目录、整个 base 都有指纹。未知目录即便 plan 已合法也保持 unbound。
`--require-bound` 仍写出诊断需求，然后退出码 2；绑定完整退出 0，仍不授予物理资格。

### routing-feedback.json

`route_feedback.py request.json observations.json output.json` 封装观测。
每项需 `phase/category/code`、`member_ids` 或 `net_ids`、`evidence`（报告路径或
带 SHA 的证据对象）；可附 observed/limit、RC/corner 和约束范围。
phase 为 binding/access/routing/geometry/electrical/timing；category 分为
search_not_found/geometry_failed/electrical_failed/timing_failed/contract_invalid。
不接受未知目标、陈旧需求/base 或伪造摘要。

v1 **不自动学习硬约束**，拒绝 hard_constraint=true。一次 escape/trunk 搜索失败
不证明不可行，几何/时序失败仅拒绝该候选。后续若引入割容量或 RC 下界证明，
必须新增证明检查器；容量2上三束的限制不能擅自变成任意两束互斥。
反馈也不直接改 DP 代价/时钟周期，调用方按范围决定重试或重映射。

## 真实协议样例与复跑

固定 #221 `17ba807d` 的 U stored_link ABI，从 #220 真实 connections.json 读取
142位/向的传输字段，另补每向11位接收预约身份，双向合计306位。
MC/LC分发控制作为未展开依赖；四束 E.read/write 仍缺模板。因此输出不是可部署网表。
此专用适配器验证字段宽度、方向及ACK完整性，不推广到其它宏的接口。

```powershell
python -B project/experiments/block_synthesis/route_contract.py --u-connections work/YUZE-LU/219/results/mutex-control-v2/current-control/generated/connections.json --output work/YUZE-LU/226/two-u-route-requirements.json
python -B project/experiments/block_synthesis/route_contract.py --ir generated/five-groups-ir.json --plan generated/five-groups-plan.json --catalog catalog.json --base base.json --output generated/five-groups-route-requirements.json --require-bound
```

从本目录运行 `python -B -m unittest test_route_contract test_loop_dp -v`。
测试中的物理目录是明确标注的合成夹具，不是实际布局证据。
实际底座导出、via候选、完整路由及物理验收仍由后续后端完成。
