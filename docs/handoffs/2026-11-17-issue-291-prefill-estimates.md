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

用户追加PDF交付已完成：24页/39表，SHA-256 839d0d379507f680bd49fac300b0fbe5d34aef694c97692362af12ad2209fbf1。1939单元格、8警示框、7模型和2链接核验通过；全部页面渲染目检。生成脚本与依赖见work/Melodydt/291/PDF.md；源HTML/JSON及原ZIP均保持不变。此次只追加文档输出。

## 追加速度与功耗综合PDF

用户追加七模型速度/功耗统一报告和论文验证段落，已复用本任务完成14页PDF。速度输入为0550231版本，功耗索引为78812ea的v2.1，未改原速度/能耗。三单位W、J/token、token/J覆盖短P2和第二步Decode，分别列片上与片上＋DDR；完整P512误差、完整P512功耗仍未知。PDF SHA-256 11187931d2dea7129febba62bbf696301ddddd36a499bbfac36a0a68aa73f836。9来源、14时窗、168端点与482PDF文本项通过；14页渲染目检。第13页是中英文论文建议，原DOCX未修改。

恢复先读work/Melodydt/291/COMBINED.md、combined-inputs.json与combined-validation.json；若源数据有新版本，先明确更换口径再更新清单，不直接混用。独立序列验证仍待用户指令。无需远程续跑，本轮无新作业。负责人Melodydt；PR草稿in_review，登记/看板限制不变。


## 论文 Word 双表接续

2026-11-17（Asia/Shanghai），本任务追加docs/experiments/seven-model-dac-tables.docx，一页两个可编辑三线表。21速度单元格、28能耗区间及最终Word渲染检查通过，SHA-256 e5881fac9aebcbf4b047d0a0dcf35276d3e943747161e5479054b39626d5e9bf。原稿/冻结combined-results.json未改，无新服务器任务。构建前head为074533d74ae5bdd1af5361449674b91edd0884b3，最终提交以PR #292为准。本地output/docx与work/Melodydt/291已生成，公共文件仅publication/word-tables隔离准备并走任务分支上传；本地根目录无.git。恢复第一步读work/Melodydt/291/WORD_TABLES.md和word-tables-manifest.json，再核对PR最新head。负责人Melodydt；独立验证暂缓，审查人待指定，PR草稿in_review/未合并，登记pending，看板unverified/同步pending。


## 2026-11-18 合并Word表

用户要求已落实为docs/experiments/seven-model-dac-combined-table.docx：七模型、各Prefill/Decode两列、吞吐和两类能耗三行。Prefill吞吐为512-token估计，Prefill能耗仍是短P2；能耗选既有区间下端点，二者不可直接组合为同窗功率。原双表和冻结数据未改。42主值、7跨列表头、14阶段列、源SHA、Word1页及全页目检通过，DOCX SHA-256 cbcb2d94925054f2a0b7a0398222896056f033d91dfed7176f43d45ac3e61167。准备时head31d6e0011f3f06c8d0bf1106db2fc9cec95b0c0c，最终提交以PR292为准。恢复先读work/Melodydt/291/MERGED_WORD_TABLE.md及merged-table-manifest.json，再核对PR最新head。本地无.git参考副本，新增仅任务目录与output/docx，共享文件publication/merged-table隔离；没有新服务器任务或监测。负责人Melodydt；PR草稿in_review/未合并，审查人待指定，登记pending，看板404/无Projects工具、unverified/同步pending。
