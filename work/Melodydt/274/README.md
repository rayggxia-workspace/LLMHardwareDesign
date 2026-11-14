# Issue #274 非 Qwen2.5 短程吞吐

2026-11-14（Asia/Shanghai）。负责人 Melodydt。[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274)，任务分支 `task/274-seven-model-short-throughput` 继承 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f173f2ad540efade8a552c35e9dba0f43c0`。

## 服务器回执

服务器登录 `yuzelu@10.129.166.172`，任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`。

| 作业 | 分区与核数 | 终态 | 本轮取得的证据 |
| --- | --- | --- | --- |
| 114273 `mdt-274prep` | c96 / node20，8×12 核 | FAILED 1:0 | 六个归档检查点全部逐文件通过历史 SHA-256。Llama 在扫描的任务/共享目录未发现完整检查点。Qwen3 功能对照因未设置原归档环境开关失败，原日志保留。 |
| 114275 `mdt-274q3ref` | c96 / node17，12 核 | COMPLETED 0:0 | 带原环境重跑 Qwen3 SystemC：28 层、9 个位置，hidden/logits 与历史输出逐字节相同，376,056 次 C/D 提交与完成对账。 |
| 114290 `mdt-274q3gath` | c96 / node17，12 核 | COMPLETED 0:0 | Algo1 编译单页母控/局控和带长度的 Gather 描述符。512-bit SRAM、3,334 ps 核周期、双通道 630 ps DRAMsim3、每通道 32 credits 下，两次独立输入查表结果逐字节匹配冻结权重，144 次 DDR 读与回调对账。 |

114290 仅执行 Qwen3 输入 embedding。独立的 descriptor ABI 8 用于该事务级模型，RTL 接口资格待核验。正式两步 decode、短 prefill 及专项 A/B 未执行。完整 B1/P512/D128 和物理签核另有合同。

| 归档文件 | SHA-256 |
| --- | --- |
| `reference-02/reference-114275/output.sha256` | `c4b2229d379424b7ff5aecc888ccb06f21f653320213d294c92931486c88526d` |
| `qwen3-gather-01/run-114290/receipt.json` | `d46c568fa277a4385e5930c374c2e9859bd74999e4952b64be4a122cb45c303b` |
| `qwen3-gather-01/run-114290/deploy/deployment.json` | `d8698ba9bd95e469f5fd66079cf449a338a1157296f672435504037f9349d8ee` |
| `qwen3-gather-01/run-114290/deploy/mother.bin` | `36873650a2025e651f44552ee5e11ab4cb77e581c0288c71fddeb12bba06e8b9` |
| `qwen3-gather-01/run-114290/deploy/local-0.bin` | `bd6dfe29c3c4329744867eca0d6760c39c473d50df18a22e8641cb30d66e26ab` |
| `qwen3-gather-01/run-114290/deploy/descriptors.bin` | `ff06fcb184b7583e6fed8dabadb15a73669a69a5c1c17d7a53439b870a2f1dac` |

六模型的逐文件散列与图索引在 `prep-01/prep-114273/{qwen3,qwen35,gemma,phi,granite,falcon}.json`，核验用 `prep-01/prep-114273/output.sha256`。Qwen3 的 full 图是既有 B1/S2 图。其余已索引的是代表层图。Llama 的旧图用重建配置与随机参数，不能作为真实模型性能输入。

## 复跑

以下命令在远端执行。每次作业输出按编号进入同目录下的新子目录。

```bash
R=/public/home/yuzelu/Melodydt/runs/issue-274
cd "$R/prep-01"
sbatch --parsable --job-name=mdt-274prep -p c96 -N1 -n8 -c12 -t 02:00:00 -o slurm-%j.log prepare_inputs.sbatch
# 60 核配置在所选 c64 节点使用 -n6 -c10，脚本分批取满 6 路。
cd "$R/qwen3-gather-01"
sbatch --parsable --job-name=mdt-274q3gath -p c64,c96 -N1 -n1 -c12 -t 00:30:00 -o slurm-%j.log qwen3_gather.sbatch
sacct -j 114273,114275,114290 --format=JobID,JobName%28,State,ExitCode,AllocCPUS,NodeList
tail -n 40 slurm-114290.log
sha256sum -c run-114290/output.sha256
```

`qwen3-gather-01/source.sha256` 和 `upstream.sha256` 固定实际运行源码、链接器、TLM、DDR 库与配置。第一次准备批次的参考脚本保留在 `prep-01`，仓库中的修订版对应 `reference-02/reference_qwen3.sh`。历史归档载荷按只读复用。

## 续办

先从真实 Qwen3 第 0 层的 norm 权重与 Gather 输出接到 1,024 维 input RMS、Q/K 头内 RMS 和 16Q/8KV。核对状态写入完成、下一位置读回和独立参考，再扩展 FFN、28 层及完整词表。其余输入已核验，但各自需要完整的短程序、内存映像和时序服务。Llama 需要获授权的 Meta Llama-3.2-1B-Instruct 实际 checkpoint 路径。

管理结构、Python 语法、上传脚本 Bash 语法通过。规则 `rayggxia-project-collab 1.0.0`，项目 `llm-hardware-design`，登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 沿用 pending。缺 `config/board.json`，看板核验和同步待具权限维护者处理，独立审查人待指定。
