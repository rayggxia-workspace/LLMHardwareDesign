# Qwen FFN 两通道综合实验

作用域为 Qwen3.5-4B 第 0 层 gate、up 和 Mid，H2560，输入为带种子的合成 post-RMS 激活。每次试验选择两个输出通道。两个 P16 绑定的执行模型、可综合试验 MC/LC 和传输器读取同一套编译输入。原生 P16 服务的测试适配器由仿真驱动。镜像为本实验格式，独立于 PR #180。

## 数据和运行

1. 固定 PR #190 的 P16 RTL，并把 `27eaaace1` 的 `project/rtl/block_local_s` 与 `project/rtl/s_sram` 放入同一暂存树。真实权重可使用项目既有检查点，或用 `fetch_weight_rows.py` 从固定 revision 提取少量行。
2. 使用 `python3 -B test_optimizer.py` 检查优化和反馈协议。用 `compile_slice.py manifest.json mapping.json` 选择估计代价较低的方案，再运行 `images.py mapping.json images`。比较实验可用 `--up-owner 0` 或 `--up-owner 1` 强制选指定方案。
3. 远端用 `sbatch run_native.sh REPO OUT CHECKPOINT SYSTEMC_ROOT` 执行。SYSTEMC_ROOT 是包含 `include/systemc` 与 `lib/x86_64-linux-gnu/libsystemc.so` 的任务专用工具目录。单次编译用 10 核，随后 6 个单线程案例并发。输出含逐案例、逐映射日志与 SHA-256。
4. 布线用 `sbatch run_coupon.sh REPO OUT ACCEPTED_P16_TAR OVERLAY GAP`。以两个间隔分别提交 10 核作业。OVERLAY 为已核验的上层技术 LEF 与轨道设置目录。试验输出只覆盖数据线，对控制、完整几何连通、电气和时序需另做核验。
5. `route_feedback.py` 将同一候选底座真实路由 DEF 的上层网覆盖转为软罚项。首次实验以每条缺覆盖网 1,000 个周期当量量化。罚项是估计权重。报告保留原始 DRT 结果及映射前后的程序和连线，区分代价改变与硬约束冲突。

可查证的实验记录见 `work/YUZE-LU/192/ITERATIONS.md`。
