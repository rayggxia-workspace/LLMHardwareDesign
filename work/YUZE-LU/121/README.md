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

服务器成果根：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/`。
`block-v1-20261027-001`/`002`为以上两个探针；后续各run以不可变manifest和状态记录。

## 尚未验收的完整范围

完整新顶层四profile数学/恢复/epoch/root及背压回归；全部真实存储与逻辑成本；P0存储实体/预算定版；原生层硬化、PG/CTS、严格完整STA/电气；真实M10内部pin/OBS与边缘对照；十二层RCX/DRC校准；宏同源与精确门级；共同底座冻结；同底座两产品仅新层定制及敏感性；正式参数库/PR审查。均保留在#121，不提前关闭。

登记沿用管理中心PR5 pending。当前无board.json及Projects能力，真实看板unverified、同步pending，管理员待指定；不能以管理CI代替研究验收。
