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
