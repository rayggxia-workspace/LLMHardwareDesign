# 七模型速度与能耗合并表

2026-11-18（Asia/Shanghai）；负责人Melodydt；[Issue #291](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/291) / [PR #292](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/292)。沿用task/291-seven-model-prefill-estimate；本轮父提交31d6e0011f3f06c8d0bf1106db2fc9cec95b0c0c，基分支task/280-seven-model-energy。最终提交见PR，不新建任务或仿真。

## 交付及数据口径

[可编辑Word合并表](../../../docs/experiments/seven-model-dac-combined-table.docx)，本地output/docx/seven-model-dac-combined-table.docx。一页一个原生Word表，七个模型分组，每组Prefill/Decode两列；三行依次为吞吐（token/s）、片上能耗（J/token）、片上＋DDR能耗（J/token）。跨双栏18.3903 cm，TNR8pt，两级表头、重复表头、不拆行，表注7.5pt。旧双表和原论文保留未改。

按用户最新要求，Prefill吞吐直接采用estimated_input_tok_s_to_logits（512-token估计，含最终一次输出头），Decode沿用已有decode_tok_s。能耗采用既有区间的下端点，四舍五入到四位小数，不声称绝对最小值或完整芯片能耗。**Prefill吞吐是512-token估计，Prefill能耗仍是两token短窗；两者不能组合成同一512-token实验的功率。** 文档以加粗表注明确这一点，保留完整序列未独立验证、非线性仍线性近似、未覆盖分项及省略寄生说明。

冻结源combined-results.json SHA-256为741b593914265932c88c1b9924bdd80d8e8ae3e78e1652741cd66b4c3bf200e9。源速度与功耗范围不变，只选择字段、端点与排版。详细字段、42主值和输出散列见merged-table-manifest.json；校验结果见merged-table-qa.json。

## 构建与实际检查

使用Codex bundled Python3.12.14、python-docx1.2.0。先将已归档docs/experiments/seven-model-dac-tables.docx复制到本地output/docx/同名文件，作为风格来源；或沿用本地前次交付。

```powershell
# $py 为当前Codex bundled Python。
& $py -B work/Melodydt/291/build_dac_combined_table.py
# 用独立隐藏Word只读打开新DOCX并ExportAsFixedFormat(...,17)到以下临时PDF。
pdftoppm -png -scale-to 1900 work/Melodydt/291/tmp/combined-table-render/combined-table.pdf work/Melodydt/291/tmp/combined-table-render/page
& $py -B work/Melodydt/291/verify_dac_combined_table.py
python -B scripts/check_project.py
```

构建、42主值与既有JSON下端点核对、七个模型跨列、14阶段列、两个重复表头、原生编辑结构、宽度/字体、原始数据/旧双表/原论文SHA均通过。标准render_docx.py本轮确实尝试，但环境缺soffice.exe；沿用已批准的独立隐藏Word16.0只读导出，成功1页。Poppler有未使用Symbol/ArialUnicode字体映射警告；最终page-1.png全页目检，模型和阶段列清晰、数值完整、没有溢出/裁切/遮挡，加粗窗口口径提示可读。QA临时PDF/PNG不作为额外交付上传。管理结构检查通过；没有运行新的业务仿真或物理流程。

## 接续与交付状态

本地无.git，新增仅work/Melodydt/291和output/docx；公共文档隔离准备，不覆盖父会话本地文件。通过Melodydt连接提交已有分支/PR，源数据不混入主线更新。Issue in_review，PR草稿、未合并、审查人待指定。登记沿用management-hub PR5 pending；config/board.json本轮读回404，无Projects工具，实际条目unverified、同步pending，由具权限维护者处理。

恢复第一步：读取PR最新head及本说明，再核验manifest源散列。如果希望Prefill速度/能耗来自同一个512-token窗口，需要另做完整Prefill能耗评估，当前表没有完成该工作。原独立序列验证仍按用户要求暂缓，无新增后台监测或服务器任务。
