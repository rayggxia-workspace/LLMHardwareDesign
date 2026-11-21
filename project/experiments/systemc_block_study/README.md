# Block 内服务与搬运的 SystemC 架构实验

关联 [Issue #240](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/240) / [PR #241](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/241)。本目录是架构时序模型，不是 PR #220 映射器的新版本，不生成可部署的母控／局控程序，也不代替 RTL 或物理验收。结果及全部边界见 [研究回执](../../../work/YUZE-LU/240/RESULTS.md)。

保留独立宏、局控归属和 M1–M10 底座加 M11/M12 定制的方法；不把五类控制分组封成五种大硬块。本轮仅激活 P0、P1 和 U0，其他资源不参与计算。每组私有 S 始终为 16 KiB，没有跨组共享缓存。跨组结果显式经外存写回／读入，未假设存在免费直连。

输入分两种：完整 Qwen2.5-3B 的既有 B1/S2 prefill 整数算子 DAG，以及按 36 层、H2048、FFN11008、16 Q heads / 2 KV heads 构造的 decode 工作量图。后者包含真实大小的 KV 状态和每步写确认，但不是数值验收过的 KV 程序。两者的 token/s 必须分开。

## 模型具体计算什么

- SystemC 进程表示两个 M 服务、P 的双缓冲生产／消费和两个外存通道。每个请求等待真实建模的 ACK 后才能使用目的数据或释放槽位。
- 私有 S 的访问通过同一端口日历竞争；P 的两个操作数缓冲和 96 位累加工作区做容量检查。U 的 12 KiB 行缓存留出 4 KiB 工作区，并追踪脏数据、末次消费和外存有效性。
- 外存有有限 beat credit、32 个描述符 credit、bank/row、读写换向及传输时间。`queued_*` 允许描述符并行在途，其他配置逐描述符等 ACK。这个控制器是研究模型，未与 DDR RTL/VIP 或板卡校准。
- 原 M 的九种 R/K 执行延迟由同 SHA 的 `block_v2_m.sv` 测量；测试夹具中的 RTL 是未修改主线快照。未来 S32 M、E32 服务及宽 S 端口仍用明确假设，不能继承旧宏的 TT 300 MHz 验收。
- `stream_p*` 建模 A256/B512 接口、全 K 的 96 位累加和宏内流水；`*_resident` 在确实装得下时保留输入，并同时缩小 K 分片。`queued_pipe*` 再加入有限 DMA 排队和 E32 的 II=1、延迟 6、16 个 packet 上下文。
- `w8` 只改变静态矩阵权重的传输宽度；激活／KV 仍是 S32。它是量化假设，未执行新权重量化或 HF 精度验收。W16 对照不能省略。

decode 的 SiLU、RoPE、倒数是有计数的候选微程序。SiLU 用 41 个四通道微操作预算；倒数用 128 个预算。数值系数尚未验收。运行时 View 显式计搬运，但只按形状建模，不声称已实现所有转置索引。N 的部分服务延迟是保守假设。本模型不计算实际张量数值。

## 复现

需要 C++17 的 GCC、SystemC 3.0.2、Python 3.9+；M 测量还需 Verilator 5.042。所有命令在**新建的实验目录**运行。不要复用其他任务的输出目录。

```bash
# Copy this directory into NEW_RUN; use relative SystemC paths on Windows.
cd NEW_RUN
g++ -std=c++17 -O2 -Wall -Wextra -Werror model.cpp -ISYSTEMC_PREFIX/include -LSYSTEMC_PREFIX/lib -lsystemc -o model
g++ -std=c++17 -O2 -Wall -Wextra -Werror kernel_probe.cpp -o kernel_probe
# 将 work/YUZE-LU/240/inputs/*.trace 及 input.json 复制到 NEW_RUN/generated/
# 将已提交的 evidence/native/m-profile.log 复制到 NEW_RUN/m-profile.log
export BLOCK_STUDY_MODEL="$PWD/model"
python -B check_kernels.py
python -B validate.py
python -B smoke.py
python -B sweep.py --workers 4
python -B audit_results.py
```

Windows 可将 `BLOCK_STUDY_MODEL` 指向 `model.exe`。`--candidate-only` 跳过依赖旧 M 实测表的配置。服务器上的 `run.sbatch` 给出容器、编译和原生 M 测量的完整命令；按实际软件路径设置环境，遵守 `docs/REMOTE_RULES.md`，不能在登录节点跑整模型。冻结原始 IR 很大，不纳入 Git；已有 trace 足以重跑计时。需要重新提取时执行 `extract.py --source FROZEN_IR`，并核对研究回执中的原始 SHA。

`check_kernels.py` 验证分解、宽累加、RNE 和饱和；`validate.py` 检查有限队列、驻留切换、KV ACK 和缺失生产者的负向案例；`audit_results.py` 独立检查矩阵工作量、权重流量下界、分片数和容量。它们不构成完整图的数值交叉验证。能耗没有标定参数，本轮只提供工作量／搬运计数，不给出焦耳或瓦特。
