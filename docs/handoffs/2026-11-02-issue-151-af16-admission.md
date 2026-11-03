# AF纵向衔接与八模型准入交接

仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design；Issue151 / PR152；主要负责人Melodydt。分支task/151-six-connection-study，base task/143-seven-block-v2；输入cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6；实际测试源a37df8be480d6472627a11419777511042af6a60。最终证据交付commit以PR152最新回执核验。

本地隔离API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/af16-cd8dfc9/integrated，无.git/HEAD/暂存；源与最终上传文件/SHA清单在包外source-upload-manifest.json和upload-manifest.json。根参考、前序包、他人文件/ref-project未改。本地/任务分支与main合并分别记录。

成果：[AF16报告](../W4_AF16_IMPLEMENTATION.md)、[数值合同](../W4_AF16_NUMERIC_CONTRACT.md)、[八样本准入与下一实际尺寸](../AF16_MODEL_ADMISSION.md)。40输入→240B参数/hidden holding→同F两次17输入→2输出，父RUN/终态、metadata及sat归属已实现；旧38RTL/TB/include字节不变。机器索引work/Melodydt/151/af16-implementation.json，ledger af16-model-admission.json，formal checker scripts/check_af_model_admission.py。

服务器yuzelu@10.129.166.172；本人根/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af16-cd8dfc9-20261102。job95242/zenanyan-af16/r01在node1/c64/8CPU首跑COMPLETED0:0，build/sim0，33预声明CASE各一次exactPASS。30source SHA、12文本SHA及archive SHA核对；小文本在af16-rtl-evidence，编译产物留服务器runs/r01/obj_af16。30warnings原文保留，非lintclean；作业已结束，无待等待任务或自动监测。

```bash
TASK=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af16-cd8dfc9-20261102
squeue -j 95242
sacct -j 95242 -o JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList
tail -n 40 "$TASK/slurm/zenanyan-af16-95242.out"
cat "$TASK/runs/r01/results/run-receipt.json"
```

实际提交命令sbatch --parsable "$TASK/submit-r01.sbatch"；完整镜像/资源/runner参数在证据。重跑需全新input/runs与作业，先读REMOTE_RULES及AGENTS并立即提供启动回执；仅服务器Verilator，不在登录节点/本地ModelSim跑RTL，不覆盖已封存结果。

离线checker正式默认运行exit0，核22既有源+wrapper SHA、24literal正反例与八模型×三target=24行；只有synthetic1项静态ALLOW，真实全部GAP，数值/质量UNKNOWN保留。--model qwen3 --target AF16实际原生Python exit2，保留真实H1024/I3072。简要回执af16-admission-cli-checks.json；不能把正确拒绝解释为检查失败或把静态ALLOW写成模型质量通过。

下一项仍L4，优先真实Qwen3 F H1024/I3072：接收实际输入/参数数值及误差/epsilon合同，再实施N-long（count1024、128words及相关地址/拼接）、K32/N8完整归约与有序9MiB参数chunk provider。候选S0..931=14912B/T128words，单M先完成全mid再down，不能在down partial中插gate/up或逐chunk窄化。当前仅方案，不是映射/质量/性能证据。L5通用母控/端点/peerACK、L8真实MEM/共同底座M11-M12物理另验。

在线状态按最终PR/Issue读回：外部审查人待指定，不自合并/done；登记management-hub PR5仍pending。任务分支config无board.json，工具无Projects条目/字段能力，看板实际unverified、同步pending、处理人待指定，未证实权限拒绝；需配置/能力者核条目并同步Project ID/Status/Priority后读回。

恢复第一步：核最新Issue/评论、PR头/base、本人进度和本交接，先运行管理及静态准入checker，读取AF真实回执与Qwen3方案，确认并行范围后在新隔离目录继续。完整L4/实际模型、跨岛和物理仍未验收。
