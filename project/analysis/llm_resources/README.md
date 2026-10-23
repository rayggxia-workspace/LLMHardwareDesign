# ≤4B INT8资源估算器

正式[输入规范、示例和公式](../../../docs/LLM_RESOURCE_INPUT.md)，[Issue48](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/48)。
Python 3.10+标准库；无安装、权重下载、模型推理、服务器或EDA调用。

```powershell
python -B project/analysis/llm_resources/estimate.py project/analysis/llm_resources/examples/dense_4b.json
python -B -m unittest discover -s project/analysis/llm_resources -v
```

`schema.json`为输入合同；profiles是PR44固定候选JSON快照，原字节由测试绑定；examples保留真实配置尺寸与合成包络的区别。
可复制示例修改参数，候选路径相对该输入文件；在其他目录运行时用`--candidate <文件>`显式指定。
扩展/修改候选用新本地JSON并以`--candidate`选择，不覆盖固定快照。所有已知和未知参数都应如实标注。

报告status始终为部分解析估算；`scans`只缩放库存，`linear_target_violated=false`不代表完整模型或拓扑可行。
输入非法/已有输出文件返回2；有效输入即使有预算缺口仍返回0并列出缺口。`--output`只写新文件，省略时输出UTF-8 JSON。
输入/候选/源码/schema字节绑定及Git版本写入报告，不把本机预算计算称为硬件实测。
