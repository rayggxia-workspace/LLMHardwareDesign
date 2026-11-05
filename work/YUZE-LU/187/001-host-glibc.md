# 001 · 启动失败与节点运行库

- 源 `6e11c17eff4d8c8c400a061d47fc5ec7abd5c501`。远程目录 `issue-187-p16-j16/001-6e11c17eff4d`，归档 `source.tar` 的 SHA-256 为 `36b45e206e74f26a7ffe5a618de181cb0b5277e14439367c4317670103fabbf5`。
- Windows 导出的提交脚本带 CRLF，首次 `sbatch` 在提交阶段拒绝。保留归档，执行 `tr -d '\r'` 得到 `run_rtl-lf.sh`，SHA-256 `1d75e2e2210abcef904a94c1c1193e51021b9689fb77c76f9d87bf1552c84fce`。
- 作业 97467 在 c96 node17 启动两个 12 核步骤。两者在 Verilator 5.042 装载时因节点宿主 glibc 缺 GLIBC_2.29 至 GLIBC_2.35 中的多个版本退出。用时 1 s，`sacct` 峰值列返回 0，无可用内存采样。
- `rtl/P.log` 与 `rtl/J.log` 同摘要 `0f116765adfcd686bfb11f902fb10729fb113cefc6009644d02c2f2c31219153`。改用现有容器，保留同一 HDL 和基准。