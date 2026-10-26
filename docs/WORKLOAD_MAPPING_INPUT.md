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

科学JSON与runtime.json的时间戳/绝对路径分开。初步A逻辑链通过；完整v2接入及资产导入见下述本轮结果。C真实物理接入始终独立标注，不因A通过变pass。

## 资产与物理接入

参考PR18普通LEF解析器保留PIN/PORT/LAYER/RECT、PG/OBS、单位及局部坐标。ACT/MXU/GEMM分别按固定commit、run、master与原SHA绑定，不按同名master拼接新旧版本。多PORT不合并为免费贯通，矩形中心不是via接入点，图像不用于猜测坐标。真实协议、数值能力、时钟/复位、RTL/Liberty、位置/朝向没有证据时保持未知。

M1–M8固定，M9/M10及技术允许的M8↔M9、M9↔M10过孔定制；M11/M12单列后备。缺同版真实实例、固定M8引出、冻结底座与技术via证据时C=blocked；显式请求物理绑定非零退出并保存报告。M5/M6 pin不是M8接入。#55缺匹配读取入口时mapping_request是拟议合同，独立consumer不是实际布局布线联调。

未来先取得同版实际实例/端口、bit次序/协议、真实固定M8引出及冻结底座，再补物理绑定。服务器未来也须另获操作授权，先只读比较旧源码/输入SHA，在新目录整合运行，保护旧未提交版本。


## 字段、单位和支持范围

输入ID在图内跨类别唯一，端口ID在所属资源内唯一。tensor字段为id/shape/axes/layout/logical_bits/storage_bits/metadata_bytes/storage/offset_bytes/producer/consumers/role/initial/alias_of；storage为id/resource/size_bytes/begin/end；call为id/node/resource/reads/writes；transfer为id/tensor/source_storage/destination_storage/path/messages。路径填link ID，存储与消息量用byte，payload另外保留bit。显式copy沿用声明的tensor offset，源与目的有不同offset需求时分别划分storage槽；首版不搜索或自动重排地址。

图状态为id/kind/initial/versions，kind区分kv/convolution_history/recurrent；每版本含tensor/writer/previous。事件为id/kind/ref/step/phase，数组即有限有序安排，step非递减、phase为prefill/decode/iteration。节点为id/semantic/contract。资源为id/kind/capacity_bytes/capabilities/ports；capability为semantic/status/source；port为id/direction/protocol/width_bits/fifo_bytes；link为id/source/source_port/destination/destination_port/protocol。缺能力或路径直接拒绝，未知属性按scope列缺项。

`--semantics`接收独立的`workload-semantics/1`，保持旧#48 schema不变：

| 字段 | 内容与检查 |
| --- | --- |
| source | commit/kind/files(path,sha256)，区别文档来源与实际运行源 |
| tensor_formats | 每tensor的unit/signedness/stage/group/owner/epoch/version；stage区分VALUE/PARTIAL/COMPLETE/PROPOSAL/SHADOW/COMMITTED/SNAPSHOT |
| reductions | call/partials/expected_groups/complete/rq_call/rq_output/target_unit；组覆盖唯一、shape/unit一致、COMPLETE先于一次RQ；混合unit须另有ALIGN_REDUCE实现，当前明确拒绝 |
| transactions | id/state/owner/unit/epoch/expected_version/version/previous/proposal/shadow/published及四stage call、outcome/attempt/step/guard/guard_pass/private |
| memory_domains | 每resource独立private_ram/shared_bank/rom/fifo/external/host容量；storage_domains逐槽分型，ROM禁止运行时写，FIFO不能充RAM |
| dependencies | before/after事件及send_complete/consume/release/state/guard/commit原因，重新校验顺序 |
| bank_ports/bank_accesses（可选） | 1RW/位宽和resource/event/storage/op/slot；slot为唯一连续串行访问索引，绝非周期 |

事务只在全量guard之后通过私有shadow原子发布，commit才推进公开version；abort的published=null且公开版本不变，后继读取旧有效状态，重试重新计费。当前侧车校验声明协议；实际数值guard由明确的上游验收器验证，不声称执行任意算子的数值计算。支持固定epoch的连续版本，未实现任意rescale/epoch更新或通用宽算术。unknown unit在需要数值合同的级别返回结构化blocked，不能默认为0。

布局导出将消息挂到已有logical_channels，显式实例/端口和连接列表供下游消费。真实master/尺寸/坐标/朝向保持null，physical_qualified=false；value_lifetimes另列产生、使用和静态保留释放事件。消费端从导出的完整logical_graph、block_specification及侧车重新检查引用/驻留/覆盖/状态/容量/位宽/路径/字节/来源摘要，不读取producer的pass作为结论。

