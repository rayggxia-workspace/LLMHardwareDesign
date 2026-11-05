# 020 · 隔离 P 命令与 J TX 组合长路

- 源 `6debe0b92`，归档摘要 `cb94c619d944483156713401cb9b832fde771a0c662d2dec53af7bfaa0a27855`。作业 97507，两块在一台 c96 上各 12 核构建，整轮 7 s。
- 018 的 P 最差 CTS setup 为外部 `cmd_op[1]→store`（−0.52 ns），J 为 `io_req_addr[12]→io_req_ready[1]`（−0.74 ns）。P 把原生命令暂存在发射槽。J 把 TX 地址和真实读响应暂存在租约绑定的保持槽，释放时等待槽为空。
- P/J RTL 通过。日志 SHA-256 分别为 `67cb3c697a48109c3d2c508223e5810a5e28a2251020461a73c0f550d37d30dd`、`62768c3db74e99b8684679f7904a829db6b19dd224e4ef7cbafe604e9e56a9f5`。CUGR 对照作业 97508，后继 97509。复跑脚本副本的 SHA-256 `4a0bb35507150fa5deffbb1e0ada454a84f6ac5406f20ef4134bd99b893efd3e`。
- 草稿 [PR #190](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/190) 以计划分支为基线，远端头 `a4d1cb0d38eab10edb68d93d6dcdf2cab133c4bd`，树与本地 `6debe0b92` 相同。