# 本机Llama跨模型最小验证（Issue56）

仅复用已下载meta-llama/Llama-3.2-1B-Instruct对应的原BF16权重，model.json冻结9文件SHA及两来源revision。
FP32计算同一checkpoint，不是另一个原生FP32 checkpoint。4线程、本机CPU、离线，无服务器/大模型下载。
捕获layer0完整Q0..3/KV0、d64、prefill32+decode8；独立校准32，systems/arithmetic两评价文本，参数规则沿用Issue47。
q_proj捕获完整GQA所需256输出、K2048；down_proj取16输出、完整K8192，不能称全FFN或全模型INT8。

所有正式脚本须从干净commit运行；`--development`仅保留开发诊断，不接受为正式数据。
先`python -B scripts/check_project.py`及`test_contract.py`。

```powershell
& <已有环境>/Scripts/python.exe -B project/experiments/llama_cross/capture.py --weights <已有Llama目录> --output <新D盘capture目录>
& <已有环境>/Scripts/python.exe -B project/experiments/llama_cross/run.py --capture <capture> --output <新attention目录>
& <已有环境>/Scripts/python.exe -B project/experiments/llama_cross/linear.py --capture <capture> --output <新linear目录>
& <已有环境>/Scripts/python.exe -B project/experiments/llama_cross/service.py --output <新service目录>
```

后三项依赖捕获后可并行；service内部2worker，与另外两个整数进程合计4worker。环境为既有torch2.10.0+cpu/transformers4.57.6。
run/audit/cache由Issue47固定工具适配4头，core/oracle/fixed/tables直接复用并绑定SHA，不修改旧Qwen数据或源码。
attention的audit.py重算Fraction输入、Decimal scale、独立oracle与因果cache；linear的audit_linear.py独立重算输入和INT64/RQ。
每种整数与服务运行各两次，`--repeat`核科学payload逐字节相同；单纯通过本模型不等于完成所有E1/E2。

服务固定库存沿用Issue51的MC6KiB+PE2KiB/M总32KiB、S8×32KiB、1RW/128bit、64B包头和payload对齐、有限2KiB FIFO。
输入区域限S0..5，S6保存META、S7保存结果，W/A区分配独立bank；K8192/16行预装容量拒绝，改8行。
384条件固定扫描；8份trace事前选定。每个位置配对同精度/资源/策略，两窗口/两策略的最佳包络只作描述，非全局最优。
四次代表N16 tile重复是服务压力，不称完整q_proj、完整GQA服务或32token全图。矩阵/消费者周期未RTL校准。
线性RQ32整数参考和packet位相同不代表8lane硬件或近端速度已实现。

norm/RoPE/模型其余层仍FP32参考；量化与M/r编译离线浮点，P15 PV宽乘为多8位乘/宽整数合并，RNE/饱和显式，不能称全整数模型。
关注跨模型是否改变RQ/完整K内留与容量/端口判断；M/A完整attention、递推/物理与端到端收益仍须后续证据。
