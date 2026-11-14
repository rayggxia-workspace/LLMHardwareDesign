# #270 ATT1 KV 回填第一轮

关联 [Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) 和 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260)。Melodydt，2026-11-14（Asia/Shanghai）。任务分支 `task/270-qwen-rtl-throughput`，基点 `55620f173f2ad540efade8a552c35e9dba0f43c0`。这次提交保留现有独立原生集成树的补丁和对应 TLM 补丁。

原生候选对 AV 逐分片启动。每行只发含当前输出小组的一个 64 B V beat，沿用 512 B 行步长和 32 B SRAM 写入。保留已验的两笔 S 写在途、同址标签和最终 ACK。K 仍用原路径。TLM 补丁以 110382/110383 的基础流水源码为基准，只更改 V 的取数地址和请求数。它保留原有分片搬算重叠；原生补丁的分片内 DDR 请求仍为单笔。这两套证据分别报告。

## 原生对照

Verilator 5.042、C380、真实 S128、封存 MC/LC、定点 Attention 参考数据。112602 和 112603 在 c64/node1 各 8 核完成，退出 0:0。逐字读回匹配冻结参考，两版再逐字互比。SRAM 应答均为 52,489，KV 回包为 15,200→9,120。正常模式 227,431→163,454 拍（−28.13%），施加背压 436,458→371,268 拍（−14.94%）。

- 112557/112558 因启动参数含多余字符退出；112572/112573 和 112585/112586 因测试台地址表达式宽度告警退出。最终版本保留原 lint 门。
- 封存 source.tar SHA-256 `8a1e2de3e43b195e596fd0f2ecf3fa1fc340104a65ae4c83d373e52b9f5e0c43`，algo1.tar SHA-256 `ec585fca81b4f97600175570e52b854f8a69e0d6789319735767248c56123a5a`。见 [RTL 源清单](rtl-source.sha256)。
- 原生 `proof.sha256` 文件的 SHA-256 为 `ce4f9c898d8a4809ef99a7c130a1cf0938b588b4992bb9744ff43f349b4d58a0`（基线）和 `bf3eb36d05f575ec71b74b3ef51ad0602cbea04340c26a7a8f91fa38ea9f5bb0`（候选）。两模式读回文件 SHA-256 均为 `994dc727df03121bf5cb902b630890ef3d6da48df3e762ca9987bd63dd85e3ee`。

## 短程吞吐

同一部署及输入，512-bit S，3,334 ps 核时钟，双通道 630 ps DDR，每通道 32 credit，KV 窗口 8，并保留基础流水。Decode 从已有 512 个位置的 KV 开始，按两次词表退休间隔计。短 Prefill 从空 KV 开始，按两个位置到末残差完成计。批量 DDR 执行器沿用 #265 已逐页验证的实现。

| 项目 | 封存基线 | 前四个 Attention 页外推 | 完整候选 |
| --- | ---: | ---: | --- |
| 两步 Decode | 2.338997 tok/s | 2.455394 tok/s，+4.98% | 112559 正在运行 |
| 两位置短 Prefill | 5.506517 输入 tok/s | 5.507167 输入 tok/s，约 +0.012% | 112560 正在运行 |

前缀匹配了实际程序页、母控周期、服务调用和写笔数，并核对 DDR 读笔数仅在 ATT1 页按预期下降。Decode 先取第一个缓存阶段每层减少约 0.563 ms 外推 36 层，再核对第二阶段；Prefill 先用第一个位置的前四层，第二位置可见后更新。前缀与模型估计见 [Decode](decode-prefix.json) 和 [Prefill](prefill-prefix.json)。整段候选通过原审计且两次退休 token 与跨步 KV 统计匹配之后，才更新为实际短程 TLM 吞吐。

## 复现与接续

远端 `yuzelu@10.129.166.172`。目录 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-selected-01`。源码/启动脚本及输出都留在本任务目录。补丁可在对应封存源副本上用 `git apply --check` 和 `git apply` 应用。生成工具 `prepare_att1_selected.py` 从同一来源生成两个补丁并检查替换点。服务器 `publish` 留前缀结果及补丁。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/att1-selected-01
cd rtl-clean
exp=source/project/experiments/block_local_native/run_native_attention_core_scope.sh
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-r0 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=0 "$exp"
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-r1 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=1 "$exp"
cd ../tlm
sbatch --parsable --job-name=zny-att1-dec run_att1_tlm.sbatch decode
sbatch --parsable --job-name=zny-att1-pre run_att1_tlm.sbatch prefill
squeue -j 112559,112560,112602,112603
sacct -X -j 112559,112560,112602,112603 -o JobID,JobName,Partition,AllocCPUS,NodeList,State,ExitCode
tail -n 10 slurm-112559.out slurm-112560.out
ref=/public/home/yuzelu/project-circuit/issue260-sram-pipeline-qk3uTFl1
python3 -B ../compare_att1_selected.py decode "$ref/run-110382" run-112559
python3 -B ../compare_att1_selected.py prefill "$ref/run-110383" run-112560
sha256sum -c run-112559/output.sha256
sha256sum -c run-112560/output.sha256
```

由 Melodydt 恢复读取两项 TLM 的退出、输出散列和完整审计。ATT1 下一小步是分离回包信用和最后 S 写 ACK，对照同流量的 S 回填/读出流水；随后测 C639 和故障排空。完整 P512/D128 及物理验收仍待执行。项目登记 PR #5 待合并。Projects 缺 `config/board.json`，待具权限维护者核验条目与同步。
