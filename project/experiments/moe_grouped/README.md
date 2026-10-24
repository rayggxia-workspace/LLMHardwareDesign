# Issue74：完整整数MoE与同函数分组边界

[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74) / [PR75](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/75)，负责人Liangruizhi。执行前范围见[PROTOCOL](PROTOCOL.md)，格式见[GRANITE](GRANITE.md)，服务微程序见[GROUPED_SERVICE](GROUPED_SERVICE.md)，独立接收见[AUDIT](AUDIT.md)。实际成果和限制以[实验报告](../../../docs/experiments/issue-74-moe-grouped.md)及`results/issue-74/index.json`为准，协议不是通过证明。

所有真实模型、张量、整数重算和服务仅在本人CPU服务器新目录执行；本机只写源码、跑小型合成边界测试、读JSON及核字节。无新模型下载、GPU/其他机器任务或Phi解封。既有Issue70/72输入只读，失败保留。CPU运行时间、软件整数参考和条件服务时隙均不能冒充目标INT8内核、RTL或PPA。

## 检查与恢复

先读最新AGENTS/Skill、Issue/PR、进度及交接，核本人认证和任务分支。已有NumPy环境中运行：

```text
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/moe_grouped -p test_*.py
python -B -m unittest discover -s project/experiments/closure -p test_*.py
python -B -m unittest discover -s project/experiments/architecture_extensions -p test_*.py
```

本机为当前进程指定D盘TEMP/TMP，不改系统变量。服务器Python3.12.7、NumPy2.2.6、Torch2.10CPU、Transformers5.20.2，复用Issue61既有环境；具体模型revision、文件SHA和工具版本在捕获及运行manifest。编译/运行绑定原phase的干净Git commit与每源SHA，不能拿当前HEAD替代。每次`--out`必须新建，默认实际SHA重写负例不能跳过。

实际命令和Slurm参数逐项保存于`work/Liangruizhi/74/slurm/*-submit.json`。其`command`为Python参数列表，`phase`指明源胶囊；`sources/phaseN-staging.json`给出原commit及各源SHA。恢复时取得授权服务器输入和原胶囊，在同一自有根下使用新输出后缀，不覆盖旧目录，不依赖可能已从Slurm清除的旧job ID。

Granite流程：`granite_capture.py`先核真实residual/norm/下游参考，再`granite_chain.py compile`，最后`granite_chain.py run --layer 0|13 --router-bits 8|16 --split calibration|evaluation`。8条件分别通过`receive_granite.py`全值接收。`posthoc_granite.py`仅读这些固定产物作误差归因，不是新的格式实验或模型质量门。

分组流程：三份既有g0/K512/K256完整数值产物分别用`grouped_service.py --placement near_m|shared_v --label split|shared`，每项由`receive_grouped_service.py`接收。同g配对才是placement比较；不同g是不同数值函数，不能直接排名质量或归成位置收益。两种标签应科学负载逐字节零差。width lowering、元数据、包头/打包、bank1RW、BUS和有限FIFO计价不等于物理网表已实现。

## 字节接收

取得`results/issue-74/`后，精选metadata包用既有工具核每个成员：

```text
python -B project/experiments/closure/verify_delivery.py --index project/experiments/moe_grouped/results/issue-74/delivery-index.json --archive project/experiments/moe_grouped/results/issue-74/selected.zip --out NEW_RECEIPT.json
```

该复用工具回执schema保留历史issue72名称，含义仅为SHA/字节接收。完整数学接收需要服务器实际NPZ，不能以精选包代替。完整数据位置、大小、SHA、源Git字节核验、实际作业与未完成项见统一索引；权重和旧输入不随新包重复上传。
