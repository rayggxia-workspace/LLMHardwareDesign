# 七模型512-token Prefill条件估算交接

负责人 Melodydt；[Issue #291](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/291) / [PR #292](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/292)。仓库 rayggxia-workspace/LLMHardwareDesign，分支 task/291-seven-model-prefill-estimate，基点89b02b0424e3ab923fca320509a4058692bd5f97，采样源码395fe768ceaed45ef2b822d9ce288e1f98f0fe0f。

本轮完成用户要求的计时拆分、长度建模及局部采样，报告已逐模型更新。保留原短P2和两步Decode，新增P512主体/一次词表头条件估计。Phi/Falcon的局部直线偏差为10.72%/10.16%，按用户要求继续线性并显眼标注；Granite未增加路由扫描；混合模型只测固定大小递推零态/512末态，未取得中间真实递推快照。独立16/32-token验证用户暂缓，不称完整P512结果已验证。

## 真实位置

- 本地无.git参考副本 D:/Study_material/Study_material/LLMHardwareDesign；本任务新增内容仅 work/Melodydt/291，公共文档版本隔离在其 publication/。未覆盖父会话文件。
- 服务器 t6s011227@BSCC-T6@ssh.cn-zhongwei-1.paracloud.com，~/LLMHardware/zenanyan/issue-291-prefill-01/run-38826721。代码在其上级，工具沿用~/LLMHardware/opt。
- 38826721，v6_384/m3ca0801，7×1核，UNLIMITED，COMPLETED 0:0，30秒。38826673/38826697失败记录保留，原能耗作业不动。日志slurm-38826721.log和逐模型.log。
- [报告](../experiments/seven-model-speed-evaluation.html)、[机器结果/回执与命令](../../work/Melodydt/291/README.md)；样本源码、输入/输出SHA均在对应JSON。

实际检查：330 ATT的独立读量公式、8递推状态写回与回包守恒、原速度字段不变、显式512项插值求和、回收样本与服务器清单SHA、HTML主值与警示、管理结构。未执行独立序列或完整512数值/RTL/物理验证。

## 恢复第一步

先读取PR当前head与报告，核验 work/Melodydt/291/results/server-results.sha256 中已回收samples.json，然后根据用户下一步指令处理独立序列验证，或Phi/Falcon非线性、MoE路由及混合前缀状态。原任务#280的能耗覆盖单独进行。

在线与验收：本任务分支提交不等于合并主干。PR草稿/未合并，审查人待指定；登记沿用management-hub PR5 pending；config/board.json缺失且无Projects工具，条目unverified、同步pending，处理人待具权限维护者。本轮未配置自动监测，所有新增采样作业终态。规则rayggxia-project-collab 1.0.0。

交付时读回基分支已前进到78812ea98ddc5714ea3e71d789b9800a4641bb7e；将其完整树合入本任务分支，保留主线PDF v2.1及新增进度。速度数据与采样源码不变。报告数据提交0441c9950eca5f3c21d240835e936a928ff18664；ZIP SHA-256为9b3dc6b784d8fc972a71b3e51bf912b1ab7d7749cf88de727fcc09c022b8884f。HTML/JSON/ZIP/清单远端Git blob SHA与本地一致。任务状态in_review，PR仍草稿未合并。
