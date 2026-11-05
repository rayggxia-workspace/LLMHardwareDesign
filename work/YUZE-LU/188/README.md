# U16/C16/F16 实施记录

[Issue #188](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/188) · [共同计划 #185](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/185) · [P16/J16 #187](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/187)。基线为 main `27eaaace1bc03cb4422954d1be343de556b757e3`，含 #186 已验收的 N4/N5 SRAM RTL 和物理索引。U/F 用 N4，C 用 N5，均为 16 KiB。

本轮交付三个 Block 共用的单命令存储客户端。客户端先抓取零至三个 128 位源字，再发运算请求，允许写回与源地址相同。运算错误禁止写回，正常存储命令须等真实 S 写响应才能完成。复位中止本客户端在途协议，集成时与叶宏、S 和对象 epoch 一起复位。测试在边界驱动存储及算术响应，用来验证协议。真实 N/E/G/R 和 SRAM 的集成回归及各 Block 的物理验收仍待进行。

## 2026-11-06 首次 RTL 事务回归

远程工作目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-188-ucf16/`。将 RTL、testbench 与 [smoke.sh](../../../project/experiments/block_ucf_v1/smoke.sh) 放到同一个新目录，从该目录执行 `sbatch --parsable smoke.sh`。冒烟作业用 debug 的 2 核；正式后端批次按独立案例与实际配额并发，c96 首选评估 8×12 核，并复核内存。

| 目录与作业号 | 证据和根因 | 修改与复验 |
| --- | --- | --- |
| smoke-01 / 97470 | Slurm FAILED 1:0。宿主缺 Verilator 5.042 所需 GLIBC_2.29/2.35 等版本，模拟未启动 | 保持 RTL 和测试不变，改用 ORFS 现有容器 |
| smoke-02 / 97472 | Slurm FAILED 127:0。node27 的批处理 PATH 没有 `singularity` | 从项目既有验收脚本确认共享 Singularity 绝对路径，切到 `SLURM_SUBMIT_DIR`，避免脚本 spool 路径 |
| smoke-03 / 97474 | Slurm COMPLETED 0:0。Verilator 5.042 编译并运行 | 三个读地址及操作数顺序、背压、写确认前禁止完成、错误不写回、复位清在途通过 |

输入和结果 SHA-256 如下。

| 工件 | SHA-256 |
| --- | --- |
| 97470 日志 | `94553f3121ecac64eda9fce597a3ba884c74bb98159c24f916e2c062817d6548` |
| 97472 日志 | `2b17169b70bf15e7661cc868954c79a6ff3445fd86cc4975d7df5d0c58a4d846` |
| 97474 日志 | `6220c1e89b6033767e9cd29af4b75a1d07b52f10aead82b760f33ea2c5558c82` |
| RTL | `8757f22b6cc03c11d2ac7aae873c2c2121d00e130bfab90ab6de7eca1e258cc` |
| testbench | `3e2aa47d2e1dd9a04961ed08e243299a6b54f4827bfe5989a7ccb936096037a2` |
| smoke-03 脚本 | `0536635d93fd97a6b1f3faa508216016e71b73612a44df2db9c9173d8e4bc9b0` |
| ORFS 容器 | `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a` |

下一步用正式 S 及算术叶宏替换测试边界，登记命令字段、数值合同、复位和物理端点。C 的 512 位原生响应与状态读写接口需单独适配。独立 M1–M10 验收覆盖实际 SRAM、M10 引出、PG、几何、连通、300 MHz 时序及电气。

## 2026-11-06 三块 RTL 与独立后端

U 实例为 N/E/S（四客户端），F 为 G/E/S（四客户端），C 为 R256/G/E/S（五客户端）。复用已验收 SRAM 银行及 S 控制 RTL；Block 的组合 RTL、物理实现与验收独立于叶宏。RTL 测试使用 #158 行为模型，不把行为模型当成版图证据。各运算命令仅在真实写响应后返回成功；块外地址保留和跨块 ACK 的释放由上层控制。

| 目录与作业号 | 证据和根因 | 修改与复验 |
| --- | --- | --- |
| rtl-01 / 97479 | 失败：原生 R 模块既有的位宽诊断被 Verilator 当作错误。日志 SHA-256 `c2749273c8599804ffc9e14c6a149c822adb07c9fbf45ef394533502a51a172c` | 保留原生 RTL，只对该模块限定两类位宽诊断；随后用非零状态算例复验 |
| rtl-02 / 97483 | 三种 Block 基础写入、E 运算与末地址回读通过。日志 SHA-256 `ce381afe2b79d0672b891b3d7aafcfc32ac3f6afbeca99341e220672ae6fd8c7` | 扩充叶宏测试 |
| rtl-03 / 97491 | U：Softmax 的累加/归一化、RMS、恒等旋转；F/C：SiLU 和带门控 Sigmoid；C：非零递推、old/next 独立、512 位结果四片回读。日志 SHA-256 `1487d1937083b1d0d025846c31a132922a8d23a0111854fc06de3c220ac8394e` | 三实例在实际 S RTL 与四个 SRAM 银行行为模型下完成回归 |
| pnr-01 / 97487 | 容器 Python 无 `hashlib.file_digest`；U1300 日志 SHA-256 `442ed49a33986e1f412aa71db411ebb052aacde53837914c3f9505606a3000ea` | 改为分段哈希 |
| pnr-02 / 97488 | 默认 ORFS 推断存储保护门限拒绝 N/G 运算查找表；U1300 日志 SHA-256 `c2f7a5b9b4415cc27a300da92c4536e0e3b0b24b9a8fac2a2356e75913da5f0d` | 先显式完成 Yosys 逻辑映射，再进 ORFS；断言只保留四个真实 SRAM 黑盒且无推断存储 |
| pnr-03 / 97490 | Yosys 层级检查要求 S 参数备用分支的源模块也可解析；U1300 日志 SHA-256 `c65450ce8d70b42b9e81eaa1d92649d5d97dd294286d989990dcb3f07ae9d2be` | 补齐 `block_feed_s16k.sv` 与 `block_feed_loader.sv`；实际映射依旧须通过四银行检查 |
| pnr-04 / 97493 | 八个物理候选已进入 Yosys 实际映射 | U、F 各试 1300/1450/1600 µm；C 试 1500/1800 µm；8 个独立任务 × 12 核，各自绑定 CPU |

独立物理验收还须分别检查最终 ODB 网表回归、GDS 完整规则集、原生 DRC、连通和 PG、M10 端点，以及 TT 300 MHz 提取后 STA 和电气。九实例底座属于后续验收。
