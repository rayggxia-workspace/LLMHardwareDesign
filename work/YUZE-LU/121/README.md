# Issue 121 执行记录

负责人 YUZE-LU；[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)。
分支 `task/121-block-v1-twelve-layer`，独立工作树，不改变 #116 工作区。

## 当前执行快照：2026-10-27 CST

P0/P1 与 P2 资格推进中，尚未进入正式 Block P&R。91903 精确完整映射门级仍在构建；不能因源码或逻辑层测试通过而提前验收。

- run009：91905 新层路由接入和原生 SAMENET/EOL 读回通过；91907 数学/协议 8 种语义故障均被拒绝，原始证据未修改。
- run010：91909 完整同源叶块网表、4389/386 位端口和 SDC 已生成；91910 原生 GDS/图层映射审计通过。物理预算见正式决策。
- [run012](results/run012/index.json)：91914 独立 GDS 接入几何、M10 mask 不变和五类负例通过；91916 更新的官方固定场求解器通过原作者 2D/3D 参考及线程/介质缩放检查。91915 解码 133488 条线网覆盖全部十二层。
- 后续科学复核发现校准分组必须包含同实验的全部 cntxM 导体；91915 的旧分组不可用于 RC 校准，修正另开 run。见[场景决策](../../../../docs/decisions/2026-10-27-block-v1-calibration-scenes.md)。完整校准/模型拟合/留出验证、全层 DRC、正式硬化与共同底座冻结、两产品定制均未完成。
- run013/014 修正分组和新版求解器资格/先导通过。run015 实际使用 node14–node19 六台96核节点，各8×12线程；严格点估计符号断言拒绝原结果，run016按预先记录的统计接收界限独立重验全部通过，原始输出不改。
- run019：3840行场解＋3344个DC图形实际拟合；逐网R/地C/耦合C读回最大缩放误差低于6e-8。该模型只是候选。run020旧格式读取崩溃；run021现代格式可读，run022实际耦合提取崩溃，未进入留出数值比较。发现距离3校准留下1542个空表，正在准备全十二层上下文新批；不会将这些失败当作RC资格通过。

### 03:27 CST 增量

- run024–026 完整上下文与六分片参考场解通过；run029 候选拟合通过，2472表的有效覆盖检查通过。188个官方未使用格式槽位为空是合法的，不放宽实际必需表检查。
- run030 实际提取完成但跨层耦合留出失败；run031 的2.0/2.2/2.3均未解决，旧模型未验收。
- [run034](results/run034/index.json)：91986–91991，node14–node19六台机器，六种小几何的直接场解与独立有限体积参考全部通过，三网格、远边界、残差和预先锁定阈值均通过。
- [run036](results/run036/index.json)：六例真实DEF/SPEF/OpenDB及独立GDS mask集合核对通过；错误电容单位和折掉耦合的负例均被拒。短线π网络尚不代表完整Block分布式RC。
- [run037](results/run037/index.json)：实际路由ODB路径/过孔/端口可直接导出，实例pin与PG尚需补齐；run038实例坐标API探针失败保留，修正另开run039。详见[直接场解决策](../../../../docs/decisions/2026-10-27-block-v1-direct-field-extraction.md)。
- 91903完整映射门级已编译，正在运行两种背压混合回归；未取得完整回执，不提前记通过。正式Block P&R仍未开始。

以下保留各早期阶段的历史记录；其中“尚未”以本节当前快照为准。

## 初期状态：P0/P1，尚未进入正式 Block P&R

按 `docs/plans/block-v1-nangate45-m11-m12.md` 全部阶段执行，不能将以下局部工作等同于 v1 完成。

