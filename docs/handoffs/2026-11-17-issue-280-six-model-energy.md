# 六模型 TLM 分项能耗扩测

2026-11-17（Asia/Shanghai）。负责人 Melodydt。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) / [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)，分支 `task/280-seven-model-energy`。代码 `92d5f20d7d8525a63549f02037a004ebb5b334ac`，冻结速度基线 `fbff1bd0e455739f28d9b7dd00b97216fe7bb847`。

## 工件与连接

六模型的完整执行计划、三 P 母/局控程序、W8A16 权重、真实历史和已验收输出在旧服务器本人目录生成归档，未重新生成检查点。源归档根 `/public/home/yuzelu/Melodydt/runs/issue-280/six-energy-transfer-01`。传输采用 `scp -3` 在两服务器间直接中继，不在本机保存完整模型。

| 模型 | 归档字节 | SHA-256 |
| --- | ---: | --- |
| Llama | 2423797760 | `39bfaef60dacc5a4e1b7f31c6c416d9986894ae0ec3d307684a1199a4c5f7375` |
| Granite | 3895429120 | `ff5ed769d88ebf58de11c9513b30add061ab2302354a359833abb46a5779b26b` |
| Phi | 6728038400 | `939ffdabeae8cdb4cda893226b90c5de03cc636caa02feba14d66f59e2ed12be` |
| Gemma Q12 | 7016376320 | `dab724187118cbe91834461fcedf849762b3955932206dafa5d282f190f250c0` |
| Qwen3.5 | 7172689920 | `50df04e61e879786bd51753cbaff414c3f86cdaa08b21c2acd64a488229cc882` |
| Falcon | 4051200000 | `0594b4366c6c7b521b2f30db0c4ed8fc3624f6dac7d3b09d8d199a9c6055510c` |

BSCC 登录目标 `t6s011227@BSCC-T6@ssh.cn-zhongwei-1.paracloud.com`。本轮观察到域名解析至 `36.103.203.6` 后密码认证成功但 session open 超时；固定已核验的 `36.103.203.5` 后控制命令恢复。RSA 主机指纹与既有记录一致。密码和私钥不进入记录。

目标工作根 `/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01/six-model-energy-01`。依赖仍用 `~/LLMHardware/opt/orfs-current-repacked.rootfs` 和既有 Qwen3 bridge。运行时把冻结输入绑定到原逻辑路径，以保持计划与程序 SHA 不变。每个作业有独立 `run-<job>-<model>/runner`；输入只读。共享源文件不覆盖，计算节点逐文件验证后才开始回放。

## 首个作业回执

Llama 首轮 `38820291` 在 m3ca0306、24 核、UNLIMITED，12 秒后 `FAILED 2:0`：归档校验与解包通过，但漏载 singularity 模块，未执行模型。失败记录保留。

