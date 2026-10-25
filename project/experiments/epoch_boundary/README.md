# 32bit epoch终止协议验证（Issue92）

阅读PROTOCOL.md及docs/experiments/issue-92-epoch-boundary.md。实际RTL唯一增量在project/rtl/runtime_cache/chain85.sv；baseline-chain85.sv保留85原Git blob，不能当修复版运行。

所有真实RTL/整数/综合/证明/完整接收只在本人授权CPU服务器Slurm。先核管理结构python -B scripts/check_project.py。执行源码必须从清洁commit冻结binding.json并逐源SHA匹配；运行目录应全新，不能覆盖已有结果。全部精确argv/容器/工具/资源见work/Liangruizhi/92/execution.json。

服务器冻结phase4下：boundary_run.py build --out NEW_BUILD；boundary_run.py sim --build NEW_BUILD --input IMMUTABLE_85_INPUT --out NEW_RUN --stall 0（另开新目录stall1）。原版本build/sim加--baseline，预期真实terminal discard失败。prove.py --out NEW_PROOF证明真实源门锥，加--baseline要求有效响应反例；二者不替代整核验证。正常60命令复用runtime_cache/run.py和verify.py，map相同配方。receive.py --root OWN_92_ROOT --out NEW_RECEIPT --library SAME_LIB严格接收正式阶段；本版按冻结phase4产物名绑定，迁移需保持相对布局并明确只读旧输入路径。

PC仅字节接收：

```text
python -B work/Liangruizhi/92/verify_delivery.py --index project/experiments/epoch_boundary/results/issue-92/delivery-index.json --archive project/experiments/epoch_boundary/results/issue-92/selected.zip --out NEW_D_RECEIPT.json
python -B work/Liangruizhi/92/verify_sources.py --repository REPO --index DELIVERY_INDEX --selected SELECTED_ZIP --expected-phases 5 --out NEW_D_SOURCE_RECEIPT.json
```

完整96.41MB含RTL/C++构建、原YosysJSON/抽锥、SAT/反例、全输出及失败；输入物理权重/激活另按索引读取旧84/85，无新模型。精选仅metadata/log与回执，不能据字节检查宣称数学/时序通过。
