# 006 · 分层导入首次失败

- 远程 `006-physical-trial` 的 `source.sha256` SHA-256 为 `5668edb7b176f07e3d7c1f524e41edd397e4d9a52f526e37f9d2711e49597fbc`。RTL 为首轮 004 的版本。使用 005 六份试装视图及原 Nangate45 库。
- `run_physical.sh <source> <005-leaf-views> <pnr>` 作业 97475，c96 一节点 P/J 同时各 12 核，6 s 失败。
- Yosys 已读到三个叶单元，OpenDB 随后报告 `library (leaf) already exists` 与门乘或残差 master 缺失。各 LEF 文件名都是 `leaf.lef`，OpenDB 从 basename 得到同一个库名。改用唯一的软链接文件名，实际视图内容与 GDS 保持字节级一致。
- P/J 综合日志摘要分别为 `2f6e9e815ab059af1d491db496240b992b5ef7dcd5cb9d2955ca457e4361fd3b`、`65267cbba346f2c3462f3338848b62435a291db819c5efce4d790e8d9aed3558`。日志中的导入峰值 P 228532 KiB、J 156092 KiB。