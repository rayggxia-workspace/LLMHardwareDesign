# main 的64位控制基线

Issue179 / PR180。将 main `c4d7b960599b9d292f27eb4429d5f226a7156c95` 的母控、五类原生组及局控生成器作为64位实现来源；同路径内容逐字节采用 main，来源见 `main-lock.json`。这是有范围的文件同步，提交只继承 PR180，不冒充整个 main 历史已合并。共享的128位源码和旧验收保留，但本入口只生成/验证 v2、64位程序。

`project/rtl/mother_control_v1` 与 `project/experiments/{mother_control_v1,pu_leaf_base,cfj_leaf_base}` 是本轮权威实现。母控内含自己的16KiB PM；P/U 保留 main 的局控及 U 修复；C/F/J 使用 main 冻结的 #180 控制子集。`frozen_inputs` 只保存该 CFJ 锁定快照中与当前 PR180 不同的三份辅助文件，不覆盖当前方案或放宽 SHA 检查。

旧 `control_five_boot_v1`、`control_recovery_boot_v1`、`control_task_compiler_v1` 仍是先前研究配置；它们没有自动升级成 main 全功能原生服务。尤其不能用 `control_frontend_v1/stage.py` 的 `native_lc()` 替换 main P/U 局控后，继续引用 main 的验收结果。

## 检查与服务器回放

```bash
python3 -B project/control_main64_v1/check.py
python3.12 -B project/control_main64_v1/replay.py --kind mother --out /results/mother
python3.12 -B project/control_main64_v1/replay.py --kind U-fma-duplex --out /results/u-fma
```

RTL 仿真只在获授权服务器 Slurm 分配内运行。回放需要 main 原脚本所绑定的 #193 acceptance-02 和 #155 bank，使用已安装 Verilator5.042、ORFS容器。其余 `--kind` 见 replay.py。main 的产生器原文不改；新增内容仅核验来源和替换测试夹具中的 MC+母控PM，局控程序存储仍是夹具行为模型。该回放不验证统一 boot manager、编译器、三端真实PM、完整ISA或物理组合时序。

详细审查和缺项见 `docs/local-blocks/CONTROL_RESEARCH_HANDOFF.md` 的“main64合入”段。旧1690/1690、九配置综合交付和 main 独立物理回执各有源版本，不合并计为本轮新回归。

37份额外物理脚本依赖见physical-dependencies.json；只核验原始main来源和模块导入，本轮不重跑物理。123例RTL源版本为f046a8c9，其后补充这些未参与RTL编译的工具文件，不把它们记为已重做物理验收。
