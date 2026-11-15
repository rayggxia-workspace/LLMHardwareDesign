# 当前算子图到宏级指令与候选连线流程

架构依据是 PR185：P/U/C/F/J 是控制归属，功能宏才是硬边界；包括同组内部路径在内的数据连接都需要明确的产品端点绑定。当前底座为 hardware/blockv2-mod-shared-memory.json。

## 两类输入与编译过程

- 硬件：宏、控制归属、服务 ABI、有限存储/仲裁和真实端点。
- 算子图：同源 native-recipe-graph.json、native-operand-recipes.json、native-value-layout.json。它们是图和操作数描述，不是历史执行计划。

在 Slurm 任务中使用 reproducibility/environment.json 指定的 Python/module roots。当前命令和参数见 README.md：

1. compiler/run_macro_graph_frontend.py 生成合法宏服务候选。
2. compiler/run_macro_selection.py 选择同一图的完整计划。
3. compiler/materialize_native_product.py 合并产品阶段所需静态连接，生成宏/父层单元端点绑定。选中装配必须有对应源码哈希一致的完整 elaboration 证据。
4. compiler/package_native_plan.py 生成母控页、有限局控内核、描述符、部署序列、地址分配和同计划 candidate-wiring.json。
5. tlm/run_macro_package.py 执行封存指令包；运行数据和 SRAM 参数需与目标底座绑定。TLM 不重新映射算子或替换选中计划。

## 当前验证结果

完整 36 层 Qwen2.5-3B 两 token prefill 和一步自产 KV decode 已执行全部 141490/70457 次调用；651/723 个产出张量与独立定点参考逐字节一致。验收记录为 evidence/architecture-revision-185/Qwen-short-acceptance-115200.json。

剩余 benchmark 的 20 张单层图均已尝试，但均停在尺寸解析或 operand lowering，尚无一张进入完整选择计划。具体责任和证据见 evidence/architecture-revision-185/RESULTS_ZH.md。

时序是未校准 TLM 预测，排除程序装载与外部阶段准备，不代表物理验收、广泛模型精度或连续请求稳态吞吐。未运行 P512/D128。

## 历史入口

run_flow.py/run_flow.sbatch 是旧底座诊断入口，必须显式 --legacy-diagnostic，并仍受冻结源码校验约束。algo1_full_model.sbatch、full_instruction_flow.sbatch 和 algo1.sbatch 默认拒绝运行。旧说明和实现保存在 evidence/history。

旧归档页、固定 U/P 供数路径、旧 symbolic RUN_LOOP 结果和 diagnostic-zero 回放，均不能代替当前两输入编译、候选连线或完整实数值评估。
