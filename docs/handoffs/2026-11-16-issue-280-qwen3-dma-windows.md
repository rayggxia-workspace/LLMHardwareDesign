# Issue #280 Qwen3 DMA 三窗口补采

2026-11-16（Asia/Shanghai）。仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 `llm-hardware-design`，负责人 Melodydt，分支 `task/280-seven-model-energy`。当前线上草稿 PR HEAD 为 `91812f2891ba9ec563fb5a41aff71920129fe761`。冻结回放来源为 DDR 试点脚本提交 `ac2a7265d4510e0fc73164a83ebb5355da586a88` 和作业 116481 的两个成功阶段。新探针文件在 Windows 管理目录和服务器提交目录，按真实文件 SHA-256 标识。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [冻结 DDR 回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/049bd82218920e0b3786dfc9dfc7a0ed3534d3b5/work/Melodydt/280/QWEN3_DDR_PILOT.md)

## 时限读回

c64 和 c96 的分区时限为 `infinite`。对已运行的两项本人任务实际执行 `scontrol update JobId=<ID> TimeLimit=UNLIMITED`，Slurm 对两项均返回 `Access/permission denied`（退出码 1）。

| 作业 | 启动节点 | 截止时间（北京时间） | 读回时限 |
| --- | --- | --- | --- |
| 117939 `mdt-280dma300` | c96/node17 | 2026-11-16 18:25:15 | 04:30:00 |
| 117729 `mdt-280mgate` | c96/node15 | 2026-11-16 17:32:20 | 06:00:00 |

上表为取消前的时限读回。按用户随后指示执行 `scancel 117939` 和 `scancel 117729`，`sacct -X` 确认两项均于北京时间 2026-11-16 15:17:54 进入 `CANCELLED`。新补采作业 118132 使用 `--time=0`，取消后读回仍为 `PENDING (Priority)`、`UNLIMITED`。

| 作业 | 运行时长 | 中止点和功耗用途 |
| --- | --- | --- |
| 117939 | 01:22:39 | 停在 Yosys 综合。计划为共享 DMA fabric `mc_dma_fabric_typed_p` 生成 300 MHz 约束下的网表和布线寄生，并用冻结 C639 端口活动做内部传播，标定共享 DMA 动态和漏电。未取得最终物理工件及功耗回执。源码 `91812f2891ba9ec563fb5a41aff71920129fe761`。 |
| 117729 | 03:45:34 | 停在 M 门级回放准备／构建之后且回放完成前。计划复用 116976 的已布线 M 网表和寄生，在 C639 回放中采真实门级活动，标定三路 M 在不同 FFN 阶段及背压下的功耗。未取得完整门级波形和功耗回执。源码 `6c031ed93ef9a97bf442d4a9e2c1f9ae23a46c18`。 |

执行目录位于 `/public/home/yuzelu/Melodydt/runs/issue-280`。下列文件以该目录为基准，取消后读回 SHA-256。已复核 `qwen3-non-dma-subtotal-01/results.sha256`；已覆盖小计为 DDR 芯片及 G32 活跃增量。现有 M 局部端口活动估值 268.51–272.19 mW/路，仍需逐路的整窗活跃／空闲驻留才能用于估算。

```text
  8fb2b2b5e892099347cb16128bb07fd4aebf4c0defbd6064baf761b1562ec4d5  c639-dma-power-300-01/slurm-117939.log
  f0b7c954c42f82c394b5432b447e883f80d1a886644f74afb0d523fbe29374aa  c639-dma-power-300-01/result-117939/flow.log
  2b7dc2224182e25bb4375b20f4d410990964480336c93241b544e7e767c95e79  c639-m-gate-300-02/slurm-117729.log
  1bd9dde9f127eae7a604612a55fda85bebfe255a962c8060b5f94fe117846053  c639-m-gate-300-02/result-117729/runner.log
```

## 新作业 118132

登录 `yuzelu@10.129.166.172`，提交目录 `/public/home/yuzelu/Melodydt/runs/issue-280/qwen3-dma-windows-01`。作业名 `mdt-280dmawin`，请求 c64/c96 一节点、2×12 核。提交命令 `sbatch --parsable --time=0 run_qwen3_dma_windows.sbatch`。日志 `slurm-118132.log`，成果写入 `result-118132/`。15:11:09 读回 `PENDING (Priority)`，节点待分配。`squeue --start` 当时预估北京时间 2026-11-23 06:56:21，随调度变化。

