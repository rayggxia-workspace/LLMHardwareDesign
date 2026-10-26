# 十二层校准场景保留上下文导体

关联 [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)、草稿 PR122；2026-10-27 CST。

91915 已逐路径解析实际 classic benchmark 的 133488 条线网，覆盖 M1–M12；这是几何解码通过，尚无场解或 RC 模型资格。复核发现旧分组仅去掉末尾数字，把 `O6_..._cntxM7_1` 与 `O6_..._3` 分到两个场景。这样会遗漏目标导体的屏蔽与跨层耦合，因此旧场景不可用于校准。保留该失败边界及原始输出，使用新不可变 run 重新生成。

修正后，同一实验的信号线及全部 `cntxM*` 导体必须在同一个场景内；只平移 XY 数值原点，保留实际 DEF 单位、端点扩展、ODB NDR 宽度及所有导体几何。地平面由官方求解器固定在 z=0，均匀介质 epsilon_r=3.9 是本研究假设。

校准只请求模型拟合所读取的信号 master 1/2/3（电阻或对角场景按实际存在者）；其他信号线和上下文导体仍完整参与场解。这里输出的是所选 Maxwell 矩阵行，不将其称为整颗校准芯片的完整寄生网表。官方固定源码的 `extModelGen.cpp` 区分 wireNum 1/2/3 并将 `cntxM` 耦合转入模型地电容；后续 SPEF/模型适配仍需实测验证。

先导覆盖每个实际生成的 family/目标层及最大上下文场景。检查有限数、Maxwell 符号、行电荷守恒、总电容统计标准误差不超过 0.3%，以及独立行互易性在 5 sigma 加总电容 1% 范围内。该门槛只是适配资格，不替代原作者参考算例、全量校准、留出几何误差及最终分层边界不重计证明。

参考实现固定为 [OpenROAD 6ea4ca 的模型生成器](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/rcx/src/extModelGen.cpp)；官方流程是参考 SPEF 经 [bench_read_spef/write_rules](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/rcx/calibration/script/generate_rules.tcl) 生成模型。不得修改旧十层规则的 LayerCount 来代替实际十二层拟合。
