# Issue 193 远程 RTL 验收

2026-11-06（Asia/Shanghai）。Slurm 作业数组 97923 使用 c64，四个分片各申请 10 核，分别在 node1、node2 和 node3 运行。实际仿真每实例使用 1 线程。Verilator 5.042（2025-11-02），Python 3.6.8。四个分片均为 `COMPLETED 0:0`，共 8 个场景通过。

| 分片 | 作业号 | 节点 | 用时 | 场景 |
| --- | ---: | --- | --- | --- |
| 97923_0 | 97925 | node1 | 11 秒 | C/U 正常、请求与确认背压、原生命令错误、背压叠加错误、待确认时协同复位 |
| 97923_1 | 97926 | node2 | 9 秒 | F 激活与逐元素 SRAM 写回 |
| 97923_2 | 97927 | node2 | 9 秒 | P feeder、两段 M、G 和 SRAM 写回 |
| 97923_3 | 97923 | node3 | 12 秒 | J 双支合并、输出背压、租约释放 |

C/U 使用真实 OpenRAM 银行数字模型。两条传输分别观察到目的 S 的写响应与源释放在同一握手周期发生。正常用例的周期是 1311 和 1752，背压用例是 1323 和 1774。协同复位后，两次有效交接出现在周期 2632 和 3083，首笔被阻塞的响应未被计为交接。故障场景验证了 C 结果地址的哨兵值及实际确认写入字节数。

- 输入提交 `e8351947ec6e9307c1d45fba7e13f551bb138e3b`。验收记录的后续提交只更新文档。
- 远程目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-193-local-control/acceptance-02/`。
- `bundle.tar.gz` SHA-256 `3387aa6f05f5fdd658e0ce326fce70fd694200c1882a4a5941c4fa6ddafea281`。
- `staged/sources.json` SHA-256 `e203596fa7459733732d77de231ec7611692bf7503d78dd64cb6fcd2366067b3`。四份 `source-sha256.txt` 均通过复核。银行模型 SHA-256 `6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7` 由各分片在编译前核对。
- 复现命令见 [RTL 回归入口](../../../project/control_native_v1/README.md)。首次 97913 的四个分片在 Python 3.6 镜像生成阶段因 `zip(strict=True)` 失败，保留在 `acceptance-01/`。修复后用新目录重跑完整数组。远程使用原版 N 源码。

| 日志 | SHA-256 |
| --- | --- |
| `results/97923-0/normal.log` | `945618370a9fe31cb0be97e3dbf803859ac2a6f6c8f68cfb3bf511734d6015dc` |
| `results/97923-0/stalled.log` | `793c1c0d4acf0f61e533760b9e0607c9353717bb16605053604fcbb2bed979ef` |
| `results/97923-0/fault.log` | `b8f1cd854db98e50595e13dd280d6575349865c8bbea1b8f552236dce616b90b` |
| `results/97923-0/stalled-fault.log` | `45440b662673a11eda845493b953ed24a153bb0156ba595360b895a912cb144d` |
| `results/97923-0/reset.log` | `1cc66ab2777647d94e4a37238a10f964de55492f5437e36e1b065b9835dbd275` |
| `results/97923-1/normal.log` | `701fa871004fadee6bd7087c578b13ffea1a41053b5396c4673ae710e848934e` |
| `results/97923-2/normal.log` | `d9681d14b559568ac1c1489981df84e74cf6385676b9d90878bf14b90fefe748` |
| `results/97923-3/normal.log` | `6d888fac34ec57414870748dad9a0121572035e66274e049cd3894b69ed09b48` |

范围为五类原生适配器和 C/U 固定双向单字链路的 RTL 验收。九实例顶层、父层布线和 300 MHz STA 分开验收。
