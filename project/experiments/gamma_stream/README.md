# Issue93 可重放入口

本目录工具的真实数组、RTL、数值接收和映射只在本人服务器运行。`inputs.py` 对 Issue84 完整物理输入和 Issue61 Gemma 原捕获实现做 SHA 验证；不得另下载模型或以当前 Transformers 替代捕获时源。

冻结目录内每个文件必须符合 `binding.json`。使用已配置服务器 Python 与容器，不在本机运行模型/RTL，不安装新工具。每个 `--out` 必须不存在：

```sh
python -B project/experiments/gamma_stream/inputs.py --old /public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025/input01 --gemma /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/gemma-capture01 --out NEW_INPUT
python -B project/experiments/gamma_stream/run.py build --out NEW_BUILD
python -B project/experiments/gamma_stream/run.py sim --input INPUT --build BUILD --stall 0 --out NEW_RUN
python -B project/experiments/gamma_stream/verify.py --input INPUT --run RUN --out NEW_RECEIPT.json
python -B project/experiments/gamma_stream/run.py map --library LIBERTY --out NEW_MAP
python -B project/experiments/gamma_stream/run.py map --baseline --library LIBERTY --out NEW_BASELINE
python -B project/experiments/gamma_stream/analyze.py --receipt RECEIPT0 RECEIPT1 --map MAP --baseline BASELINE --library LIBERTY --out NEW_COST.json
```

stall 0/1 分别完整执行，不得同时争用计时资源；这些是离散 RTL 边沿，不是 CPU 墙钟性能。原 driver 两路各 51 个完成记录（48 正常、1 预期零分母、2 故意错误 gamma 数值负例）。错误 gamma 内容被独立参考检出，RTL 不具有语义签名，不声称它主动报错。两路接收都需要严格 schema、全部角色/主矩阵、raw M 计数及精确源 SHA。

`chain93` 为独立命令原型；源代码的 epoch 尾部测试对 Verilator RTL 寄存器注入，门级必须另行适配真实 FF，不可直接沿用顶层输出赋值。单个外部读在途，恢复测试环境允许两回复槽（至少 320bit 加控制）但不计入 core 综合；该区别必须保留。

PC 只做管理检查与证据字节接收：

```sh
python -B scripts/check_project.py
python -B work/Liangruizhi/93/verify_delivery.py --index INDEX.json --archive selected.zip --out NEW_BYTE_RECEIPT.json
python -B work/Liangruizhi/93/verify_sources.py --repository REPO --index INDEX.json --selected selected.zip --expected-phases 6 --out NEW_GIT_RECEIPT.json
```

具体实际 argv、Slurm、冻结 commit、报告/限制和原始 SHA 在 `work/Liangruizhi/93`、`results/issue-93` 及交接中。通用 V、H2560 完整 M、同外存入口速度比较与宏/STA/PPA 尚不属于本轮验收。
