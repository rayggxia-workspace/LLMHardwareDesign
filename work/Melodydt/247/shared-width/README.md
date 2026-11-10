# 共享32KiB扩宽评估证据

用途：Issue247 / PR243、Melodydt，记录原条件体系prefill2/W8中16/32/64/128B A入口和单/双组服务的实际评估。

报告：docs/experiments/issue-247-prefill-width-evaluation.md。analysis.json是源结果的可复核后处理，独立复核见independent-review.json。run33目录保留源码/输入/全部输出SHA、调度日志和回收回执。

完整result.json（3.59MB）、事件JSONL、生成模型和二进制保留于授权服务器/public/home/yuzelu/Melodydt/issue247-area-speed/run33/results；本地完整回收位于外层work/Melodydt/247/run33/receipts。仓库保存索引及分析，不宣称原始全包已上传。完整结果SHA e2887d8b137c7c4ca69d442586b26ac711427abf9ff26e5072a1a7115093de9b；归档SHA f858ad316e9a5522a80c8d20cc0efa663609f0d267a21b11aa473e25765d1205。

固定32KiB容量，生产RTL未扩宽；SystemC条件模型最高4.429583 token/s，不能作为原生整图RTL实测速率。共享池宏增量0，新的控制/互连/并行写入面积和物理频率未测。
