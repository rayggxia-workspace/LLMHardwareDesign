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


## 2026-11-15（Asia/Shanghai）完整输入参考和 Qwen3 权重映像

- ModelScope [Llama-3.2-1B-Instruct](https://www.modelscope.cn/models/LLM-Research/Llama-3.2-1B-Instruct) 使用 #56 的版本 `d3e551343d4d81508a0d226656b826c217e463cd`。服务器公网连接超时，本机下载后传入 `llama-checkpoint-01/model/`。8 文件在服务器重验通过；模型 2,471,645,608 B，SHA-256 `1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f`，来源索引与散列在该目录。权重原件留项目授权服务器。
- 114294 `mdt-274refs`（c96/node13，6×12）和 114313 `mdt-274llaref`（c64/node4，12 核）均 COMPLETED 0:0。七套 FP32 数值参考全量核验输出散列，保存从实际 512 个输入位置算出的 KV／适用递推状态、两个输入位置后的最终归一化 hidden、两个 decode logits 及 token。两次处理后缓存长度 513、514。这个真实历史用于对账，#260 性能基线的零值历史需要独立运行。
- 114340 `mdt-274q3pack`（c96/node21，8×12）COMPLETED 0:0。Qwen3 共 28×7 个原生 W8A16 投影和一个全词表 HEAD16 权重，582,016 个 N8/K128 记录，642,957,312 B。独立解包逐项核对权重、scale、顺序与填充。逐张量最大相对 L2 量化误差 0.74051%，仅为权重域诊断，端到端量化精度待核验。回执清单 `qwen3-pack-01/packed-114340/receipts.sha256` 的 SHA-256 为 `5e7ca0612b823472fd048d4fb679e500e5afd7f1306dee4843fcac6dfe4e01d4`。

| 模型 | FP32 Decode 的输入 token → 两次选出 token | reference.json SHA-256 |
| --- | --- | --- |
| Qwen3-0.6B | 264 → 72349 → 5785 | `ce3dc38a50a6ac7d780998978f28fc613961ee27a9acc27942663898a2aad6de` |
| Llama-3.2-1B | 7576 → 264 → 73449 | `8683338243c4d9a9063dc1ef23a1e90d5838c94b31061a54cf927ffe7d72ced3` |
| Gemma-3-4B | 8735 → 496 → 64745 | `b22a62c01d9b55be5a4cda7338ba8207417dc48fbfd2efb10ea2957f513be184` |
| Phi-4-mini | 261 → 164009 → 9682 | `a16a0ad108a1bee93365d6798b1625b8aa3ec5881de8e585b66661a924c182bf` |
| Qwen3.5-4B | 264 → 69892 → 5604 | `4a0f354aae4205d5c150497909059d9f2caa82e1d2d2a20d32a96164df75d3fa` |
| Granite | 312 → 17283 → 4121 | `6db3ae905eef97c446b16fe04cbe7ff36b08f1e6866b34763637920a4107ee3e` |
| Falcon-H1-3B | 772 → 52010 → 10415 | `0a8812cdeef87877b9767c9f03f35fd6e90cbc4145843ce0c3fab3e29531450a` |

服务器任务根下的 `reference-workloads-01/ref-114294/<模型>/reference.json`、`reference-workloads-01/ref-114313/llama/reference.json` 记录来源和全部输出摘要。准备脚本和复跑见下。

```bash
R=/public/home/yuzelu/Melodydt/runs/issue-274
cd "$R/reference-workloads-01"
sbatch --parsable --job-name=mdt-274refs -p c96 -N1 -n6 -c12 -t 01:00:00 -o slurm-%j.log reference_workload.sbatch qwen3 gemma phi qwen35 granite falcon
sbatch --parsable --job-name=mdt-274llaref -p c64,c96 -N1 -n1 -c12 -t 00:30:00 -o slurm-%j.log reference_workload.sbatch llama
cd "$R/qwen3-pack-01"
sbatch --parsable --job-name=mdt-274q3pack -p c96 -N1 -n8 -c12 -t 00:30:00 -o slurm-%j.log pack_qwen3.sbatch ../reference-workloads-01/ref-114294/qwen3/reference.json
sacct -j 114294,114313,114340 --format=JobID,JobName%28,State,ExitCode,AllocCPUS,NodeList
sha256sum -c packed-114340/receipts.sha256
```

下一步用已打包真实权重编译 Qwen3 第 0 层的输入 RMS、QKV、头内 Q/K Norm、RoPE、16Q/8KV 和 O/FFN/残差服务，以实际写确认核验跨位置 KV。当前整模型短程吞吐 0/7，#274 继续进行中，审查未完成。
