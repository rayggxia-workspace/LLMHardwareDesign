# Issue102 完整 GQA RTL 实验

[冻结合同](PROTOCOL.md)、[报告](../../../docs/experiments/issue-102-attention-rtl.md)、[实际命令](../../../work/Liangruizhi/102/execution.json)、[结果索引](results/issue-102/index.json)。仅本人授权CPU服务器运行张量、RTL、综合、门级和数学接收。本机只源、管理结构及字节校验。禁止覆盖已有out。

先运行 `python -B scripts/check_project.py`。服务器已有环境：Issue61 venv-modern，Singularity ORFS26Q1，Verilator5.042/Yosys0.63，Nangate45 typical；所有实际argv和commit/逐文件SHA见execution及对应phase binding。

流程：`inputs.py --out NEW_INPUT`编译冻结61/64来源；`run.py build --suite pilot|qualification`构建相应真实driver；`run.py sim --suite ... --stall 0|1 --pilot 0|1|2`运行；`receive.py --run RUN --input INPUT --out NEW_RECEIPT --negative`独立核原捕获编码和所有有效QK/score/exp/P/PV、计数与故障恢复。运行必须提供实际`--binding`、`--prefix`、`--build`等参数；按execution中完整argv复用，不能仅复制上述省略式命令。

正式RTL a6961b7/phase5；最终无注入sim与qualification driver为3b5743f/phase7。正式输出full03s0/s1、qualification02s0/s1；phase8 b84f0b2的receivefull04s0/s1、receivequalification03s0/s1从实际simulation-command独立核binary/build，并严格数值接收。map02来自同RTL字节，cost02严格库存。

`gate.py prepare/build/sim`重放精确map02+原Liberty函数、行为store82；无Q注入的同sim driver，rtlp1/2s0/1与gatep1/2s0/1比较。`gate_receive.py`逐字段核两者并再次独立数学接收。门级只选9query×2等待，每个完整8头；错误/abort/terminal仅RTL。`analyze.py`只汇总已接收actual；不造频率/PPA估计。

接收器数学与inputs.py独立：原捕获SHA→独立Q20桥/Q8/K16/V16编码→I64点积/Fraction RNE→Decimal50 exp表→有理除法→I64 PV。真实cached Q来自61 `.cached`，不以64 `.full`冒充cached。原64有效prefix全数组逐位一致，未来masked QK不在执行域。校准静态KV单位不使用评价数据重新选值。

PC字节：`python -B work/Liangruizhi/102/verify_delivery.py --index project/experiments/attention_rtl/results/issue-102/delivery-index.json --archive project/experiments/attention_rtl/results/issue-102/selected.zip --out D:/Projects/Codex/NEW_TASK/new-receipt.json`。原Git用同目录`verify_sources.py --repository REPO --index INDEX --selected SELECTED --expected-phases 10 --out NEW`。新out必须不存在；精选只metadata/日志，不能用本机字节接收代替数学重跑。
