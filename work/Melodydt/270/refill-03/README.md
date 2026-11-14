# ATT1 SRAM 多块回填

2026-11-14（Asia/Shanghai），Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) / [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。基点 `af29d7a5199095d63d3411245bb0e79ebb7366a0`。本轮保留 V 选择读取、8 笔 DDR 未返回和 16 个响应数据槽。原生 S128 仍限制两笔 SRAM 写在途，分开跟踪已发写的块和收到最后 ACK 的块，以便跨块连续发写。512-bit TLM 允许四个已回包块提交写入同一个 S 端口。两者保留整片最后 ACK 后再交给 Dot，当前 ATT1 读口和整体物理时序待另测。

## 吞吐

| 阶段 | 两步 Decode（tok/s） | 两位置短 Prefill（输入 tok/s） | 口径 |
|---|---:|---:|---|
| V 选择读取，112559/112560 | 2.456194082 | 5.502011970 | 完整 TLM |
| DDR 回包与写确认解耦，112637/112638 | 2.455285523 | 5.502011970 | 完整 TLM |
| 多块回填，112976/112977 | 2.609134315 | 5.502847775 | 前四层外推 |

前四个 Decode ATT1 页平均减少 0.667103 ms/层，按上轮完整两次退休间隔 407.284607 ms 外推至 383.268885 ms（吞吐 +6.27%）。短 Prefill 暂复用第一个位置的前四层差值，约 +0.015%。[Decode 逐页](decode-prefix.json) · [Prefill 逐页](prefill-prefix.json)。TLM 固定 512-bit S、3,334 ps 核周期、双通道 630 ps DDR、每通道 32 credit。四个前序作业终态均为 0:0，582/578 页审计和输出 SHA-256 全通过。回包解耦轮的两次退休 token、跨步 KV 与 V 选择读取轮一致，Prefill 计时完全一致。先前记录的前缀外推对最终候选的误差分别约为 V 选择读取 Decode −0.033%、回包解耦 Decode +0.004%、两轮 Prefill +0.094%。

## 原生对照和故障排空

- 112990/112991 在 c64/node1 各 8 核用 Verilator 5.042 完成，均为 0:0。C380 正常 85,495→67,242 拍（−21.35%），背压 271,308 拍持平。两模式仍为 9,120 个 KV 回包、52,489 次 SRAM 应答，读回逐字一致且匹配冻结参考。读回 SHA-256 `994dc727df03121bf5cb902b630890ef3d6da48df3e762ca9987bd63dd85e3ee`。
- 113009 在 c64/node1、2 核完成 0:0。定向回归覆盖正常、错误 DDR tag、错误 SRAM ACK tag，每组均排空 40 个 DDR 回包，SRAM ACK 分别 80、78、80，错误请求回报失败。113002 为测试台 lint，113006 为解除复位同拍采样竞争，均已修正。
- A/B 的 `proof.sha256` 文件 SHA-256 为 `f482bd89557ae46af908c59b2be66d7a539983074e38f74d7a294aefd0bf0b9c` / `d4ff982f9da34db584ed22caf133301f2b6768a1e076cd96df23322ad20f3dcc`；故障 `output.sha256` 文件 SHA-256 `7eacfcf69d5981d918f36abaf5a047ead20bdae4a649350f7976a8009cceed16`。散列成员校验通过。[RTL 源清单](rtl-source.sha256) · [TLM 源清单](tlm-source.sha256)。

## 复现与接续

服务器 `yuzelu@10.129.166.172`，源码与结果目录 `/public/home/yuzelu/Melodydt/runs/issue-270/att1-refill-03`。在 #270 第二轮对应封存副本应用本目录补丁。RTL 测试用到未改动的只读封存源。测试清单与启动命令如下。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/att1-refill-03/rtl-min
exp=source/project/experiments/block_local_native/run_native_attention_core_scope.sh
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-wr0 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=1,DDR_RESPONSE_QUEUE=1,OVERLAP_REFILL=0 "$exp"
sbatch --parsable --partition=c64,c96 --time=00:12:00 --job-name=zny-att1-wr1 --output=slurm-%j.out --export=ALL,SELECT_V_BEAT=1,DDR_RESPONSE_QUEUE=1,OVERLAP_REFILL=1 "$exp"
sbatch --parsable run_refill_fault.sbatch
cd ../tlm-final
sbatch --parsable --job-name=zny-att1-wdec run_att1_tlm.sbatch decode
sbatch --parsable --job-name=zny-att1-wpre run_att1_tlm.sbatch prefill
squeue -j 112976,112977
sacct -X -j 112976,112977,112990,112991,113009 -o JobID,JobName,Partition,AllocCPUS,NodeList,State,ExitCode
tail -n 10 slurm-112976.out slurm-112977.out
for job in 112976 112977; do sha256sum -c "run-$job/output.sha256"; cat "run-$job/timing-audit.json"; done
previous=/public/home/yuzelu/Melodydt/runs/issue-270/att1-response-02
python3 -B "$previous/compare_att1_response.py" decode "$previous/tlm/run-112637" run-112976
python3 -B "$previous/compare_att1_response.py" prefill "$previous/tlm/run-112638" run-112977
```

112976/112977 持久运行于 `tlm-final`。Melodydt 接续先核验 582/578 页、退出码、散列和退休 token/KV，再测 ATT1 回填与 Dot 读出重叠。管理结构检查通过，正式 P512/D128 和 300 MHz 物理 STA 未执行。管理中心登记 PR #5 待合并，仓库未配置 `config/board.json`，Projects 由具权限维护者核验和同步，独立审查人待指定。
