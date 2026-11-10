# Issue247：已实施优化与最新旧体系性能总览

负责人 Melodydt；2026-11-10，Asia/Shanghai。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，现有任务分支 task/242-r-load-bounds，in_review、未合并。用途为用户请求的统一总结和 PDF；没有新增 RTL、服务器仿真或第五轮。

正式报告：[已实施优化总览与最新性能评估](../../../../docs/experiments/issue-247-implemented-optimizations-summary.md)。包含六类生产可选功能、继承直连、独立实验候选、最新八场景、历史矩阵、容量/融合参考及实现边界。

## 数据与来源

- `extract_metrics.py` 解码已提交的五个完整 result，要求固定 SHA 与 passed=true，排除 smalltrace 单算子诊断；按 workload/profile/variant/context/容量/端口/切换/复用/预取策略精确配对。
- `summary.json` 包含 8 条 R4-enabled 结果、同配置 run15 与 R2 基线、百分比、整 trace 时长、历史 16 配置矩阵、4 容量参考、完整来源与输入 SHA。解码复核 93 条完整场景；本次没有新仿真。
- `notes.md` 是派生数据的可读表；历史值不得描述为 R4 未测配置的结果。
- 生产源核对基点：fcc21de7ac57b2c2916c21795e797d6f6207daae；最新 RTL 校准源 7048c35ed2912e80e62bd7827deaec480d4a7e1a，模型源 e6209544086f2460662bf7edfc91cbfb2c63cd9b。文档提交不替代实验源码版本。
- 原始原件仍位于 `../speed-iterations/round01..04/` 和 `../legacy-metric-eval/`；不重写其源绑定证据。A64 融合及 FIFO 回放引用 `../fusion/summary.json`，与最新版 RTL 配置分开。

从仓库根目录复核（Python 标准库，不运行 EDA）：

```powershell
python -B -X utf8 work/Melodydt/247/optimization-summary/extract_metrics.py --repo . --output tmp/issue247-summary-verify
```

本次实际复核由 bundled Python 在非 Git 快照内读取上述原件，输出在隔离目录 `work/Melodydt/247/summary-research/root-verify`。两次 summary SHA 完全一致：61c031815a9497721e882cb9eeb1a5c0aa06d8a19102bc79e51acff5ce923ff4；notes SHA fb4d60a1eb5a103b7fc5b4610aa97be73783a452f36adfa89754a59f8a4f20cb。

## 大容量条件模型与面积预算

新增[capacity/README.md](capacity/README.md)记录run04/run05/run09的完整结果、8个面积来源SHA及两份可复算脚本。逐字节复核JSON一致：性能5f8e2e6b77ccecb96ab3cf8d456922a05d92ca2f9b2c30ac8b953b9824accdbb；面积6812b9e5f3d49a782a8b6fd3140585881dff7dffef16e963f219a9853e99b8d4。历史完整trace109条包含重复回放，不与前述93条相加当独立配置数。A48/A64未实装，面积属于相同1RW宏的容量复制代理。

## PDF 生成与核验

本次10页修订版绑定报告源commit 9d987151ee687322c0ce52d69a0a14f2275bd52b，源SHA e5a6b28d672d089d63b5526d4834114b7908b91ee686a7e6e2ed938942abb80d。PDF SHA-256：3e70437bac53997fc7f4471dc00bd261268b34dedd27661188d001239b2ec9d1。404内容单元、16表/85行、2代码块、全部链接与嵌入中文字体及10页逐页视觉QA通过；完整证据为[pdf-capacity/qa.json](pdf-capacity/qa.json)。artifact edit marker e93afc成功执行一次。PNG本地保留并在QA中索引，不上传大图。

`export_summary_pdf.py`从固定commit的Markdown导出全文，`finalize_summary_pdf.py`在全部PNG实际查看后记录QA。Windows依赖reportlab、pypdf、pdfplumber、Pillow、微软雅黑/宋体和Poppler，来自Codex bundled runtime。导出参数包含`--artifact-marker e93afc --compact-table-sections 7`，第7节压缩表格留白，字体大小不变；Poppler `-r 120 -png`，最终render回执4ce39b，finalize回执8a3f33。

正式PDF位于[docs/experiments/pdf](../../../../docs/experiments/pdf/issue-247-implemented-optimizations-summary.pdf)。旧用户副本被打开占用，首次覆盖返回PermissionError；因此新用户副本保存为`output/pdf/issue-247-optimizations-capacity-area-summary.pdf`，没有强制关闭查看器。首轮11页排版含短尾页，已调整后重导出为10页并重新检查全部页面。

旧7页版本保留在[原提交9925300](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9925300dc32c18b786bff7a3fe14a2c07ce5746f/docs/experiments/pdf/issue-247-implemented-optimizations-summary.pdf)，旧[pdf/qa.json](pdf/qa.json)仍对应该历史PDF，不能用于校验当前10页文件。旧报告固定c60106201c232742c701da6b3861df575208f8e3、旧PDF SHA4625c72b6b472a048fdc6f0fc7e29d38309b82b0f05b085654f376c34ec23ef1。

## 限制与接续

300MHz 与理想1R1W仍是旧模型条件，不是新物理资格；共享端口列也不等于原生完整生成。prefill2 是两个输入 token 吞吐，不能作为 decode TPOT。R4 未测 ctx1、decode128、W16 prefill、W16 decode2048、48/64KiB 联合配置。

6 类生产参数默认保持兼容，旧母控镜像没有自动启用新功能；独立实验 RTL 与仅模型候选不混入生产清单。既有四轮因轮数上限结束。下一步独立审查本报告/实现与证据，恢复时核对最新 PR head；审查人待指定。

登记 management-hub PR5 pending；缺 config/board.json 和 Projects 工具，看板 unverified、同步 pending，管理员待指定。GitHub CI 以最终 PR 回执为准，不以本地管理检查替代线上 CI 或业务/物理验收。
