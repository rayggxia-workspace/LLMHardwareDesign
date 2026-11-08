# 通用路由实际后端接入

任务 [Issue230](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/230)。
用户指定 main 新五类、P×3/U×2/C/F/J×2 九组 `_64`，前置 #220。
本目录保留实际证据索引；**完整九组产品闭环未完成**。不以局部接口回归替代用户要求。

源码：`project/experiments/upper_router/`；[实现与验收边界](../../../project/experiments/upper_router/BACKEND.md)。
父提交 `f0273848e1872d9b2d9488981eaf279a902218a5`，独立分支 `task/230-backend-router`。
硬件 main 固定 `c4d7b960599b9d292f27eb4429d5f226a7156c95`；
#220固定 `f23a6d93448849b6f7b15edccce7e996d1092e7d`。
五包及包 SHA 见 [inputs.json](inputs.json)，U 使用 #221 修复包。

服务器所有新增工作：
`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-230-backend-router/`。
每项10核、最多六项同时执行；不修改其他任务、他人目录或原始验收归档。
源包各自保留在 attempt01–12，实际执行代码以各源包为准；失败不覆盖。
本次代码已提交[草稿PR231](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/231)，
前置仍为#229/#227/#220。最终证据收集100471依赖100406结束；源包SHA
`6810443dbb78813243f81ebfc7e350e7b3969592b57284b560d86704022901df`。
attempt12采用最终29项测试并打包小型实际上层ODB/GDS，原生合成GDS留在服务器。

## 当前已取得的证据

- 五个包级 SHA、全部清单文件重新校验；实际 ODB 端口、几何及驱动/接收端导出。
  完整索引体积约35–57MB/类，保存在服务器及本地独立 artifacts 目录；Git 仅保留
  [散列、计数和晚接端点摘要](evidence/inventory-index.json)，不纳入大物理文件。
- 五类晚接接口362网由通用算法生成路线，实际 DEF→ODB→矩形导出已通过；
  数量为 P34/U130/C34/F34/J130，均来自当前交付包连接合同，无手写模型路线。
- 本地29项算法/后端测试通过；服务器100463同29项通过（100414为此前26项）。最终显式 RC 参数版本
  与已执行路线的 DEF/LEF 五类逐字节相同。
- 实际 OpenDB 过孔删除、原生 GDS 哈希错误两个负对照均被独立物理读回拒绝。
  [原始检查回执](evidence/handoff-check.json)、[29项日志](evidence/tests-29.log)及
  `evidence/{P,U,C,F,J}-physical-readback.json` 已回收；未改写原始报告内容。
- 100404 重新运行原检查器，#220 的1083任务通过，18个逻辑束的产品级信号映射
  尚未提供，#227需求保持 unbound。不是18束物理不可布的证明。
  [原始产品输入审计](evidence/readiness.json)逐束列出未绑定原因。

五类完整 GDS 读回与全部原生层 XOR 已由100399全部通过。原版 DRC100406仍在运行，
最终状态见后续收集的作业和文件索引；
没有相应报告的项目不记通过。无新的分布耦合RC/电气/STA结果，所有几何工件保持
`physical_qualified=false`。

## 失败与修改

| 尝试/作业 | 问题 | 修改与复验 |
| --- | --- | --- |
| attempt01 /100378，五项失败 | 原容器未启用 OpenROAD `-python` | 改为Tcl只读导出；attempt02/100383五项通过 |
| attempt03首次提交被拒绝 | Slurm节点memory登记1MB，不能请求60GB | 使用集群默认内存策略；仍每项10核，未独占CPU节点 |
| attempt03 /100389，五项失败 | KLayout未采用外部Python模块路径 | 将独立散列函数放入读回脚本；未改几何规则 |
| attempt04 /100394，五项失败 | 错误要求ODB/GDS的DBU相同 | 精确换算0.5nm/1nm，并拒绝不可精确表示的坐标；attempt05复验 |
| attempt08 /100408，失败 | 测试源快照漏带同级block_synthesis依赖 | attempt09补齐相同依赖；100414全26项及两项物理负例通过 |

这些失败是工具/输入/交付适配问题，不冒称算法已经解决了长线电气或拥塞失败。
没有放宽线宽、金属间距、切孔间距、原版DRC、Liberty或频率门槛。

## RC 采用的证据

- #202 `20b945d3cdb73d74778bdccc4952eb4315170cd8`：查表遗漏跨层互容及场解修复。
- #216 `5f055f6cd1349174ecb71ea55bc48e9acd6a618d`：旧#206实际完整上层场解和SPEF读回。
- #218 `40f65575427a7bdfed6782775ce0b07226e4f7c7`：固定几何铜R敏感性，主Rs0.0102Ω/□，
  via仍0.08Ω假设。相同几何才可复用C，新路不能套用旧SPEF。
- #225 `3c544b8547eb4cd9ac7ac98aaa86073ceea361ca`：真实下层耦合会改变上层负载，
  仍是旧版图，不是新底座的耦合后系统STA资格。

实际工具：OpenROAD版本自报unknown，二进制SHA
`0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53`；
KLayout0.30.12，SHA`fee1214ef5c63033057626a9dab0deb0664fecb69184d1c3fd43dc9c0dc1eba5`；
容器SHA`49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`。

## 完整目标剩余的实际依赖

main 的五类独立交付不包含九组共同 ODB。约2300–3000个夹具端口中，信号M10端口
只有68或260个，其余大多在M5/M6；现有后制规则不能直接接上。局控PM仍在夹具外，
当前独立母控只有两个驻留目标。#220 的真实整网使用虚拟外存，其逻辑 read/write
和io.load/store尚无完整产品信号目录。少数晚接旁路不能替代这些服务。

恢复完整产品工作的第一步：以真实叶宏视图、当前局控/适配RTL生成九组共同原生候选，
明确局控ID、PM、母控分发、实际memory gateway及固定预连；重新落实M10端点、PG/CTS
和原生工程验收，再导出全局base/catalog。五类分组继续是控制归属，不生成五种大硬块。
随后用同一#220 binding生成全静态网、布线、重新提取上下层耦合并跑原库300MHz门。
当前未建立此完整候选，不声称用户的最终目标已经完成。

规则 rayggxia-project-collab1.0.0；负责人/操作账号YUZE-LU。登记沿用management-hub
PR5 pending；缺board配置，Projects unverified/同步pending，复用Issue7交接。
未自合并、批准、关闭或将Issue标done。独立审查人待指定。
