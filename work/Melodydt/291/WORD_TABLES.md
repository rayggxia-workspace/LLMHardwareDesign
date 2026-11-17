# 七模型论文 Word 双表

2026-11-17（Asia/Shanghai）；负责人 Melodydt；[Issue #291](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/291) / [PR #292](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/292)。沿用 `task/291-seven-model-prefill-estimate`，准备时 head `074533d74ae5bdd1af5361449674b91edd0884b3`，基分支 `task/280-seven-model-energy` 的 `78812ea98ddc5714ea3e71d789b9800a4641bb7e`。最终提交见 PR；未启动新仿真。

## 成果与口径

[Word 双表](../../../docs/experiments/seven-model-dac-tables.docx)，本地交付 `output/docx/seven-model-dac-tables.docx`。一页、两个原生可编辑表，参照用户 `D:/Download/v2-IEEE-integrated.docx` 第3页三线表。Letter、跨双栏18.3903 cm、Times New Roman 8 pt、表注7.5 pt；表号II/III承接原稿现有Table I。插入论文时放入跨双栏节并保留源格式。未修改或上传原稿。

- 速度：七模型列；短Prefill、512-token Prefill条件估计、Decode三行，token/s，三位小数。
- 能耗：片上与片上＋DDR两组，各分Decode/Prefill；J/token，四位小数，保留low–high标定端点。
- Prefill能耗仅对应两输入token的短窗。512-token吞吐为含最终一次词表头的估算，短Prefill不含该头；完整P512误差未独立验证。非线性样本继续线性估算的限制已加星号表注。
- 两个能耗口径均为已覆盖分项。读DMA、未标定特殊算术与其余控制/时钟/互连缺项、DDR PHY/板级及主动省略的布线寄生均在表注说明；端点不是整体误差界。

冻结源 `combined-results.json` SHA-256 `741b593914265932c88c1b9924bdd80d8e8ae3e78e1652741cd66b4c3bf200e9`；它沿用综合PDF的七模型数据，不改 #280 或已有速度回执。原稿SHA、DOCX SHA与未舍入输入字段见 `word-tables-manifest.json`。

## 实际验证与复现

使用 Codex bundled Python（版本见 `word-tables-qa.json`）和 python-docx；构建与核验：

```powershell
# $py 指向当前 Codex bundled Python。
& $py work/Melodydt/291/build_dac_tables.py --reference D:/Download/v2-IEEE-integrated.docx
# 用 Word 只读打开 output/docx/seven-model-dac-tables.docx，导出临时 PDF 后：
pdftoppm -png -scale-to 1700 work/Melodydt/291/tmp/word-tables/final-render/tables-final.pdf work/Melodydt/291/tmp/word-tables/final-render/final-page
& $py work/Melodydt/291/verify_dac_tables.py
python -B scripts/check_project.py
```

本次 `build_dac_tables.py`、`verify_dac_tables.py` 均运行通过。原稿哈希不变；两表七模型、21个速度单元格、28个能耗区间/56端点、原生编辑结构、宽度、字体、重复表头和不拆行已检查。最终Word16.0只读导出1页，PDF文本主值和关键边界说明检查通过；`final-page-1.png` 全页人工目检：没有溢出、裁切、重叠或断行错误，模型列对齐，区间完整可读。管理结构检查通过，不替代业务/物理检查。

标准 `render_docx.py` 已尝试，环境缺LibreOffice；改用经批准的独立隐藏Word16.0实例、禁用宏、只读打开后 `ExportAsFixedFormat(...,17)`，退出不保存。覆盖第一次预览失败后使用新的PDF名，最终成功。Poppler报告Symbol/ArialUnicode字体映射警告，图像上实际TNR内容完整，非交付缺失。QA PDF/PNG仅本地；不作为额外交付上传。没有重复仿真、综合或物理流程。

## 接续和状态

本地是无.git的参考副本。本任务仅写 `work/Melodydt/291/` 和 `output/docx/`；共享进度/架构的拟提交版本在 `publication/` 隔离保存，不覆盖父会话文件。通过Melodydt连接向已有任务分支交付。PR草稿、Issue in_review，待指定独立审查人；不自合并。登记沿用management-hub PR5 pending；缺 `config/board.json` 和Projects工具，实际看板unverified、同步pending，待具权限维护者处理。

恢复第一步：读PR最新head和本说明，再核验输入清单；如数据变化，明确新版本和覆盖范围后重建双表并重新渲染。原独立序列验证继续按用户要求暂缓，未新建后台监测或服务器任务。
