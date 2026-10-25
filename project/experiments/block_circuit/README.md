# Issue80：完整宽控制器与局部 frame 电路验证

本工具对应 [Issue80](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/80) / [PR81](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/81)。[冻结协议](PROTOCOL.md)、[规格](../../../docs/BLOCK_CIRCUIT_SPEC_V1.md)、[报告](../../../docs/experiments/issue-80-block-circuit.md)、[统一索引](results/issue-80/index.json)分别说明范围、接口、实际结果和 SHA。全部真实编译、输入提取、RTL、综合及独立接收在本人 CPU Slurm 服务器执行；PC 只做源码、小合成、JSON 和字节核验。

## 代码与证据

- project/rtl/wide_service：8 条 byte/S8 ALU、完整 PC/取指/调用/异常控制器、512B 单 1RW frame、单 128KiB ROM、有限 128bit 事务桥。
- assemble.py / graphs.py：输入值无关的静态微码；原 807 样本、69 ROM 请求、7 协议负例、4 RQ 链、6 真实 Granite 完整八专家单坐标 merge 链、2 个缩小完整 norm 行，共 895 命令。
- sim.cpp / run.py：host 只提供命令入口、初始输入及只读程序响应。全部中间运算由 RTL 控制。原始仿真输出、五种实际复位状态、真实周期和 caller IO 留档。
- verify.py / compare.py：独立整数 oracle 和四配置逐位/资源比较，不导入 compiler / micro.py。真实改码并重新 SHA 的负例仍须被拒绝。
- logic_map.py / qualify_logic.py：固定 Nangate45 非制造研究库的逻辑映射和独立实例/工具统计/面积和来源接收；两侧共同 frame/ROM 整体 wrapper 均 blackbox。没有宏面积或 STA。

实际命令、Slurm ID、完整 argv 和每 phase commit/SHA 在 [execution.json](../../../work/Liangruizhi/80/execution.json)；下面只说明调用方式。所有输出目录都必须为新目录，不能覆盖本轮结果。

## 本机轻量检查与接收

```powershell
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/block_circuit -p "test_*.py"
python -B -m unittest discover -s project/experiments/granite_ports -p "test_*.py"
python -B project/experiments/closure/verify_delivery.py --index project/experiments/block_circuit/results/issue-80/index.json --archive project/experiments/block_circuit/results/issue-80/selected.zip --out D:/Projects/Codex/your-new-task/byte-receipt.json
python -B work/Liangruizhi/80/verify_sources.py --repository . --index project/experiments/block_circuit/results/issue-80/index.json --selected project/experiments/block_circuit/results/issue-80/selected.zip --expected-phases 8 --out D:/Projects/Codex/your-new-task/source-receipt.json
```

先为当前任务新建 D 盘临时目录并设置进程级 TEMP/TMP、PYTHONDONTWRITEBYTECODE=1。最后两条仅核字节，不重做张量数学。接收 source 时需取得索引所指八个历史 commit 对象；不能用当前文件近似替代。

## 服务器复现入口

原根为 /public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025，source phase1—8。输入生成使用旧 Issue76 micro-calibration03 和旧 Issue74 两层 R16 evaluation，只读核 SHA，不重新下载或加载模型。phase4 编译最终 input03；phase5 建立最终 03 仿真；phase4 的 synth-m002/m102 提供 generic 库存；phase7 提供逻辑映射；phase8 接收映射及归档。最终构建与运行的 RTL / sim.cpp 逐源匹配；generic、逻辑映射与最终数值接收所用的五份 RTL SHA 完全一致。

每次正式执行先校验 binding.json 中的 Git commit 与所有来源 SHA，再由 sbatch 按 docs/REMOTE_RULES.md 申请资源。Verilator 5.042、Yosys 0.63、SIF 及完整容器 prefix 见 execution.json。必须给容器显式 --pwd，缺 ROM 的 warning 不接受。

CLI：

```text
assemble.py --primary OLD76/micro-calibration03 --granite OLD74/granite-l0-r16-evaluation01 --granite OLD74/granite-l13-r16-evaluation01 --binding SRC/binding.json --out NEW/input03
run.py build --binding SRC/binding.json --mode 0|1 --out NEW/build --prefix JSON_PREFIX
run.py simulate --binding SRC/binding.json --mode 0|1 --input NEW/input03 --build NEW/build --stall 0|1 --out NEW/run --prefix JSON_PREFIX
verify.py --input NEW/input03 --run NEW/run --negative --out NEW/receipt.json
run.py synth --binding SRC/binding.json --mode 0|1 --input NEW/input03 --out NEW/synth --prefix JSON_PREFIX
logic_map.py --binding SRC/binding.json --library LIB --provenance PROVENANCE --input NEW/input03 --mode 0|1 --out NEW/map --prefix JSON_PREFIX
```

这些是参数格式，0|1 表示二选一，不是可以原样运行的 shell 管道。compare.py / qualify_logic.py 使用报告约定的最终目录名；完整可执行命令以实际 submissions 为准。大数据包留授权服务器；精选 metadata 不能替代完整整数接收。

## 公平比较及限制

最终 03 背压按外部事务序号决定 request wait / response latency，BUS 和 LOCAL 对同一外部取指序列收到相同等待；不是按全局时钟相位给两者不同压力。一次 frame 跨桥请求/响应实际 5×128bit，局部直达仍支付 frame 端口、RMW、控制和 caller 32 行写入/32 行读出。无并发 context，也没有总 scalar carry /8。

895×4=3580 命令全部独立通过，五状态 reset/abort 额外验证；完整 frame 一致。42%—44% 是该微码任务集执行周期的组织差，不是 LLM 加速、物理线延迟或同面积 PPA。纯 byte lowering 的 norm8 仍约 579 万周期/任务，程序镜像 1,928,832B；这是必须进一步优化的实测成本。
