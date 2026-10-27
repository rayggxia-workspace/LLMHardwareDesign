# T6K 保护负载与剩余间距诊断

2026-10-27。120 完整独立接收失败，完整 DRC 保留 23 项原始间距标记；原生 STA 还把 189 个 `ANTENNA_X1/A` 作为无有限 setup/hold 的端点列出。原失败不改写，不提前冻结候选。

新增诊断必须同时满足：实际 Liberty 只有一个 A 输入，存在正有限输入电容，无状态、逻辑函数、clock 属性和任何 timing group；实际最终 ODB 的 master 类型、pin 方向和根网与封存保护清单一一对应；仅这些输入的原生 STA 两项 slack 均为 INF 且无扇出；全部其他端点原行、原生违规计数、时钟和电气报告逐项保留。纯电容负载不会成为有 setup/hold 检查的采样端，但必须继续进入负载、RC、电气、面积、PG和物理检查。

`native_passive_endpoint.py` 初始版本仅诊断，不更改正式 `native_sta.inspect` 的接收规则。实际 DFF 加实际库保护单元的正例、真实超负载/短周期/缺输入约束反例与库时序弧/方向/函数/状态错误控制须在服务器执行；未通过前不能用于正式宏验收。本地 8 个合成报告/精确清单控制已通过，仅证明解析和分类边界。

`native_drc_locate.verify` 新增显式受限的 `native_pipeline_diode_full.json` 来源选择，绑定120失败回执、111成功源回执、原始lyrdb与ODB全部SHA。沿用只读真实形状/过孔/pin扫描，保留全部命中、未命中和歧义，不用包围盒命中替代精确GDS连接或DRC修复。

两项通过 `native-diagnosis-group` 在同一16CPU allocation内以两路8CPU并行执行，分开工作目录/日志/回执；实际可用内存少于48GiB时串行。独立一路失败不终止另一条。诊断组不新增物理候选、不复用删负载的网表、不减免完整DRC。实际部署与结果另留索引。

## 实际终态及正式接收绑定

2026-10-27 11:28 CST：131/92203同节点两路只读诊断通过1:09、TotalCPU33.743秒、MaxRSS697096K。23个间距标记全部定位，108形状命中、零遗漏，集中在少数边缘pin附近；M9同网短凹口和M10异网近距仍需实际修复。实际Liberty/最终ODB/真实DFF与STA证明189个ANTENNA_X1/A为纯电容负载；保留全部其余原报告后49544个有效端点全部有限且setup/hold非负，最差5.203448ns/.005355ns，电气/clock/原生计数逐项不变。真实过载/短周期/缺数据约束三反例及库timing/方向/函数/状态四反例均拒绝。新接收器仅在绑定131完整控制、同SHA库与模块、每个实际ODB根网后采用类型判定；原120失败不改写，23项DRC仍不通过。130旧接收仅部署无job，停用；后续134分组接收配置准备，等待128两路成功。

实际数据见 `work/YUZE-LU/121/results/run131-group-terminal/index.json`、`run131-locate-terminal/index.json`、`run131-sta-terminal/index.json`。新接收保留原始 `endpoints.tsv`，将精确类型报告另写 `passive-endpoint-audit.json`；其他端点原行逐字保留，原全部时钟/电气/count与无用输出判定完全相同。134尚未部署或执行，不报告完整Block通过。

下一有限探针核实际封存CTS的强制via接入可行性，同时读取安装版ORFS脚本与原生LEF；不改变原pin XY/几何或源ODB。官方[详细布线文档](https://openroad.readthedocs.io/en/latest/main/src/drt/README.html)区分via-in-pin包围限制与via-access层限制；[ORFS变量文档](https://openroad-flow-scripts.readthedocs.io/en/latest/user/FlowVariables.html)列出DETAILED_ROUTE_ARGS。安装版是否支持及真实接入结果仍须实际工具验证，不能据最新版文档宣布有效修复。

## Via-only 完整资格失败与并行只读定位

2026-10-27 13:18 CST：135/92222完整资格组已终态FAILED，48:10、TotalCPU4:55:06、MaxRSS73373228K。A独立DRC18项（M10间距16/M9间距2），C独立DRC2项（M10间距2）；原生DRT均0，全部其他接收门均通过，A/C最终功能三初态通过。两路不能冻结为合格宏。原始失败及全量DRC索引已保存，147依赖失败且从未提交job，停用；新148准备以一个16CPU c96 allocation内A/C两路8CPU只读定位，不修改ODB、pin或任何DRC规则。135按64CPU分配的整体CPU利用约9.6%，仅代表此批（含串行DRC等待段）；后续分阶段并发，并保留实际内存/CPU证据。128 C8两路进入详细布线；134/141继续等待128完整成功，当前6个本任务allocation，最多8个。

完整终态在 `work/YUZE-LU/121/results/run135-group-terminal/index.json`、`run135a-physical-terminal/index.json`、`run135c-physical-terminal/index.json`。先前两份功能终态仍独立保留。所有间距条目、精确坐标、来源哈希和17项通过的接收门均保留，不能将原生DRT 0当作独立DRC 0。定位器仅增加显式 `native_pipeline_viaonly.json` 的A/C来源选择；仍严格要求失败接收回执与成功源回执、原始DRC、ODB及input-sha256对应，扫描后再核源未变。148两路独立日志/回执、总线程上限16、48GiB可用内存不足则串行，失败一路不取消另一条。实际部署与终态另行保存。完整宏、父层物理、一般十二层RC/拼接、共同冻结底座与两产品仍未验收。

## 148 实际终态

2026-10-27 13:24 CST：148/92231同节点A/C各8核只读定位通过，1:11、TotalCPU54.043秒、MaxRSS1299772K；两路实际重叠约26.75秒。A扫描5743302形状/83命中，C扫描5738655形状/8命中，18+2标记零遗漏。M10标记均涉及相邻边缘接口异网，A的两项M9标记涉及read_data[43]同网凹口，仍未修复。147已读回确认无job/空state，因135失败停用；134/141继续等待128完整成功，当前6个本任务allocation。安装原生DRC脚本固定threads(4)，已新增节点内并行决策，按实际阶段CPU/内存配置并发；全部验收门保留。

源码a153b97d974f14a41a9bcce6a5d92214cafa3baa，归档078e2dd061a9dfc9484b4b00d0a06b474670de04c400f97bf2b3e3dda8d591e5，156成员/1054720字节。组及A/C全部终态索引保留在 `run148-group-terminal`、`run148a-locate-terminal`、`run148c-locate-terminal`；原失败仍为135，每路18项接收门中的17项通过，独立DRC门失败。定位包围盒候选与原始edge-pair共同支持上述诊断，不能将定位通过当作路由修复；进一步接入路径/路由器行为仍待有限实际探针确认。
