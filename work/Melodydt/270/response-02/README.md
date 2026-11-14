# ATT1 DDR 回包与 SRAM 确认解耦

2026-11-14（Asia/Shanghai），Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)，基于该 PR 的 `d1072b184cc2a90943da5d2be330a8bda0e89572`。沿用上一轮每行只读取所需 V beat 的地址序列。允许 8 笔 DDR 请求未返回，最多预留 16 个 64 B 响应数据槽。DDR 返回释放读额度，SRAM 最后一次写 ACK 释放相应数据槽。Dot 仍须等整个分片提交。RTL 候选的回包接口要求有序，依靠每个请求的 tag 检查返回，S128 写端最多两拍在途。需要为新增的 1 KiB 响应寄存数据及标签、控制付面积和时序成本。

## 原生 C380 对照

112668 和 112669 在 c64/node2 各用 8 核运行，两项均 `COMPLETED 0:0`，Verilator 5.042。上一轮原生串行读基线在该夹具复现。

| 模式 | 上一轮 RTL | 回包队列 RTL | 周期变化 |
| --- | ---: | ---: | ---: |
| 正常 | 163,454 | 85,495 | −47.69% |
| 背压 | 371,268 | 271,308 | −26.92% |

四次对照均为 9,120 个 KV 回包及 52,489 次 S 应答，逐字读回与冻结参考和对应基线一致。桥峰值在途从 1 到 8。读回 SHA-256 为 `994dc727df03121bf5cb902b630890ef3d6da48df3e762ca9987bd63dd85e3ee`。112668/112669 的 `proof.sha256` 文件 SHA-256 分别为 `ec677fa26e5caf0d403ff099fb6f9d0f5076aabd77be7fe7c5c7d936f8f8827b`、`d2b893f386952dca6060b1134f632ab6ead99ee5da58b578e80ec2828763ef1f`，全部成员校验通过。112662/112663 因按参数裁剪的分支标签告警退出，修正引用后保留 lint 门。未运行故障注入、完整系统 RTL、综合或 STA。

## 512-bit TLM

保留两个 630 ps DDR 通道、每通道 32 credit、3,334 ps 核周期、KV 窗口 8、基础流水与同一套输入。新旧的模型均允许 8 笔 DDR 在途，唯一变量是 DDR 额度释放时机与 16 个预留槽。原生 C380 对比覆盖从单笔到八笔及队列管理，不能直接换算成整段收益。

| 测试 | 上一轮前缀预估 | 本轮前缀预估 | 完整候选 |
| --- | ---: | ---: | --- |
| 两步 Decode | 2.455393940 tok/s | 2.455394664 tok/s | 112637 运行中 |
| 两位置短 Prefill | 5.507166863 输入 tok/s | 5.507166863 输入 tok/s | 112638 运行中 |

同程序和 DDR/SRAM 流量核对 84/126 页。Decode 第一步的前四层平均每层仅少 3,334 ps，外推 36 层少 0.120 μs。短 Prefill 第一个位置的前四层一致。上一轮完整窗口未结束，使用其前缀估计作为基点。回执见 [Decode](decode-prefix.json)、[Prefill](prefill-prefix.json)、[TLM 源清单](tlm-source.sha256)。后续完整候选与同配置基线都结束后再更新比较，以第二次词表退休间隔和第二个位置末残差为准。

## 复现、追踪和下一步

登录 `yuzelu@10.129.166.172`。项目工作目录 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-response-02`。先在上一轮封存的源副本应用集成补丁，并将 `s128_ddr_response_load.sv` 放到 `project/rtl/block_local_native/`。模型补丁施加在上一轮 TLM 源副本。可用本目录中的生成脚本重现并核对 [RTL 源清单](rtl-source.sha256)。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/att1-response-02/rtl-checked
exp=source/project/experiments/block_local_native/run_native_attention_core_scope.sh
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-cr0 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=1,DDR_RESPONSE_QUEUE=0 "$exp"
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-cr1 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=1,DDR_RESPONSE_QUEUE=1 "$exp"
cd ../tlm
sbatch --parsable --job-name=zny-att1-cdec run_att1_tlm.sbatch decode
sbatch --parsable --job-name=zny-att1-cpre run_att1_tlm.sbatch prefill
squeue -j 112559,112560,112637,112638
sacct -X -j 112559,112560,112637,112638,112668,112669 -o JobID,JobName,Partition,AllocCPUS,NodeList,State,ExitCode
tail -n 10 slurm-112637.out slurm-112638.out
for job in 112637 112638; do
  sha256sum -c "run-$job/output.sha256"
  cat "run-$job/timing-audit.json"
done
previous=/public/home/yuzelu/Melodydt/runs/issue-270/att1-selected-01/tlm
python3 -B ../compare_att1_response.py decode "$previous/run-112559" run-112637
python3 -B ../compare_att1_response.py prefill "$previous/run-112560" run-112638
```

后续处理人 Melodydt。恢复时先查询四个持久作业的退出状态和输出散列，核对 582/578 页、DDR/SRAM 流量和两次退休 token / 跨步 KV。下一项硬件候选在保留有限回包窗口的前提下，让多个已返回分片的 SRAM 写确认重叠，再测 S 读给 Dot 的共享端口。登记 PR #5 待合并，Projects 因缺 `config/board.json` 待具权限维护者核验同步。