退出码：0表示请求范围通过；2表示输入或合同非法；3表示请求范围缺必要资料（含显式物理请求和未知必需单位）；4表示独立verify/replay失败。build默认验证已知逻辑必要条件，`--require-complete`还要求列出消息和语义检查的必要信息齐全。物理未请求为not_executed，显式请求而缺资料为blocked且非零。

## PR78两图接入和实际成本

`v2_bridge.accept_fixed`先核固定input/expected和原replay.py SHA，调用原replay与独立expected比较，再转换图；convert不读取expected答案。core/semantics没有两个graph_id或预期数字。数值变体由原窄合同控制，不能冒称一般LLM执行。

| 场景 | runtime消息 / wire byte / 理想16B拍 | 静态保留域 |
| --- | --- | --- |
| 两组PARTIAL32→COMPLETE→一次RQ→残差 | 2 / 256 / 16 | M RAM52、V RAM64、FIFO256，总372B |
| 三步状态正常提交 | 6 / 768 / 48 | R RAM52、S bank44、FIFO512，总608B |
| t2 shadow之后失败，再重试 | 7 / 896 / 56 | 同一608B保留；失败trial不产生state版本 |

初始x/W/残差、初态copy和输入预置不混入runtime；setup账保留在上游actual和科学摘要。图1导出独立8参数、4×2一次矩阵的synthetic #48 envelope，weights placement=unknown，因为v1无法表达M私有驻留；两个M调用复用一个实例和权重。图2 ACT16和事务语义不伪装成旧主矩阵合同，resource_input=null并列不兼容。原估算器CLI已实际读取图1导出并与API逐值对照。

其他7个通用输入覆盖最小跨资源图、权重重复读取/多消费者、alias/copy、scale独立数据、i33/i64、1984/1985分包边界、多跳和共享TX、三步卷积历史/递推状态、Qwen3-0.6B所选层prefill2+decode1与tiny变体、两种合成配置替换。Qwen来源沿用PR50配置：H1024/I3072/Q16/KV8/head_dim128，Q输出2048、K/V1024、O输入2048；这是配置推导而非真实trace，不验证数值质量。硬件容量/连接明确synthetic，不称#41库存完整可行。

## 真实离线资产实际覆盖

PR18固定`19c4b829211678d1a6fefa61bc0a23e68e4f13e1`：ACT20 860、MXU20 2172、GEMM20 3753个信号pin，连PG共6791 pin；保留geometry、单位2000 DBU/um、PORT层次和OBS。原parser SHA `d41e815de3c4ccc72eb23b69a70c9265aecbf2d313a085035645ed2b400c612c`，未另写LEF解析器。真实catalog必须重读固定原LEF并重解析全结构，自改catalog/hash不能冒充来源。

PR20固定`cce235975b7be6d77247c9c9c7b09ea15608e2cf`的1585317B原ZIP本轮通过本人Git HTTPS实际取得；选定3032位按原Yosys顺序、CSV与同版LEF的名字/方向/位号/几何行独立对照通过。它没有转成新#55资产，也没有重跑原完整三视图pipeline。协议/Liberty timing/完整RTL/时钟域资格未验证；GEMM只有已取得LEF，不伪称其RTL逻辑顺序已验。

[selected summary](../project/analysis/workload_mapping/assets/real_import_summary.json)分开记录真实导入、一个实际ACT clk端口引用、未知协议与物理blocked。其余多位次序/方向/协议负例由明确synthetic夹具测试，不能代签真实宏协议。

## 完整离线验证与独立复跑

在已具备固定原始资产的本任务目录，完整命令如下。输出目录必须全新；`formal-new`每次换新名字。

```powershell
python -B -m project.analysis.workload_mapping.validate_delivery --output-dir .local/runs/formal-new --reference-root .local/dependencies/reference_assets
```

该命令运行管理检查、原32小图测试、原31估算器回归、全部适配器测试、两个原始replay；10个选定场景build后冻结源码/依赖/输入，复制到独立源码目录，在新进程/新cwd重放并逐字节比较4个科学JSON。真实资产导入/3032位对照和bind/verify/replay也独立重放；显式physical请求必须退出3。源码必须先提交且干净，--allow-dirty仅用于开发预检，不是冻结验收。raw stdout/stderr保留.local，精选receipt/science索引在work/huangpingyang04-lgtm/63。

新clone可先显式获取两个固定commit对象，再运行`assets/acquire_reference_assets.py --allow-git-object-fetch --output-dir .local/dependencies/reference_assets`；该命令仅为GitHub固定资产取得，必须单独授权其显式Git对象获取。转换/测试/replay没有调用它，不会自动联网或追踪浮动版本。原ZIP和全LEF仅.local保存，仓库不上传>1MiB原始归档。CI将获取与科学运行分为独立步骤，科学阶段设置GIT_NO_LAZY_FETCH=1。

