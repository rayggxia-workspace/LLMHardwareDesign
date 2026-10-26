# Issue 121 执行记录

负责人 YUZE-LU；[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)。
分支 `task/121-block-v1-twelve-layer`，独立工作树，不改变 #116 工作区。

## 状态：P0/P1，尚未进入正式 Block P&R

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
