# Issue68精选R证据包

`portable_r.py`提供不依赖旧5GB包的精选整数接收。选择预先固定为真实legacy layer0/end8192、S16与S32 D31、guard_rescale的连续token `[2,14)`；完整H2/K128/V128不切分。该段包含真实token3、12两次范围拒绝/重定标，各有前后步。不是按误差挑好样本，也不代表完整256步或全模型质量。

```text
python -B project/experiments/range_service/portable_r.py collect --legacy <issue66/long-state01> --integer <issue68/range-legacy01> --oracle <冻结receive_range.py> --audit <receive-legacy01/audit.json> --chunks <chunks01.json> --out <新目录> --binding <JSON>
python -B project/experiments/range_service/portable_r.py verify --bundle <新目录/portable-r.zip> --out <新接收receipt.json> --negative
```

collect binding为`portable_r_sha256`、`receive_range_sha256`、`commit`。所有操作只在获授权目录；真实采集和打包由服务器Slurm执行。verify只需要本脚本、Python与NumPy和这个ZIP，不访问原source root；ZIP也包含本脚本与固定SHA的独立`receive_range.py`源码，可解出本脚本单独运行。独立oracle不import producer，逐个Python整数做完整K归约和RNE。

ZIP严格上限15MiB，内含：

- 两格式真实boundary2已提交状态及12步q/k/v/beta/decay、value单位；13个state/units/epoch边界和12个output/output-unit。
- boundary2的state SHA、units、epoch、version、position、sequence，以及全部attempt/abort/rescale/commit切片。
- 原输入/输出NPZ大小及SHA、完整原成员SHA、派生数组SHA及明确切片范围；原manifest与独立接收/chunk资格回执。
- 本collector与固定独立oracle源码，各产物SHA及ZIP统一索引。

接收验证包内全部SHA/大小、码域与完整维度、真实边界接续、未clip proposal、当前token触发guard、逐次RNE重编码、未提交副本、共同state/output/scale/epoch发布、两次实际重定标和全部事件成本。`--negative`实际改输出或epoch后重写NPZ、数组SHA及ZIP索引，确认SHA通过仍被独立数值语义拒绝；保留负例ZIP和收据。

边界2来自已审计fullrun，精选包不能独立证明省略的前两步如何产生它，也不重新核验原浮点编译/校准、余下242步、全256误差或真实硬件内存/端口/PPA。原全量数据留服务器和SHA索引。文件/数组SHA是软件完整性与来源链接，不是独立的真实性认证。
