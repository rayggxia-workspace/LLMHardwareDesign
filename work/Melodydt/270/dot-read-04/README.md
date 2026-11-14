# ATT1 双窗口回填与 Dot 读出

2026-11-14（Asia/Shanghai），Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。分支 `task/270-qwen-rtl-throughput`，基点 `c2d14050c66d3e479952ae9b88a4c30bf6f33ccb`。

## 原生验证

C380 A/B 固定 16 KiB SRAM、一个请求端口及两个有序应答位置。原工作区分成两个各 128 个 S128 字的窗口，QK 分片 4 行、AV 分片 64 行。候选在当前 Dot 分片期间向另一窗口回填，轮转仲裁保留已呈现请求，按 FIFO 归属分发应答。Dot 切换前等待下一窗口最后一次写 ACK。

| C380 工况 | 同分片串行，113104 | 双窗口重叠，113105 | 周期变化 |
|---|---:|---:|---:|
| 正常 | 75,877 | 65,932 | −13.11% |
| 背压 | 282,528 | 279,968 | −0.91% |

两项均在 c64/node1 以 8 核运行 Verilator 5.042，退出 0:0。均为 9,120 个 KV 回包、54,087 次 SRAM 应答，读回与冻结参考及相互逐字一致。候选正常模式重叠 46,408 拍，期间回填和 Dot 请求分别等待 21,488 / 21,565 拍。背压模式重叠 224,640 拍，等待 198,157 / 199,297 拍。两个等待计数可同时增长。

与第三轮较大分片候选 67,242 / 271,308 拍直接比较，本轮正常减少 1.95%，背压增加 3.19%。跨分片比较同时计入额外的 Dot 分片和 1,598 次 SRAM 应答。

原生基线/候选 `proof.sha256` 文件的 SHA-256 分别为 `b47e6882f3979e7ec8fb8ee3022a680f4780c2568446e298a5b52ddc00905c2b` 和 `119baaf8844f16990ec957308874c0b32f411a3ae35b42302dcc877d28ebff3d`。两模式候选读回 SHA-256 均为 `994dc727df03121bf5cb902b630890ef3d6da48df3e762ca9987bd63dd85e3ee`。[RTL 源清单](rtl-source.sha256)。本轮共享端口故障注入及 STA 待执行。

## 512-bit TLM

第三轮模型已有两个半窗口和搬算重叠。本轮对模型单独开放 QK/AV Dot 操作数读两笔在途。Softmax 读写节拍沿用基线。固定相同程序、权重、KV 输入、512-bit S、3,334 ps 核周期、双通道 630 ps DDR、每通道 32 credit、ATT1 窗口 8、16 个响应槽和四块回填。对账程序、控制发射及 DDR/SRAM 事务和字节。TLM 用已有 S 端口预约规则，RTL 用实际请求/ACK 及轮转仲裁。

| 阶段 | 两步 Decode（tok/s） | 两位置短 Prefill（输入 tok/s） |
|---|---:|---:|
| 第三轮前四层外推 | 2.609134315 | 5.502847775 |
| 本轮前四层外推 | 2.739536158 | 5.504622886 |
| 增量 | +5.00% | +0.032% |

Decode 前四个 ATT1 页平均缩短 0.506766 ms，外推 36 层省 18.243588 ms。短 Prefill 暂使用第一个位置前四层。第三轮 112976/112977 与本轮 113070/113071 的整段结果待对照，当前外推采用第三轮预估窗口。[Decode 前缀](decode-prefix.json) · [Prefill 前缀](prefill-prefix.json) · [TLM 源清单](tlm-source.sha256)。

上游 PR #260 的 112069/112070 已完成，其独立结果为 3.007297 tok/s / 6.652582 输入 tok/s，运行包含另一份 FFN 权重取数配置。保留作后续 FFN 对照证据。

## 作业与接续

服务器 `yuzelu@10.129.166.172`，隔离目录 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-dot-read-04`。补丁针对第三轮封存 RTL 和 TLM。启动及审计命令如下。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/att1-dot-read-04/rtl
exp=source/project/experiments/block_local_native/run_native_attention_core_scope.sh
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-dr0 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=1,DDR_RESPONSE_QUEUE=1,OVERLAP_REFILL=1,HALF_TILE=1,OVERLAP_DOT=0 "$exp"
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-dr1 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=1,DDR_RESPONSE_QUEUE=1,OVERLAP_REFILL=1,HALF_TILE=1,OVERLAP_DOT=1 "$exp"
cd ../tlm
sbatch --parsable --job-name=zny-att1-rdec run_att1_tlm.sbatch decode
sbatch --parsable --job-name=zny-att1-rpre run_att1_tlm.sbatch prefill
squeue -j 112976,112977,113070,113071
sacct -X -j 112976,112977,113070,113071,113104,113105 -o JobID,JobName,Partition,AllocCPUS,NodeList,State,ExitCode
tail -n 10 slurm-113070.out slurm-113071.out
prev=/public/home/yuzelu/Melodydt/runs/issue-270/att1-refill-03/tlm-final
for j in 112976 112977; do (cd "$prev" && sha256sum -c "run-$j/output.sha256" && cat "run-$j/timing-audit.json"); done
for j in 113070 113071; do sha256sum -c "run-$j/output.sha256"; cat "run-$j/timing-audit.json"; done
audit=/public/home/yuzelu/Melodydt/runs/issue-270/att1-response-02/compare_att1_response.py
python3 -B "$audit" decode "$prev/run-112976" run-113070
python3 -B "$audit" prefill "$prev/run-112977" run-113071
```

Melodydt 接续先验四项 582/578 页、退出码、退休 token、跨步 KV、散列和外推误差。ATT1 正常与背压结果均须作为配置取舍依据。之后在相同工作负载上进入 FFN 权重供数对照。项目管理检查通过，完整 P512/D128 与物理时序未执行。登记 PR #5 待合并，Projects 因缺配置由具权限维护者核验同步，独立审查人待指定。
