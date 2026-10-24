# 工作负载通信输入适配器 v1

Issue [#63](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/63)，入口 `project/analysis/workload_mapping/`。本机独立续接；不连接服务器。旧服务器版本未读取、未覆盖，聊天恢复文件尚未与服务器原件逐字节比较。

## 范围与算法

显式静态图、有限事件安排、资源分配和有向路径经过严格校验，转换成通信需求和声明存储占用。工具不自动搜索映射、调度或硬件划分。节点能力仅按declared/implemented/verified/unknown保存；声明通过不证明硬件功能实现。

先建立ID索引、检查生产者和全部消费者及状态lineage；逐事件验证本资源驻留和显式复制，再检查已声明路径、端口方向、协议、位宽和FIFO；按storage的闭区间生命周期统计保留容量，拒绝活值提前覆盖。alias是同存储字节范围的view，部分view副本不能充当完整父tensor。权重复用不增加唯一参数库存。

`workload-mapping/1`根字段：schema_version/id/evidence/scope/nodes/calls/tensors/storages/states/events/transfers/resource_input。每个对象字段闭合，详见core.parse及小型examples；拒绝重复JSON键、未知版本/字段、重复ID、缺引用、未解析shape、非法容器和单位。shape为正整数，axes/layout显式；i33须i64容器。未知metadata/capacity保持null和缺项，不能改成0。

`workload-blocks/1`列resources与links；资源是显式实例，不能用数量隐式复制连接。端口含direction/protocol/width_bits/fifo_bytes，链路必须引用实际端口。多连接共用端口及中转须显式route/mux能力，不赠送广播或转换器。

存储容量按声明分配计一次，与有效值产生/使用/释放区分；不是实测显存/HBM流量。逻辑事件序不是时钟周期。消息是运行时通信，布局连接复用资源端口和总线，不能每个tensor新增独立导线。

## 固定复用与证据

直接复用PR50 `b06d85a801a87c07f9745ccae6950dc7e4cbd0d2`的llm_resources，原字节不修改，也不复制第二套估算器。硬编码SHA与resource_source_lock.json绑定。通用端点双射映射到临时算术图后调用原compute，再逆映射；这是分包/多跳/shared TX算术，不是实际S资源或拓扑。v1可表达的原候选图子集另外导出resource_input.json；状态、事件序、alias/生命周期、实际实例/端口与物理资格列为不兼容。没有明确模型预算时输出null，不把内部算术壳当用户模型。

保留有效payload bit、容器字节、metadata、包头/对齐、消息数和逐跳wire成本。#41/#78 profile为128bit每拍16B，64B header，payload按64B对齐，最大1984B payload；对齐粒度不是接口每拍字节数。没有预算不输出B/s；理想链路拍数不当执行周期。64B/1984B/1985B载荷分别128B/2048B/2176B wire。

PR78固定head `a5ff0c5af973ffeafa441712cd3f6e491da5a2fd`作为依赖；v2文档来源固定 `88e9c4b2c3bb1b93b7155ba87ad11853e6c15512`。原fixtures、expected、sources和历史回执保持原字节。两图专用数学/状态验收入口继续复用，通用适配器通过独立转换桥接；不在core硬编码graph_id或答案。

## 本机基线与运行

Python标准库，所有输出使用本任务独立目录。下列最小链已实际运行通过：

```powershell
python -B scripts/check_project.py
python -B -m unittest discover -s project/analysis/block_v2_offline -v
python -B -m unittest discover -s project/analysis/llm_resources -v
python -B -m unittest discover -s project/analysis/workload_mapping -p test_core.py -v
python -B -m unittest discover -s project/analysis/workload_mapping -p test_resource_bridge.py -v
```

本轮分别32、31、42、23项通过。首轮test discovery的ImportError已修复，失败摘录和后续精选回执位于本任务.local/runs及work/huangpingyang04-lgtm/63。测试准备与实际执行分开，历史数量不能算本轮通过。

CLI为 `python -B -m project.analysis.workload_mapping validate|build|bind|verify|replay`；图输入通过--graph/--blocks，写入要求--root和全新--output-dir。--bundle用于verify/replay。输出覆盖、符号链接/路径越界被拒绝。verify重算输入/源码/依赖/输出SHA，重新build并由独立consumer核验图、驻留、生命周期、路径和字节；仅重算被篡改结果的hash不能通过。

科学JSON与runtime.json的时间戳/绝对路径分开。初步A逻辑链通过；完整v2接入及资产导入验证在后续同PR继续。C真实物理接入始终独立标注，不因A通过变pass。

## 资产与物理接入

参考PR18普通LEF解析器保留PIN/PORT/LAYER/RECT、PG/OBS、单位及局部坐标。ACT/MXU/GEMM分别按固定commit、run、master与原SHA绑定，不按同名master拼接新旧版本。多PORT不合并为免费贯通，矩形中心不是via接入点，图像不用于猜测坐标。真实协议、数值能力、时钟/复位、RTL/Liberty、位置/朝向没有证据时保持未知。

M1–M8固定，M9/M10及技术允许的M8↔M9、M9↔M10过孔定制；M11/M12单列后备。缺同版真实实例、固定M8引出、冻结底座与技术via证据时C=blocked；显式请求物理绑定非零退出并保存报告。M5/M6 pin不是M8接入。#55缺匹配读取入口时mapping_request是拟议合同，独立consumer不是实际布局布线联调。

未来先取得同版实际实例/端口、bit次序/协议、真实固定M8引出及冻结底座，再补物理绑定。服务器未来也须另获操作授权，先只读比较旧源码/输入SHA，在新目录整合运行，保护旧未提交版本。