修订源码 `aec62a8b6fce24ec62cf0431309145502152ecb3` 补入 Qwen3 同款 `singularity/3.7.0` 模块。15:40:23 启动 Llama `38820601`（m3ca0704）与 Granite `38820602`（m3ca1603），均单节点两阶段各 12 核。15:42 读回两项 RUNNING、24 核、`UNLIMITED`。分别核验 713／3,961 个目标文件 SHA，已输出 `FROZEN_INPUTS_AND_PROBES_PREPARED`。尚无回放验收结果。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01/six-model-energy-01
sbatch --parsable --time=0 --job-name=mdt-280e-llama run_six_model_energy.sbatch llama
sbatch --parsable --time=0 --job-name=mdt-280e-granite run_six_model_energy.sbatch granite
squeue -j 38820601,38820602 -o '%.12i %.18j %.10T %.10M %.10l %.18R'
sacct -X -j 38820601,38820602 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed,Timelimit
tail -n 30 slurm-38820601.log slurm-38820602.log
tail -n 15 run-38820601-llama/{prefill,decode}.log
tail -n 15 run-38820602-granite/{prefill,decode}.log
cat run-38820601-llama/{prefill,decode}/acceptance.json
cat run-38820602-granite/{prefill,decode}/acceptance.json
```

日志 `slurm-38820601.log`／`slurm-38820602.log`，结果 `run-38820601-llama/`／`run-38820602-granite/`。归档传输完成不代表目标 SHA 验收或仿真通过。运行、退出码、功能与物理验收分别记录。

## 验收与能耗口径

先核验归档及全部传输文件 SHA。回放使用 512-bit TLM SRAM、3334 ps 核周期、三 P FFN、512 位置真实历史、短 Prefill 与两步 Decode。直接运行冻结 plan，不访问检查点编译器。

新采样要求完整 result、logits、残差和逐层文件与原验收结果一致；这继承原同输入 FP32 对照，不冒充本轮重新执行 FP32。DDR 终态、各窗口的提交/接收/回调与 SRAM 位宽、字节、bank 计数分别核验。任何差异拒绝生成通过回执。

`six_model_tlm_power.py` 复用 Qwen3/C639 的 300 MHz 分项标定，输出片上已覆盖＋DDR 器件的小计，读 DMA 动态另列敏感性。主表的 M 增量与 Qwen3 v1 一样只含 PR272 FFN 分组；普通投影的忙时单列。任意 PM 页长度按实际字数换算，未经同长实测的页明确标为按字迁移；256/384-bit 局部访问列出串行映射。计数包含 Granite 嵌套专家激活；Gemma GELU、sigmoid、缩放、GDN/Mamba2 等未匹配标定的计算不能当作零能耗。

这是固定 TLM 时间下的条件估算。旧 M 时序未闭合、实际驻留与门控、读 DMA 空闲、控制取指、额外算术、顶层时钟/互连、PHY/板级仍未全部覆盖。区间是样本端点，不是误差置信区间。

## 后续与交付

继续完成五模型转存，逐模型提交同一入口并核验 `UNLIMITED`；通过三窗验收后积分、读回结果与散列，每个模型完成即更新 `energy_report_models.json` 和同名 `docs/experiments/seven-model-energy-evaluation.pdf`。本轮截至首次提交还没有新增模型能耗结果。

已执行：本地 Python AST、Qwen3 系数换算核对、项目管理检查；BSCC Bash 语法与脚本 SHA 已核对。管理检查不代替业务回放，未执行的模型回放/物理验收不计通过。审查人待指定，Issue 进行中，PR 草稿；项目登记 PR #5 pending，缺 `config/board.json`，Projects 条目未核验/同步 pending。

本机目录 `D:/Study_material/Study_material/LLMHardwareDesign` 的管理文件可能旧于远端。后续写共享文档先读远端最新版本，保留无关改动；使用 Melodydt GitHub 连接，不借用其他账号。本机新增辅助代码、临时 SSH 调试和传输日志与已上传任务分支分别记录。恢复第一步：检查上述作业和传输状态，验收完成模型，再按本页入口续跑。处理人 Melodydt。


## 15:53 后续作业接续

Phi 回放 38820798 于 15:47:41 在 m3ca2002 开始，24 核、UNLIMITED，1241 个输入 SHA 校验通过。日志 slurm-38820798.log，结果 run-38820798-phi/。入口为 sbatch --parsable --time=0 --job-name=mdt-280e-phi run_six_model_energy.sbatch phi，源码仍为 aec62a8b6fce24ec62cf0431309145502152ecb3。

已受理三项单核、不限时、afterok 依赖积分作业：38820946（Llama，依赖 38820601）、38820947（Granite，依赖 38820602）、38820949（Phi，依赖 38820798）。入口为 sbatch --parsable --time=0 --dependency=afterok:<回放号> --job-name=mdt-280p-<模型> run_six_energy_rollup.sbatch <模型> <回放号>，积分脚本源码 efccd9bd81851eaf2d55abaf0ea2a5cd5a72d876。日志 slurm-<积分号>.log，输出 power-<积分号>-<模型>/<模型>_tlm_power_v1.json。依赖就绪前节点待分配，不视为运行。先验回放 results.sha256，再检查 acceptance，最后积分并生成散列。

跟踪全部新任务：squeue -j 38820601,38820602,38820798,38820946,38820947,38820949；历史终态使用 sacct -X -j 同一作业列表 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed,Timelimit。


## 16:11 全部迁移完成与首模型验收

六个归档均以 scp -3 直达 BSCC，传输进程退出 0。Falcon 38821328 的归档和 1177 项输入通过，但两个 srun 步骤因 Unexpected message received 未开始，父作业 FAILED 1:0（70 秒）。其失效依赖 38821329 已取消，失败文件保留。使用相同代码排除 m3ca2201 后重提。

| 模型 | 回放作业／节点 | 积分作业 | 16:11 状态 |
| --- | --- | --- | --- |
| Llama | 38820601 / m3ca0704 | 38820946 | Prefill 通过，Decode 运行 |
| Granite | 38820602 / m3ca1603 | 38820947 / m3ca0308 | 两作业 COMPLETED 0:0，回放 30:05，积分 00:06 |
| Phi | 38820798 / m3ca2002 | 38820949 | 两阶段运行 |
| Falcon | 38821511 / m3ca0507 | 38821512 | 两阶段运行 |
| Gemma | 38821513 / m3ca2204 | 38821514 | 两阶段运行 |
| Qwen3.5 | 38821601 / m3ca0104 | 38821602 | RUNNING |

新增三组使用同一服务器、任务目录、分区 v6_384、回放 2×12 核及积分 1 核，全部读回 UNLIMITED。回放源码 aec62a8b6fce24ec62cf0431309145502152ecb3，积分源码 efccd9bd81851eaf2d55abaf0ea2a5cd5a72d876。实际命令：

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01/six-model-energy-01
# model 分别为 falcon、gemma、qwen35；依赖号分别为 38821511、38821513、38821601
sbatch --parsable --time=0 --exclude=m3ca2201 --job-name=mdt-280e-$model run_six_model_energy.sbatch "$model"
sbatch --parsable --time=0 --dependency=afterok:$replay_job --job-name=mdt-280p-$model run_six_energy_rollup.sbatch "$model" "$replay_job"
squeue -j 38820601,38820602,38820798,38821511,38821513,38821601,38820946,38820947,38820949,38821512,38821514,38821602
sacct -X -j 38820601,38820602,38820798,38821511,38821513,38821601,38820946,38820947,38820949,38821512,38821514,38821602 --format=JobID,State,ExitCode,Elapsed,NodeList,Timelimit
# 将变量替换为表内实际模型、回放及积分号
 tail -n 20 slurm-$replay_job.log
cat run-$replay_job-$model/{prefill,decode}/acceptance.json
cat power-$power_job-$model/${model}_tlm_power_v1.json
```

