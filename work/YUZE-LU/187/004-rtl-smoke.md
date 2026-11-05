# 004 · P/J 首轮 RTL 功能通过

- 源归档和 003 容器脚本保持原 SHA-256。运行 `sbatch -o "$attempt/slurm-%j.log" "$shared/run_rtl.sh" "$source" "$qualified/source" "$attempt/rtl"`。其中 `source` 为 001 目录本身，`qualified` 为 `local-s-sram-qualification-20261105-01`。
- c96 作业 97471 总用时 7 s，两个 12 核构建步骤及两个 1 核运行步骤全部完成。Slurm 未提供有效峰值，Verilator 报告的分配量分别为 P 86.523 MB、J 63.523 MB，模拟进程各约 6 MB。这些工具统计与进程 RSS 不同。
- P 通过 feeder、两段 K、最终格式化写回、非法命令和 SiLU 门乘。P 日志 SHA-256 `be44f33d08865056ba05d63c80b9d5c06dbaf5649b77d3bbe4eca72a9ef72a60`。
- J 通过标签错配拒绝、加法饱和、SRAM 写回和背压下的 T 租约。J 日志 SHA-256 `aa09660c73e96b296be2b0ba19f6a211e10320ff75f9d5ff7e9ca60d0c9fe3e4`。
- `004-path/rtl/{P,J}.log` 是可复核的输出。银行采用数字功能模型。此轮范围为首轮功能路径。完整描述符身份、三路汇合、M10 候选和独立物理门继续实施。