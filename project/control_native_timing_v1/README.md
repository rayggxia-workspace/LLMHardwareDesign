# 原生控制配置的独立映射与时序

Issue #179 / PR #180。`map_one.py` 固定五类原生LC的两种实例ID、P16两种ID、原生MC和双局控返回连接，共14配置。STA采用既有锁定的Nangate45 typical Liberty/LEF，周期保持3.333333333 ns。

接口预算见 `constraints.json`：输入/输出max 0.5 ns、min 0.05 ns，输入转换0.05 ns、输出5 fF，setup/hold uncertainty 0.05/0.02 ns。所有非时钟输入均受约束，保留异步复位recovery/removal检查。

```bash
python3 -B project/control_native_timing_v1/map_one.py u0 \
  --yosys YOSYS --openroad OPENROAD --liberty N45/lib/NangateOpenCellLibrary_typical.lib --out mapped
python3 -B project/control_native_timing_v1/close_one.py \
  --yosys YOSYS --openroad OPENROAD --platform N45 \
  --mapped mapped --out repaired --workers 1 --modules u0
```

配置名为u0/u1、f0/f1、c0/c1、p0/p1、j0/j1、p16_0/p16_1、mother、link。每配置独立执行标准单元映射、布局、缓冲、setup/hold修复、全局布线RC估算、slew/cap检查和寄存器对应的网表等价证明。

新增hold修复保留复位检查，通过延时缓冲处理最小路径；电气修复按相同单元族选择更大驱动。目标周期及接口预算不因失败而放宽。最终gate同时要求setup/hold非负、setup TNS=0、电气违规0和等价通过。阶段结果及未结束配置分别记录，映射成功或setup转正不等于全部通过。

这是理想时钟、CTS前、单模块预算下的研究估算。[分配置结果与散列](../../work/Melodydt/179/native-control-and-top-validation.json)分别记录已结束与仍运行的配置。它不代替正式父层、实际宏、CDC、时钟树、详细布线和签核工况验收。新双P顶层的组合时序也不能由单模块结果推定。