### Granite 结果

所有数值和计时与冻结 plan 相同，两个阶段通过完整 result、数值文件及 DDR/SRAM 对账。两阶段小型观测、工具版本、源码与源/输出清单保存于 `work/Melodydt/280/six-model-results/granite/`；原始层文件与权重留授权服务器。17 个下载文件与回放清单逐项核对；积分结果与服务器清单匹配，本地 Python 3.7.0 重算字节一致。

| 窗口 | tok/s | 已覆盖片上＋DDR mJ/token | 平均 W | 加同写读 DMA 动态代理 mJ/token |
| --- | ---: | ---: | ---: | ---: |
| 短 Prefill | 16.073199 | 250.733745–251.012268 | 4.030093–4.034570 | 251.050874–251.329397 |
| 首 Decode | 6.945634 | 522.456211–522.737333 | 3.628790–3.630742 | 522.878914–523.160036 |
| 稳态 Decode | 6.940185 | 522.814140–523.095266 | 3.628427–3.630378 | 523.236987–523.518113 |

结果 `work/Melodydt/280/granite_tlm_power_v1.json`，SHA-256 `83895abc6a9d4b7780f71083136a1b5de89a71dba829eef870ea31cbbbba9fd1`。64 维紧凑 KV、V 复用和真实 top-8 专家 3/3/2 并行保持冻结版本；嵌套激活实际计数。尚未覆盖 router、softmax、加权累加等未匹配算术的完整能耗；不是整芯片签核。

本地复算（输出文件须不存在）：

```bash
python work/Melodydt/280/six_model_tlm_power.py granite work/Melodydt/280/six-model-results/granite work/Melodydt/280 tmp/granite_tlm_power_recomputed.json
```

剩余五模型的回放和 afterok 积分继续运行；每个完成后重验小型输入清单、复算与单位，并更新同名 PDF。物理缺项、旧 M 时序、登记和看板状态与上文一致。

## Llama 结果与 PDF 首次扩展

Llama 回放 38820601 在 m3ca0704 运行 33:57，积分 38820946 在 m3ca0608 运行 00:04，均 COMPLETED 0:0。713 项输入校验、两阶段完整冻结输出与 DDR/SRAM 对账通过，17 个下载文件和服务器结果 SHA 核对、本地 Python 3.7.0 复算字节一致。

| 窗口 | tok/s | 已覆盖片上＋DDR mJ/token | 平均 W | 加同写读 DMA 动态代理 mJ/token |
| --- | ---: | ---: | ---: | ---: |
| 短 Prefill | 15.534217 | 270.433706–270.804381 | 4.200976–4.206734 | 270.818890–271.189566 |
| 首 Decode | 5.677407 | 659.473574–659.847803 | 3.744100–3.746224 | 660.017313–660.391541 |
| 稳态 Decode | 5.674618 | 659.826720–660.200951 | 3.744265–3.746388 | 660.370555–660.744786 |

结果 `work/Melodydt/280/llama_tlm_power_v1.json`，SHA-256 `ee3705e8423dd808bb3d60ad4611a061b8af9d06d1eb3f0aff4d3a3f1fd2d1c9`，可复算小型输入在 `six-model-results/llama/`。保留 64 维紧凑 KV、V 复用和稠密三 P 的 DDR Mid 路径，未改模型调度；256-bit 局部访问按串行 128-bit 参考、固定 TLM 时间估计。普通投影 M 额外情景仍在主表之外。