- Bash/Python 语法通过，C++ 探针使用实际容器以 `-std=c++17 -Wall -Wextra -Werror -fsyntax-only` 检查通过。启动前固定冻结桥、DDR 库、原两份全层结果、每分窗快照以及逐层记录 SHA-256。
- 继续使用相同的 Qwen3 W8A16、28 层、三 P、512-bit SRAM、3,334 ps 核周期、双通道和真实 512 位置历史。探针独立累积 DRAMsim3 边界每通道的 DMA 提交、接受和读／写回调，带边界队列数和在途数，以及队列／在途的拍数量时间积分。记录 DDR tick 上的无／单／双通道在途和 throttling、credit、设备背压等待。
- 验收要求 prefill、首 token、两退休间 decode 均逐窗对账。新旧 TLM result、逐层散列记录、DDR 快照字段和退休完全一致。每通道每方向的提交、接受、完成及边界积压守恒。结果标为 TLM 传输观测。片上 DMA 客户端 6,144-bit 回包输出翻转及 RTL 内部活动需额外波形。
- 提交清单文件 SHA-256 `58375263f34793ba25740b3ca2f032685018630f848f1a4d6ea6957abf8d0bd8`，入口脚本 `3c68d74decdfe94dd10a7c5dbca058793c849b4db8bf871bc8574ac3d3a1739d`，探针 `9ef494bbdb4cccf569943183bac0d6c3cdcf7ae9078ddcb5b268670d5f9f991e`，生成的预检桥 `b222185e1797d57c04347adea53cf11c31802653aef4bcf36e29cb22d839fce8`。

```bash
ssh yuzelu@10.129.166.172
cd /public/home/yuzelu/Melodydt/runs/issue-280/qwen3-dma-windows-01
squeue -j 118132,117939,117729 -o '%i|%j|%T|%P|%N|%M|%l|%R'
squeue --start -j 118132 -o '%i|%T|%S|%R'
sacct -j 118132,117939,117729 -o JobID,JobName,State,ExitCode,Elapsed,Timelimit,NodeList
sha256sum -c archived-ddr-completions.sha256
tail -n 25 slurm-118132.log
tail -n 25 result-118132/replay-launch.log
(cd result-118132 && sha256sum -c results.sha256 && cat dma-windows.json)
```

## 冻结快照中的 DDR 事务完成数

已在服务器提交目录写入 `archived-ddr-completions.json`，并通过 `archived-ddr-completions.sha256` 核验。仓库 [计数 JSON](../../work/Melodydt/280/qwen3_ddr_archived_completions.json) 对应文件 SHA-256 `77385ab843b4bbc07d04dafd631e1d28f2f134d6facf800b81da7a309a9cb7a7`。表中为 DRAMsim3 两通道合计，分别取短 prefill 结束前累计、首 token 退休前累计、两次退休之间增量。片上 DMA 提交、接收、在途和等待仍需补采作业。

| 窗口 | DDR 读完成 | DDR 写完成 |
| --- | ---: | ---: |
| 短 prefill（2 tokens） | 14,782,150 | 17,920 |
| 首 token（已有 KV） | 13,794,813 | 8,960 |
| 稳态 decode（第 1 至第 2 次退休） | 13,801,957 | 8,960 |

## 2026-11-16 15:24（Asia/Shanghai）同步前读回

- 118132 仍为 `PENDING (Priority)`、`UNLIMITED`，节点待分配。再启动前先核对封存包及冻结来源，不从归档的 DDR 器件计数推断片上 DMA 的提交和等待。
- 117940（C639 局控取指）在 c64/node1 运行 1 分 04 秒，`FAILED 2:0`。OpenROAD 修复 hold 时达到缓冲器上限，未出功耗。查看 `c639-lc-fetch-power-300-01/result-117940/flow.log`，SHA-256 `7316ea14fced18a1e1c2ccf46eff82e565ba8cb758e72b88dabb74a2e52f8c33`。
- 117855（M ECO）在 c64/node1 运行 1 小时 03 分 28 秒，`FAILED 2:0`。已形成重布线数据库和候选网表，最终报告阶段的 Kepler 等价检查异常退出。等价及最终提取时序尚未验收。查看 `c639-m-grt-eco-03/result-117855/finish.log`，SHA-256 `1d7c9ef8e5248e0a6106c581cfd937d6276f8c374f1a167d110824fc63739bcd`。

## 剩余步骤

1. 读回 118132 实际节点与终态，核验散列和三窗计数，并逐窗汇报。
2. 取得共享读 DMA、阶段切换及 512-bit 写回的同源网表及物理工件。补 6,144-bit 返回活动，标定空闲、正常、背压与并发窗口。
3. 将 DMA、其余片上分项和 DDR 芯片在三个同一窗口合并，之后扩至其他模型。PHY 与板级另计。

项目管理结构检查通过。规则 rayggxia-project-collab 1.0.0。账号 Melodydt 已核验仓库写权限。草稿 PR #281 待审查，登记 PR #5 待合并。项目未配置专属 Projects 看板，组织总览的 #280 条目待管理员核验。Slurm 作业通过服务器持久排队，可用上述命令复查。
