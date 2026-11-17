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