- 原计划 SHA256 `2ef18149c806cfbda996bbc91b69c84b31781ad9553e7093630d1f7a2ddc20cf`；源闭包33文件全部满足原科学SHA与发布Git blob，见 source-manifest/source-import。
- 2026-10-27 CST，探针91865/node13失败：计算节点PATH缺Singularity，原日志保留。修正显式PATH后91866/node13 `COMPLETED 0:0`；Python3.10.12、Verilator5.042、Yosys0.68+post、KLayout0.30.12可用；OpenROAD版本字符串unknown，按二进制SHA绑定。
- 探针镜像SHA `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`；实际tech LEF SHA `834a79295054cd4209178d1bade67c353863c47bb4b3c22ee38b862b7cec37f2`；原生最高metal10、cut到via9、RCX LayerCount10。
- `transaction6k.sv`：真实384×128bit，顺序填充、整事务commit/revoke、同步读取、背压保持、消费者单引用lease释放；复用前必须完整覆写，无RAM reset假设。测试/映射结果须看实际作业回执，源码存在不代表通过。
- `shared121.sv`：保留C8控制器/观察接口，内部接真实T6K，只有core DONE成功后发布payload；候选接收后等待root提交完成；DONE ACK等消费者release。基线数学/外存桥/单一S16K不改。新顶层回归尚未验收。
- `technology.json`/`overlay.py`：十二层几何研究起点，M10 landing不需后增补；原生字节精确保留。early RC明确仅估算，完整RCX/耦合校准和新层DRC尚未完成。
- 单dispatcher跨本Issue各run共用预算锁；六基础/八上限，排队及未知提交计槽，节点内线程显式分配。只轮询本任务jobID，不改其他作业。
- 003批91872–91877全部在启动时失败（exit2）：Git archive受Windows core.autocrlf影响导出CRLF，未进入业务计算。blob实为LF，新增bundle.py直接逐Git blob打包、shell LF负检查及worker逐文件SHA验证，另开新run，不改旧日志。

服务器成果根：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/`。
`block-v1-20261027-001`/`002`为以上两个探针；后续各run以不可变manifest和状态记录。

## 尚未验收的完整范围

### 2026-10-27 CST：已取得的实际业务证据

- [草稿 PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)，持续实施，未合并。
- 004批：91878 T6K随机242事务、264051周期、3295817断言通过；91879两种真实存储映射通过；91880完整C8＋S16K＋T6K映射通过，Yosys层次面积1538342.904 μm²，尚未独立库存接收或PPA验收。
- 006批：91893完整13命令混合回归、91894完整44命令恢复回归，各在两种背压条件下运行，独立整数接收全部通过；91895十二层LEF/OpenDB读回通过。见 [run006/index.json](results/run006/index.json)。
- 004/005/006结果保留原失败：旧LEF版本语法失败、旧工具缺PythonAPI失败均不覆盖；修正后使用新批次。十二层读回通过不等于路由、DRC、RC提取通过。
- 当前工具不带内置场求解接口。计划编译官方固定提交6ea4ca的独立C++场求解闭包，先校验原作者2D/3D有限体积参考算例及线程一致性，再开展研究RC校准。源码53文件257109字节，归档SHA `b2eaefce378aba09cccb966b3c56486412f1958e0a83ff3fb313fd35b3dfe2a7`；清单见fsv-source-manifest.json。尚未编译或宣称校准完成。
- 上述短作业实际由Slurm分配到node13；“六基础/八上限”是本任务并行预算，不能把同机多个allocation声称为六台物理节点已被利用。重型物理阶段依据实际分配CPU/RAM装箱。

独立全部真实存储与逻辑库存；数学/协议接收负例；精确映射门级；P0存储实体/预算定版；原生层硬化、PG/CTS、严格完整STA/电气；真实M10内部pin/OBS与边缘对照；十二层RCX/DRC校准；宏同源与最终门级；共同底座冻结；同底座两产品仅新层定制及敏感性；正式参数库/PR审查。均保留在#121，不提前关闭。

登记沿用管理中心PR5 pending。当前无board.json及Projects能力，真实看板unverified、同步pending，管理员待指定；不能以管理CI代替研究验收。