PDF v1.1 已加入 Granite 并增加跨模型汇总页，七页 Poppler 目检通过；SHA-256 `5d4b3e8f77c4d05c212ae73f8343233e69555ea1b51b19a9045ae47104afde8d`。原 `output/pdf/seven-model-energy-evaluation.pdf` 写入及原子替换均返回拒绝访问，文件非只读且目录 ACL 允许修改，疑为本机打开程序占用；未强制关闭用户程序。仓库同名 `docs/experiments/seven-model-energy-evaluation.pdf` 正常更新，本机可用 `output/pdf/seven-model-energy-evaluation-current.pdf`。后续继续更新这两个可写路径并加入 Llama。Phi、Gemma、Qwen3.5、Falcon 回放及依赖积分继续。

PDF v1.2 已加入 Llama，共九页，保留逐模型实现、缺项、读 DMA 情景及源码证据链接。新增页和汇总目检、数值提取与哈希检查通过，SHA-256 `7cbedf049d10eb1b3a5a23484ed9058f92168811ca79e097c1d90cf3a0801353`。Granite 数据提交 `4cd5c6c745373092d2075d8184809cf56f940042`；Llama 数据和 PDF v1.1 提交 `8fec367f54eb5964d7d4fdfc03c5167367228fa7`，PDF v1.1 已从 GitHub 读回核对完整内容。

## 片上与片上＋DDR 两类报告

按用户新增要求，所有后续结果必须同时报告 `covered_on_chip_subtotal`（片上已覆盖）与 `covered_subtotal`（片上已覆盖＋DDR 器件），两类分别展示 W 和 mJ/token。读 DMA 动态代理属于片上增量，分别加到两类小计，并与基础表分开；未标定片上项、PHY 和板级 I/O 继续列为缺项。

| 模型 | 短 Prefill 片上 | 短 Prefill 片上＋DDR | 稳态 Decode 片上 | 稳态 Decode 片上＋DDR |
| --- | ---: | ---: | ---: | ---: |
| Qwen3 | 50.004–50.127 | 164.944–165.067 | 163.586–163.711 | 496.440–496.566 |
| Granite | 73.149–73.428 | 250.734–251.012 | 168.837–169.118 | 522.814–523.095 |
| Llama | 75.804–76.174 | 270.434–270.804 | 206.341–206.715 | 659.827–660.201 |

单位 mJ/token，不含读 DMA 动态代理。首 Decode、两类平均功耗和分项见原 JSON 与 PDF。此次没有修改标定系数和模型结果，无需重新回放。PDF v1.2.1 共十页，分别提供两类汇总页和模型页的并列指标；生成器逐窗验证片上＋DDR＝组合小计（能量、每 token 能耗、平均功耗均对账），Poppler 目检和数值提取通过。PDF SHA-256 `4a17a0ea5dcfa1d82cf86ae3d61d87f2503527992f63f6414325b207409c7b0a`。

## Falcon 双阶段与三窗能耗

2026-11-17 17:21（Asia/Shanghai）核验：回放 38821511 在 m3ca0507 用时 01:11:20，积分 38821512 在 m3ca0504 用时 00:00:02，均 COMPLETED 0:0、UNLIMITED。1177 项输入、两阶段完整冻结 result、逐层数值与输出、DDR 终态及 SRAM 计数通过；17 个读回文件对原清单通过，Python 3.7.0 本地与 Python 3.6.6 服务器分项积分字节一致。

| 窗口 | tok/s | 片上已覆盖 mJ/token | 片上＋DDR mJ/token | 片上平均 W | 片上＋DDR 平均 W |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill | 4.297764 | 272.883986–273.585167 | 944.174539–944.875720 | 1.172791–1.175805 | 4.057840–4.060853 |
| 首 Decode | 3.020610 | 387.766344–388.470652 | 1285.731718–1286.436027 | 1.171291–1.173418 | 3.883694–3.885821 |
| 稳态 Decode | 3.020079 | 387.834265–388.538576 | 1286.078536–1286.782847 | 1.171290–1.173417 | 3.884059–3.886186 |

不含读 DMA 动态代理；该项单独位于结果 JSON 的 read_dma_dynamic_sensitivity。主表没有计入无匹配标定的 Mamba2、卷积与额外缩放算术，但其 DDR 与已观测 SRAM 访问已覆盖。保留冻结的递推后注意力执行、128 维 ATT1 的 V 读取流水、真实持久状态和三 P FFN。

结果 `work/Melodydt/280/falcon_tlm_power_v1.json`，SHA-256 `6dad6edadd5600f08f99eed2f941dd8962cee54073edaa9d7be9e5f87c9c14dd`。复算输入在 `work/Melodydt/280/six-model-results/falcon/`，服务器原始回放 `run-38821511-falcon/`，积分 `power-38821512-falcon/`。本地复算沿用上述命令，将 granite 换为 falcon。Phi、Gemma、Qwen3.5 继续运行；随后逐个完成验收、积分、片上与片上＋DDR 复核及 PDF 更新。
