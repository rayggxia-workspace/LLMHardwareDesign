# Qwen3.5-4B 两层 DMA 与计算 RTL 联调

复用 Issue #197 / PR #198 的检查点、冻结输出和 SystemC 外存驱动。选择完整的第 0 层 GDN 和第 3 层注意力，每层包含归一化、投影、状态或注意力计算、残差和 FFN。两层的边界输入从原完整模型前两个位置导出，按各自的缓存与状态连续执行。

`layer_dma.sv` 实例化 #182 的分组 DMA 和 16 KiB S。`native_engines.hpp` 将 M/N/E/G/R 命令送到原生 RTL，响应先与 SystemC 引擎比较，再供上层消费。R 采用 `WORDS=1024`。C++ 测试台组织命令、分片、尺度和内存模型。当前各宏和 DMA 独立推进时钟，结果用于功能及接口流量对账。

## 运行

在仓库执行 `python -B project/experiments/qwen_layer_dma/freeze.py OUT`，上传新生成的全部文件到全新的个人服务器任务目录。构建脚本复用服务器已有 #198 SystemC 源和原检查点，复制代码到新目录后应用局部适配，保留原输入。

```bash
sbatch --parsable --output="$ROOT/build-%j.log" "$ROOT/build.sbatch" "$ROOT"
# After a successful build.
sbatch --parsable --output="$ROOT/run-%j.log" "$ROOT/run.sbatch" "$ROOT"
```

原始隐藏状态 SHA 由 `prepare.py` 核对，生成两位置、两层输入与期望输出。两种执行使用同样的 16 字节元数据头和对齐尾字。成功运行输出 `layer-results.json`，分别核对完整层输出、各宏命令数、SystemC 字节数和 DMA 端成功应答的 128 位字数。详细报告和原始日志索引随 PR 保存。