当前独立消费端仍是拟议#55接口验证，未实际布局布线、未证明死锁/时序/RC/DRC或物理收益。新协议/新算子语义可能需要新适配实现；两种synthetic配置替换只证明本版合同配置机制。

## 2026-10-25 正式本机复跑回执

干净执行源 `aa6f096695af45e9898090ce4f8006b8c9265029`，实际195项测试（32原小图、31原估算器、132适配器），0跳过；10个场景在独立源码副本/新进程/新cwd中重放，四个科学JSON逐字节及SHA一致。原fixture/expected/来源快照前后不变。真实导入/3032bit audit与bind/verify/replay独立重放一致，显式physical请求退出3。科学摘要SHA `f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc`。原始日志和完整结果为 `.local/runs/formal-01/`；精选[回执](../work/huangpingyang04-lgtm/63/receipt.json)与[科学摘要](../work/huangpingyang04-lgtm/63/science.json)。C保持blocked，远端上传/CI/审查/看板另行核验。

独立消费端另拒绝重新计算来源hash后仍非法的事件枚举、byte/单位bool类型等。事务建图当前支持全guard通过后、commit前的late abort；guard失败由原验收器拒绝，不允许将失败guard后的shadow标为有效。该边界不声称支持任意异常控制流。新增两项反例测试在后续正式复跑中独立计数，不改写195项旧回执。

最新正式资格为 `.local/runs/formal-03`，执行源 `fee9ca211fcfa1440a2a4f2a3607762129957e00`：197项（32原小图+31原估算器+134适配器），0跳过，10场景独立副本/进程重放。新增反例覆盖输出重新hash后的类型/事件错误；科学摘要仍为f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc，与195项旧回执逐字节相同，旧receipt不覆盖。见[最新receipt](../work/huangpingyang04-lgtm/63/formal-03/receipt.json)。CI基线获取修复后run40114765442已真实success；最终发布head的CI与待审查状态以PR79实际读回为准。登记PR5仍open/unmerged/pending；Projects无配置/工具，unverified/同步pending。


2026-10-25 生命周期复核：干净源 `10cd3d97d3b8ca9cbb242b1eee0078c2d708f577` 在全新 `.local/runs/formal-04` 实际通过 **200 tests / 0 skip**（原32+31、适配器137，其中核心48），10场景独立源码副本/进程重放，科学SHA仍为 `f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc`。修复显式复制后源槽复用的误拒绝，按实际驻留字节范围处理部分覆盖与多个view复制；独立consumer采用另一个范围覆盖算法，并重查alias/接口宽度/FIFO。新增3个合法/非法成对回归；最初负例因残留旧transfer源导致错误提前触发，保留本机失败和修正记录，未改原fixture。旧正式回执不覆盖，最新见 `work/huangpingyang04-lgtm/63/formal-04/receipt.json`。A/B选定范围pass、C仍blocked；软件in_review。

用户再次明确要求重试SSH后，仅执行一次BatchMode连接，结果为 `Connection closed by 10.129.166.172 port 22`，未建立远程会话、未读取或修改服务器文件；未改网络配置。旧服务器版本仍未比较，后续只读比较后在新目录整合，不能覆盖原件。


## 2026-10-26 服务器验收补充

用户重新授权服务器操作后，已只读比较旧目录8文件：core/resource_bridge/test_resource_bridge与发布版SHA不同；5个vendor资料仍保留，当前发布版改用固定的兄弟llm_resources。旧目录实际上缺少consumer.py、cli.py、__init__.py；旧记录的“曾实存CLI/consumer”未由本次观察支持。旧目录未修改、未移动或覆盖。

在全新 `/public/home/yuzelu/PingyangHuang/issue-63/server-validation-20261026T0100/repo` 核验发布源 `d07abaeef16049da199f0efa96acffc95bd487dd`，通过Slurm作业91622（hpy-adapter63、debug/node27、1CPU、23秒、COMPLETED/0:0）实际200项/0skip、10场景独立源码与新进程重放通过；科学SHA仍f2ec30e28966be33888cf314bd5e93a0bb24378d4147d79cbdd9ad9971efbbdc，与Windows逐字节相同。仅传输本任务Git对象、固定参考输入；未传凭据/配置/环境，未读#55活动文件或干扰作业。最初2G内存请求被Slurm拒绝（节点公布内存1MB），保留失败，命令覆盖--mem=0后提交成功，未改集群配置。

精选证据在 `work/huangpingyang04-lgtm/63/server-20261026/`；原始日志与完整输出留新服务器目录。receipt中的server_access=false表示离线验收器自身不发SSH，不代表本轮未在服务器执行，执行平台由execution.json和Slurm记录明确区分。A/B选定范围pass；C仍缺同版实例/真实M8引出/冻结底座等证据。软件实现、离线验证与服务器复跑均完成；正式结项仍待PR79审查/合并，当前零reviews、Issue in_review，不能宣称done。看板仍unverified/同步pending。
