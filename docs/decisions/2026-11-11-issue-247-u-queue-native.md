# Issue247：优先有限两槽，保留原图位宽边界

状态：实施待审查；负责人 Melodydt；Refs #247 / PR243。
采用默认关闭的 2/4 槽 E 前端及独立 staged NExp 区域控制器，保留单 S 事务和真实 ACK。
两槽优先：取得主要独立指令收益，四槽面积更高而三元指令无收益。未新增 SRAM。
原图 S32 为主，禁止把 S16 微基准倍率直接用于整图；先实现/验证 S32 算子或真实量化映射。
模型只替换原生覆盖的 S16 NExp 局部区域费用，保留 DDR/cache，避免重复 E/N/S 计费。
不将 idealdual 或 300MHz 假设写成物理完成。完整数据、面积、范围见[实施报告](../experiments/issue-247-u-queue-native.md)。
